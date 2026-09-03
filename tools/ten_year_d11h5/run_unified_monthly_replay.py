"""Run the ten-year common-condition layered replay.

The input ladders are already research-only and PIT-audited.  This script only
aligns the D11 daily ladder to the existing monthly formation dates and applies
one portfolio/backtest policy to every arm.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from portfolio_backtester import (
    PositionBacktestConfig,
    build_position_replay_periods,
    run_position_backtest,
)
from portfolio_backtester.portfolio import build_positions_by_rebalance

from market_data_platform.research_views.daily_watch20_data import (
    load_daily_watch20_daily,
    resolve_daily_watch20_assets,
)


def _align_d11_monthly(base: pd.DataFrame, d11: pd.DataFrame) -> pd.DataFrame:
    formation_dates = pd.DatetimeIndex(sorted(base["trade_date"].unique()))
    d11_dates = pd.DatetimeIndex(sorted(d11["trade_date"].unique()))
    rows: list[pd.DataFrame] = []
    for formation_date in formation_dates:
        prior = d11_dates[d11_dates <= formation_date]
        if len(prior) == 0:
            continue
        source_date = prior[-1]
        part = d11.loc[d11["trade_date"].eq(source_date), ["symbol", "score_D11_20"]].copy()
        part["trade_date"] = formation_date
        part = part.rename(columns={"score_D11_20": "d11"})
        rows.append(part)
    if not rows:
        raise ValueError("D11 ladder has no date on or before monthly formations")
    aligned = pd.concat(rows, ignore_index=True)
    if aligned.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("monthly D11 alignment produced duplicate stock-date keys")
    return base.merge(aligned, on=["trade_date", "symbol"], how="left", validate="one_to_one")


def _read_pricing(data_root: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    assets = resolve_daily_watch20_assets(data_root)
    return load_daily_watch20_daily(
        assets,
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        memory_limit="16GB",
        threads=4,
    )[["trade_date", "symbol", "close", "amount"]]


def run(
    monthly_ladder_path: Path,
    d11_path: Path,
    data_root: Path,
    output_dir: Path,
    *,
    transaction_cost_bps: float = 25.0,
    top_k: int = 20,
    buffer_exit: int = 15,
) -> pd.DataFrame:
    base = pd.read_parquet(monthly_ladder_path)
    d11 = pd.read_parquet(d11_path)
    for frame in (base, d11):
        frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="raise").dt.normalize()
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
    base = _align_d11_monthly(base, d11)
    base["fundamental"] = base["fund"]
    base["dailywatch20"] = base["dw"]
    base["d11h5"] = base["d11"]
    base["fund_dw"] = 0.8 * base["fundamental"] + 0.2 * base["dailywatch20"]
    base["fund_d11h5"] = 0.8 * base["fundamental"] + 0.2 * base["d11h5"]
    base["dw_d11h5"] = 0.5 * base["dailywatch20"] + 0.5 * base["d11h5"]
    base["three_way"] = (
        0.8 * base["fundamental"]
        + 0.1 * base["dailywatch20"]
        + 0.1 * base["d11h5"]
    )
    # Fair-comparison contract: every arm must see the same stock-date keys.
    # The fundamental ladder is sparse before 2018, so remove those rows before
    # choosing formation dates instead of letting each arm silently use a
    # different universe or a different OOS window.
    base = base.dropna(subset=["fundamental", "dailywatch20", "d11h5"]).copy()
    score_columns = {
        "fundamental_only": "fundamental",
        "dailywatch20_only": "dailywatch20",
        "d11h5_only": "d11h5",
        "fundamental_dailywatch20": "fund_dw",
        "fundamental_d11h5": "fund_d11h5",
        "dailywatch20_d11h5": "dw_d11h5",
        "three_way": "three_way",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    date_counts = base.groupby("trade_date", sort=True).size()
    formation_dates = pd.DatetimeIndex(date_counts.loc[date_counts.ge(top_k)].index)
    if len(formation_dates) < 2:
        raise ValueError("common stock-date intersection has fewer than two formations")
    base = base.loc[base["trade_date"].isin(formation_dates)].copy()
    pricing = _read_pricing(data_root, formation_dates.min(), pd.Timestamp("20260901"))
    rows: list[dict[str, object]] = []
    audits: dict[str, object] = {
        "schema_version": "research.ten_year_d11h5.unified_monthly_replay.v1",
        "research_only": True,
        "production_eligible": False,
        "transaction_cost_bps": transaction_cost_bps,
        "top_k": top_k,
        "buffer_exit": buffer_exit,
        "formation_dates": [date.strftime("%Y-%m-%d") for date in formation_dates],
        "score_source": str(monthly_ladder_path),
        "d11_source": str(d11_path),
        "arms": {},
    }
    for arm, score_col in score_columns.items():
        data = base.dropna(subset=[score_col]).copy()
        positions = build_positions_by_rebalance(
            data=data,
            pred_col=score_col,
            price_col="close",
            rebalance_dates=list(formation_dates),
            top_k=top_k,
            shift_days=1,
            buffer_exit=buffer_exit,
            target_weight_policy="normalized",
            group_col=None,
            pricing_data=pricing,
            liquidity_floor_col="amount",
            liquidity_floor_quantile=0.05,
        )
        if positions.empty:
            rows.append({"arm": arm, "status": "empty"})
            audits["arms"][arm] = {"status": "empty"}
            continue
        periods = build_position_replay_periods(positions, pricing)
        result = run_position_backtest(
            positions=positions,
            pricing=pricing,
            periods=periods,
            config=PositionBacktestConfig(
                price_col="close",
                transaction_cost_bps=transaction_cost_bps,
                preserve_gross_exposure=True,
            ),
        )
        result.net_returns.to_csv(output_dir / f"{arm}_net_returns.csv", index=False)
        result.periods.to_csv(output_dir / f"{arm}_periods.csv", index=False)
        positions.to_csv(output_dir / f"{arm}_positions.csv", index=False)
        stats = result.summary["stats"]
        row = {
            "arm": arm,
            "status": "completed",
            "score_column": score_col,
            "formation_dates": len(formation_dates),
            "start_date": formation_dates.min().strftime("%Y-%m-%d"),
            "end_date": formation_dates.max().strftime("%Y-%m-%d"),
            "replay_periods": len(result.periods),
            **stats,
        }
        rows.append(row)
        audits["arms"][arm] = {
            "status": "completed",
            "score_column": score_col,
            "position_rows": len(positions),
            "period_rows": len(result.periods),
            "missing_price_count": int(
                pd.to_numeric(result.periods.get("missing_price_count", 0), errors="coerce")
                .fillna(0)
                .sum()
            )
            if not result.periods.empty and "missing_price_count" in result.periods
            else 0,
        }
    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir / "summary.csv", index=False)
    base.to_parquet(output_dir / "aligned_monthly_score_ladder.parquet", index=False)
    (output_dir / "audit.json").write_text(
        json.dumps(audits, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("monthly_ladder_path", type=Path)
    parser.add_argument("d11_path", type=Path)
    parser.add_argument("data_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(run(args.monthly_ladder_path, args.d11_path, args.data_root, args.output_dir).to_string(index=False))


if __name__ == "__main__":
    main()
