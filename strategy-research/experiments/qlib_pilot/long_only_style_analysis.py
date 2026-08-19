"""Long-only full-market style factor analysis.

Complement to the existing long-short (Q5-Q1) signal study. The long-short
study measures factor spread on a market-neutral, whole-quantile basis, which
overstates what a long-only strategy can actually harvest. This script measures
the same factors in the way a real portfolio is built:

1. frictionless long-only Q1-Q5 quantile legs (signal curves),
2. costed + tradable + next-day-execution long-only Top-K portfolios,
3. annual style factor breakdown.

Phase 1 (2015-2026): three factors (small-cap, low-turnover, growth), both the
full-market universe and a point-in-time top-800 universe.  Uses the clean
daily pipeline with adjusted close and ST / suspension / limit-up flags.

Phase 2 (2008-2026): the same three factors on the full-market universe using
the raw daily / daily_basic pipelines (2008+).  Growth now available from 2008
via the backfilled fundamentals vintage.  Raw prices have no adjusted close, so
returns use pct_chg and the ST / suspension / limit-up eligibility flags are
not available before 2015 (a price + liquidity filter is applied instead).

Factor directions follow the existing style_factors convention:
  factor_size_z      large-cap positive  -> small_cap score = -z(size)
  factor_liquidity_z low-turnover positive (already low-turnover)
  factor_growth_z    growth positive

Outputs are research artifacts written to --outdir (outside the repository).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_research.style_factors import compute_factors
from portfolio_backtester.style_factors_backtest import build_quantile_portfolio_returns
from style_factors.data import (
    load_fina_indicator,
    load_holder_structure,
    load_moneyflow_ths,
    load_sw_industry_membership,
)

# ---------------------------------------------------------------- data paths

CLEAN_DAILY = (
    "assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"
)
RAW_DAILY = "assets/tushare/a_share/daily/a_share_all_daily_latest/data"
RAW_BASIC = "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"
TOP800_PIT = "assets/universe/a_share_all_full_by_date.csv"

FACTOR_SIGNALS = {
    "small_cap": ("factor_size_z", -1.0),
    "low_turnover": ("factor_liquidity_z", 1.0),
    "growth": ("factor_growth_z", 1.0),
}

# ------------------------------------------------------------------ utilities


def _zscore(s: pd.Series) -> pd.Series:
    std = s.std(ddof=0)
    return (s - s.mean()) / std if std > 0 else s * 0


def _direction_score(panel: pd.DataFrame, col: str, sign: float) -> pd.Series:
    return sign * _zscore(panel[col])


def return_stats(returns: pd.Series) -> dict[str, float]:
    returns = returns.dropna().sort_index()
    if returns.empty:
        return {"total_return": np.nan, "annual_return": np.nan, "annual_vol": np.nan,
                "sharpe": np.nan, "max_drawdown": np.nan}
    nav = (1 + returns).cumprod()
    drawdown = nav / nav.cummax() - 1
    years = len(returns) / 252
    return {
        "total_return": float(nav.iloc[-1] - 1),
        "annual_return": float(nav.iloc[-1] ** (1 / years) - 1),
        "annual_vol": float(returns.std() * np.sqrt(252)),
        "sharpe": float(returns.mean() / returns.std() * np.sqrt(252)),
        "max_drawdown": float(drawdown.min()),
    }


def yearly_returns(returns: pd.Series) -> pd.Series:
    returns = returns.dropna()
    return (1 + returns).groupby(returns.index.year).prod() - 1


# ------------------------------------------------------- phase 1 factor panel


def _read_clean_formation(path: Path, formation_keys: set[str]) -> pd.DataFrame:
    columns = [
        "trade_date", "symbol", "amount", "adj_close", "is_suspended",
        "is_st", "list_date", "listed_days",
    ]
    frame = pd.read_parquet(path, columns=columns)
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["amount_cny"] = pd.to_numeric(frame["amount"], errors="coerce") * 1000.0
    frame["medadv20_cny"] = frame["amount_cny"].rolling(20, min_periods=10).median()
    return frame.loc[frame["trade_date"].isin(formation_keys)].copy()


def _read_raw_formation_partition(path: Path, formation_keys: set[str]) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["symbol"] = frame["symbol"].astype(str)
    frame["amount_cny"] = pd.to_numeric(frame["amount"], errors="coerce") * 1000.0
    frame["medadv20_cny"] = frame["amount_cny"].rolling(20, min_periods=10).median()
    frame = frame.loc[frame["trade_date"].isin(formation_keys)].copy()
    frame["listed_days"] = np.nan
    frame["adj_close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["is_suspended"] = False
    frame["is_st"] = False
    return frame


def load_formation_eligibility(
    data_root: Path, formation_dates: pd.DatetimeIndex, *, workers: int,
    source: str = "clean",
) -> pd.DataFrame:
    keys = {d.strftime("%Y%m%d") for d in formation_dates}
    if source == "raw":
        part_dir = data_root / RAW_DAILY
        files = sorted(part_dir.glob("trade_date=*"))
        reader = _read_raw_formation_partition
        result_parts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            future_to_file = {
                ex.submit(reader, f, keys): f for f in files
                if _partition_date_key(f.name) in keys
            }
            for future in concurrent.futures.as_completed(future_to_file):
                part = future.result()
                if not part.empty:
                    result_parts.append(part)
        result = pd.concat(result_parts, ignore_index=True) if result_parts else pd.DataFrame()
        result["trade_date"] = pd.to_datetime(result["trade_date"], format="%Y%m%d")
        return result.drop_duplicates(["trade_date", "symbol"], keep="last")
    files = sorted((data_root / CLEAN_DAILY).glob("*.parquet"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(lambda p: _read_clean_formation(p, keys), files))
    result = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    result["trade_date"] = pd.to_datetime(result["trade_date"], format="%Y%m%d")
    return result.drop_duplicates(["trade_date", "symbol"], keep="last")


def _partition_date_key(name: str) -> str:
    return name.split("=", 1)[1] if name.startswith("trade_date=") else ""


def build_phase1_factor_panel(
    data_root: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    min_listed_days: int,
    min_medadv_cny: float,
    workers: int,
    panel_cache: Path | None,
    source: str = "clean",
) -> pd.DataFrame:
    from style_factors.workflow import load_data  # local import to avoid cycle

    if panel_cache is not None and panel_cache.exists():
        panel = pd.read_parquet(panel_cache)
        panel["trade_date"] = pd.to_datetime(panel["trade_date"])
        return panel

    daily, basics = load_data(data_root, start_date=start.date().isoformat(),
                              basics_rebalance_only=True)
    all_dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
    rebalance_dates = (
        pd.Series(all_dates)
        .groupby([all_dates.year, all_dates.month])
        .last()
        .sort_index()
        .to_numpy()
    )
    rdi = pd.DatetimeIndex(rebalance_dates)
    fina = load_fina_indicator(data_root)
    sw = load_sw_industry_membership(data_root)
    moneyflow = load_moneyflow_ths(data_root, start_date=start.date().isoformat())
    holder = load_holder_structure(data_root, start_date=start.date().isoformat())
    basics_extra = (
        basics.loc[
            basics["trade_date"].isin(rdi),
            ["trade_date", "symbol", "dv_ttm", "ps_ttm"],
        ].copy()
        if {"dv_ttm", "ps_ttm"} <= set(basics.columns)
        else pd.DataFrame()
    )
    aux = {
        "moneyflow_ths": moneyflow if not moneyflow.empty else None,
        "holder_structure": holder if not holder.empty else None,
        "daily_basic_extra": basics_extra if not basics_extra.empty else None,
    }
    factors = compute_factors(
        daily, basics,
        fina if not fina.empty else None,
        sw_membership=sw if not sw.empty else None,
        aux=aux, rebalance_dates=rdi,
    )
    factors = factors.loc[factors["trade_date"] <= end].copy()

    formation_dates = pd.DatetimeIndex(sorted(factors["trade_date"].unique()))
    eligibility = load_formation_eligibility(
        data_root, formation_dates, workers=workers, source=source,
    )
    panel = factors.merge(eligibility, on=["trade_date", "symbol"], how="left")
    if source == "raw":
        mask = (
            panel["medadv20_cny"].ge(min_medadv_cny)
            & panel["adj_close"].gt(0)
        )
    else:
        mask = (
            panel["listed_days"].ge(min_listed_days)
            & panel["medadv20_cny"].ge(min_medadv_cny)
            & panel["adj_close"].gt(0)
            & ~panel["is_suspended"].fillna(True)
            & ~panel["is_st"].fillna(True)
        )
    panel = panel.loc[mask].copy()
    for name, (col, sign) in FACTOR_SIGNALS.items():
        if col in panel.columns:
            panel[name + "_score"] = _direction_score(panel, col, sign)
        else:
            panel[name + "_score"] = np.nan
    if panel_cache is not None:
        panel.to_parquet(panel_cache, index=False)
    return panel


def load_pit_top800(data_root: Path, trade_dates: pd.DatetimeIndex) -> pd.DataFrame:
    frame = pd.read_csv(data_root / TOP800_PIT)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
    frame = frame[frame["trade_date"].isin(trade_dates)]
    frame["rank"] = frame.groupby("trade_date")["liq_metric"].rank(
        ascending=False, method="first"
    )
    top = frame[frame["rank"] <= 800].copy()
    return top[["trade_date", "symbol"]]


def apply_universe(panel: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    return panel.merge(universe, on=["trade_date", "symbol"], how="inner")


# -------------------------------------------------- frictionless Q1-Q5 curves


def build_quantile_curves(panel: pd.DataFrame, daily, rebalance_dates):
    signals = {name: name + "_score" for name in FACTOR_SIGNALS}
    return build_quantile_portfolio_returns(
        panel, daily, rebalance_dates, signals,
        n_quantiles=5, requested_quantiles=(1, 5),
        include_universe=True,
    )


# ----------------------------------------------- costed long-only Top-K backtest


def _load_pricing_file(path: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    columns = [
        "trade_date", "symbol", "adj_close", "amount", "is_suspended",
        "is_st", "is_limit_up", "is_limit_down", "listed_days",
    ]
    frame = pd.read_parquet(path, columns=columns)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
    frame = frame.sort_values("trade_date")
    frame["amount_cny"] = pd.to_numeric(frame["amount"], errors="coerce") * 1000.0
    frame["medadv20_cny"] = frame["amount_cny"].rolling(20, min_periods=10).median()
    frame = frame.loc[frame["trade_date"].between(start, end)].copy()
    base = frame["adj_close"].gt(0) & ~frame["is_suspended"].fillna(True)
    frame["buy_tradable"] = (
        base & ~frame["is_st"].fillna(True) & ~frame["is_limit_up"].fillna(False)
    )
    frame["sell_tradable"] = base & ~frame["is_limit_down"].fillna(False)
    frame["ret"] = frame["adj_close"].pct_change()
    return frame


def _load_raw_pricing_partition(path: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
    frame["symbol"] = frame["symbol"].astype(str)
    frame = frame.sort_values("trade_date")
    frame["amount_cny"] = pd.to_numeric(frame["amount"], errors="coerce") * 1000.0
    frame["medadv20_cny"] = frame["amount_cny"].rolling(20, min_periods=10).median()
    frame = frame.loc[frame["trade_date"].between(start, end)].copy()
    frame["adj_close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["buy_tradable"] = frame["adj_close"].gt(0) & frame["amount_cny"].ge(0)
    frame["sell_tradable"] = frame["adj_close"].gt(0)
    frame["ret"] = pd.to_numeric(frame["pct_chg"], errors="coerce") / 100.0
    return frame


def load_pricing(data_root: Path, symbols: set[str], start, end, *, workers: int,
                 source: str = "clean") -> pd.DataFrame:
    if source == "raw":
        part_dir = data_root / RAW_DAILY
        files = sorted(part_dir.glob("trade_date=*"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            future_to_file = {
                ex.submit(_load_raw_pricing_partition, f, start, end): f for f in files
            }
            parts = []
            for future in concurrent.futures.as_completed(future_to_file):
                part = future.result()
                if not part.empty:
                    parts.append(part)
        result = pd.concat(list(parts), ignore_index=True) if parts else pd.DataFrame()
        return result.loc[result["symbol"].isin(symbols)].drop_duplicates(
            ["trade_date", "symbol"], keep="last"
        ).sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    files = [data_root / CLEAN_DAILY / f"{s}.parquet" for s in sorted(symbols)]
    files = [f for f in files if f.exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(lambda p: _load_pricing_file(p, start, end), files))
    result = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    return result.drop_duplicates(["trade_date", "symbol"], keep="last").sort_values(
        ["trade_date", "symbol"]
    ).reset_index(drop=True)


def _trade_dates(daily, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
    return dates[(dates >= start) & (dates <= end)]


def _next_trading_day(date: pd.Timestamp, trade_dates: pd.DatetimeIndex) -> pd.Timestamp | None:
    later = trade_dates[trade_dates > date]
    return later[0] if len(later) else None


def long_only_topk_backtest(
    panel: pd.DataFrame,
    pricing: pd.DataFrame,
    trade_dates: pd.DatetimeIndex,
    *,
    score_col: str,
    top_k: int,
    cost_bps: float,
) -> pd.Series:
    """Monthly equal-weight long-only Top-K with next-day execution and costs.

    Each rebalance targets exactly the current Top-K names.  Names that drop out
    of the Top-K are sold at the next execution date; a name that cannot be sold
    (e.g. limit-down) is held one more period and counted toward turnover later.
    Entry is screened by buy_tradable.  Daily returns are the equal-weighted mean
    of held names' returns; a per-rebalance turnover cost is deducted on the
    execution day.
    """
    reb_dates = sorted(
        pd.Timestamp(d).normalize()
        for d in sorted(panel["trade_date"].unique())
    )
    pricing = pricing.set_index(["trade_date", "symbol"])
    pricing = pricing.sort_index()
    pricing_ret = pricing["ret"]
    entry_dates = set(pricing.index.get_level_values(0))

    daily_returns: dict[pd.Timestamp, float] = {}
    prev_holdings: set[str] = set()

    for i, reb in enumerate(reb_dates):
        entry = _next_trading_day(reb, trade_dates)
        if entry is None:
            break
        next_reb = reb_dates[i + 1] if i + 1 < len(reb_dates) else trade_dates[-1]

        day_rows = panel[panel["trade_date"] == reb]
        day_rows = day_rows.dropna(subset=[score_col])
        day_rows = day_rows.sort_values(score_col, ascending=False)
        top = set(day_rows.head(top_k)["symbol"].tolist())
        if not top:
            continue

        if entry not in entry_dates:
            continue
        tradable = pricing.xs(entry, level=0)
        buyable = {s for s in top if s in tradable.index and tradable.loc[s, "buy_tradable"]}
        sellable = {s for s in (prev_holdings - top)
                    if s in tradable.index and tradable.loc[s, "sell_tradable"]}

        # stuck names were intended to be sold but cannot (e.g. limit-down);
        # they are held one more period and count toward turnover on the retry.
        prev_stuck = {s for s in prev_holdings
                      if s in tradable.index and not tradable.loc[s, "sell_tradable"]}
        held = buyable | prev_stuck
        if not held:
            prev_holdings = set()
            continue

        turnover_count = len(buyable) + len(sellable) + len(prev_stuck)
        turnover_frac = turnover_count / top_k

        window = pricing_ret.loc[
            (pricing_ret.index.get_level_values(0) > entry)
            & (pricing_ret.index.get_level_values(0) <= next_reb)
        ]
        if window.empty:
            prev_holdings = held
            continue
        held_pct = window[window.index.get_level_values(1).isin(held)].reset_index()
        if held_pct.empty:
            prev_holdings = held
            continue
        daily = held_pct.groupby("trade_date")["ret"].mean()
        for dt, r in daily.items():
            daily_returns[dt] = daily_returns.get(dt, 1.0) * (1 + r) - 1

        cost = turnover_frac * cost_bps / 1e4
        daily_returns[entry] = (1 + daily_returns.get(entry, 0.0)) * (1 - cost) - 1
        prev_holdings = held

    series = pd.Series(daily_returns).sort_index()
    series.name = score_col
    return series


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--phase", type=int, default=1, choices=[1, 2])
    ap.add_argument("--start-date", default="2015-01-01")
    ap.add_argument("--end-date", default="2026-08-18")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--top-k", type=int, default=100)
    ap.add_argument("--cost-bps", type=float, default=30.0)
    ap.add_argument("--min-listed-days", type=int, default=180)
    ap.add_argument("--min-medadv-cny", type=float, default=20_000_000.0)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--universe", choices=["full", "top800"], default="full")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)
    source = "raw" if args.phase == 2 else "clean"

    print(f"[phase {args.phase}] building factor panel {start.date()} ~ {end.date()} "
          f"(source={source})", flush=True)
    panel_cache = outdir / f"panel_p{args.phase}_{args.universe}.parquet"
    panel = build_phase1_factor_panel(
        data_root, start, end,
        min_listed_days=args.min_listed_days,
        min_medadv_cny=args.min_medadv_cny,
        workers=args.workers,
        panel_cache=None,
        source=source,
    )
    if args.universe == "top800":
        universe = load_pit_top800(
            data_root, pd.DatetimeIndex(sorted(panel["trade_date"].unique()))
        )
        panel = apply_universe(panel, universe)
        panel_cache = outdir / f"panel_p{args.phase}_top800.parquet"
    panel.to_parquet(panel_cache, index=False)
    print(f"[panel] {len(panel)} rows, {panel['trade_date'].nunique()} dates -> {panel_cache}",
          flush=True)

    from style_factors.workflow import load_data
    daily, _ = load_data(data_root, start_date=start.date().isoformat(),
                         basics_rebalance_only=False)
    trade_dates = _trade_dates(daily, start, end)
    reb_dates = pd.DatetimeIndex(sorted(panel["trade_date"].unique()))

    print("[curves] frictionless long-only Q1/Q5 quantile legs", flush=True)
    curves = build_quantile_curves(panel, daily, reb_dates)
    curve_rows = []
    for name, res in curves.items():
        for q in (1, 5):
            s = res["quantiles"][q]
            if s is not None and not s.empty:
                curve_rows.append({"factor": name, "quantile": f"Q{q}",
                                   **return_stats(s)})
        if res["long_short"] is not None and not res["long_short"].empty:
            curve_rows.append({"factor": name, "quantile": "Q5-Q1",
                               **return_stats(res["long_short"])})
    curve_df = pd.DataFrame(curve_rows)
    curve_df.to_csv(outdir / f"long_only_quantiles_p{args.phase}_{args.universe}.csv",
                    index=False)
    print(curve_df.to_string(index=False))

    print("[topk] costed + tradable long-only Top-K backtest", flush=True)
    symbols = set(panel["symbol"].unique())
    pricing = load_pricing(data_root, symbols, start, end, workers=args.workers,
                           source=source)
    topk_rows = []
    topk_returns = {}
    variants = {f"{name}_score": name for name in FACTOR_SIGNALS}
    panel["composite_score"] = (
        panel.get("small_cap_score", 0) + panel.get("low_turnover_score", 0)
        + panel.get("growth_score", 0)
    )
    variants["composite_score"] = "composite"
    for score_col, label in variants.items():
        if score_col not in panel.columns:
            continue
        series = long_only_topk_backtest(
            panel, pricing, trade_dates,
            score_col=score_col, top_k=args.top_k, cost_bps=args.cost_bps,
        )
        topk_returns[label] = series
        row = {"variant": label, **return_stats(series)}
        topk_rows.append(row)
    topk_df = pd.DataFrame(topk_rows)
    topk_df.to_csv(outdir / f"long_only_topk_p{args.phase}_{args.universe}.csv", index=False)
    print(topk_df.to_string(index=False))

    print("[annual] yearly long-only Top-K returns", flush=True)
    annual_rows = []
    for label, series in topk_returns.items():
        for year, ret in yearly_returns(series).items():
            annual_rows.append({"variant": label, "year": year, "return": ret})
    annual_df = pd.DataFrame(annual_rows)
    annual_df.to_csv(outdir / f"long_only_annual_p{args.phase}_{args.universe}.csv",
                     index=False)

    pd.DataFrame(topk_returns).to_parquet(
        outdir / f"long_only_daily_returns_p{args.phase}_{args.universe}.parquet"
    )

    summary = {
        "phase": args.phase,
        "universe": args.universe,
        "source": source,
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "top_k": args.top_k,
        "cost_bps": args.cost_bps,
        "min_listed_days": args.min_listed_days,
        "min_medadv_cny": args.min_medadv_cny,
        "entry_rule": "next market trading day close",
        "tradability": (
            "non-ST, non-suspended, not limit-up on entry"
            if source == "clean"
            else "price > 0, non-negative amount (raw 2008 data has no ST/suspension/limit flags)"
        ),
        "returns": "adj_close pct change" if source == "clean" else "pct_chg (unadjusted)",
        "factors": list(FACTOR_SIGNALS),
        "growth_pre_2015": True,
    }
    (outdir / f"long_only_manifest_p{args.phase}_{args.universe}.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
