"""Compare composite-score portfolios with independent style-factor sleeves.

The experiment intentionally separates three layers:

1. source factor qualification (the existing Q5-Q1 series),
2. long-only portfolio construction (industry-balanced fixed-width or Q4), and
3. ideal versus capacity-constrained execution from the next trading day.

Outputs are research artifacts and belong outside the repository.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from portfolio_backtester.execution_sim import (
    SELL_UNTIL_NEXT_REBALANCE,
    ExecutionSimConfig,
    simulate_execution_adjusted_nav,
    simulate_ideal_daily_nav,
)
from style_factors.data import (
    load_fina_indicator,
    load_sw_industry_membership,
)
from style_factors.factor_calc import compute_factors
from portfolio_backtester import (
    SelectionSpec,
    attach_entry_dates,
    build_targets,
    combine_targets,
    target_turnover,
)


RAW_DAILY = "assets/tushare/a_share/daily/a_share_all_daily_latest/data"
RAW_BASIC = "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"
CLEAN_DAILY = "assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"
CSI300 = "assets/tushare/a_share/index_daily/a_share_all_index_daily_csi300_2015/data/part.parquet"
CSI800 = "assets/tushare/a_share/index_daily/a_share_all_index_daily_zj800/data/part.parquet"
SOURCE_FACTOR_DIR = "strategy_outputs/style-factors/weekly-20260808-v2"
BASE_VARIANT_NAMES = [
    *(
        f"{method}_{width}"
        for width in ("30", "50", "100", "200", "q4")
        for method in ("composite_111", "sleeve_equal")
    ),
    "composite_211_30",
    "sleeve_core_7030_100",
    "single_small_100",
    "single_lowturn_100",
    "single_growth_100",
]


def _partition_date(path: Path) -> pd.Timestamp | None:
    if not path.name.startswith("trade_date="):
        return None
    return pd.to_datetime(path.name.split("=", 1)[1], format="%Y%m%d", errors="coerce")


def _formation_partitions(directory: Path, start: pd.Timestamp, end: pd.Timestamp) -> list[Path]:
    dated = []
    for path in directory.glob("trade_date=*"):
        date = _partition_date(path)
        if date is not None and start <= date <= end:
            dated.append((date, path))
    monthly: dict[pd.Period, tuple[pd.Timestamp, Path]] = {}
    for date, path in dated:
        period = date.to_period("M")
        if period not in monthly or date > monthly[period][0]:
            monthly[period] = (date, path)
    # A partial current month is not a scheduled monthly rebalance.
    end_period = end.to_period("M")
    if end_period in monthly and monthly[end_period][0] < end + pd.offsets.MonthEnd(0):
        monthly.pop(end_period)
    return [path for _date, path in sorted(monthly.values())]


def _read_partitions(paths: Iterable[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_parquet(path)
        if "trade_date" not in frame:
            frame["trade_date"] = _partition_date(path)
        frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_factor_panel(data_root: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    daily_paths = _formation_partitions(data_root / RAW_DAILY, start, end)
    basic_paths = _formation_partitions(data_root / RAW_BASIC, start, end)
    daily = _read_partitions(daily_paths)
    basics = _read_partitions(basic_paths)
    dates = pd.DatetimeIndex(sorted(set(daily["trade_date"]) & set(basics["trade_date"])))
    daily = daily.loc[daily["trade_date"].isin(dates)]
    basics = basics.loc[basics["trade_date"].isin(dates)]
    fina = load_fina_indicator(data_root, end_date=end)
    industries = load_sw_industry_membership(data_root)
    factors = compute_factors(
        daily,
        basics,
        fina if not fina.empty else None,
        sw_membership=industries if not industries.empty else None,
        rebalance_dates=dates,
    )
    keep = [
        "trade_date",
        "symbol",
        "industry_l1",
        "factor_size_z",
        "factor_liquidity_z",
        "factor_growth_z",
    ]
    factors = factors[[column for column in keep if column in factors]].copy()
    factors["small_score"] = -factors["factor_size_z"]
    factors["lowturn_score"] = factors["factor_liquidity_z"]
    factors["growth_score"] = factors.get("factor_growth_z", np.nan)
    return factors


def _read_clean_formation_file(path: Path, formation_keys: set[str]) -> pd.DataFrame:
    columns = [
        "trade_date",
        "symbol",
        "amount",
        "adj_close",
        "is_suspended",
        "is_st",
        "listed_days",
    ]
    frame = pd.read_parquet(path, columns=columns)
    frame["trade_date"] = frame["trade_date"].astype(str)
    frame["amount_cny"] = pd.to_numeric(frame["amount"], errors="coerce") * 1000.0
    frame["medadv20_cny"] = frame["amount_cny"].rolling(20, min_periods=10).median()
    return frame.loc[frame["trade_date"].isin(formation_keys)].copy()


def load_formation_eligibility(
    data_root: Path,
    formation_dates: pd.DatetimeIndex,
    *,
    workers: int,
) -> pd.DataFrame:
    files = sorted((data_root / CLEAN_DAILY).glob("*.parquet"))
    keys = {date.strftime("%Y%m%d") for date in formation_dates}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(lambda path: _read_clean_formation_file(path, keys), files))
    result = pd.concat([part for part in parts if not part.empty], ignore_index=True)
    result["trade_date"] = pd.to_datetime(result["trade_date"], format="%Y%m%d")
    return result.drop_duplicates(["trade_date", "symbol"], keep="last")


def eligible_factor_panel(
    factors: pd.DataFrame,
    eligibility: pd.DataFrame,
    *,
    min_listed_days: int,
    min_medadv_cny: float,
) -> pd.DataFrame:
    panel = factors.merge(eligibility, on=["trade_date", "symbol"], how="left")
    mask = (
        panel["listed_days"].ge(min_listed_days)
        & panel["medadv20_cny"].ge(min_medadv_cny)
        & panel["adj_close"].gt(0)
        & ~panel["is_suspended"].fillna(True)
        & ~panel["is_st"].fillna(True)
    )
    return panel.loc[mask].copy()


def _selection_spec(width: str) -> SelectionSpec:
    if width == "q4":
        return SelectionSpec(top_fraction=0.20)
    return SelectionSpec(top_k=int(width))


def build_variant_targets(panel: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    widths = ["30", "50", "100", "200", "q4"]
    variants: dict[str, pd.DataFrame] = {}
    metadata: dict[str, Any] = {"width_definition": {}}
    complete = panel.dropna(subset=["small_score", "lowturn_score", "growth_score"]).copy()
    complete["composite_111"] = (
        complete["small_score"] + complete["lowturn_score"] + complete["growth_score"]
    )
    complete["composite_211"] = (
        2 * complete["small_score"] + complete["lowturn_score"] + complete["growth_score"]
    )

    sleeves_by_width: dict[str, dict[str, pd.DataFrame]] = {}
    for width in widths:
        spec = _selection_spec(width)
        variants[f"composite_111_{width}"] = build_targets(
            complete, score_col="composite_111", spec=spec
        )
        sleeves = {
            "small": build_targets(
                panel.dropna(subset=["small_score"]), score_col="small_score", spec=spec
            ),
            "lowturn": build_targets(
                panel.dropna(subset=["lowturn_score"]), score_col="lowturn_score", spec=spec
            ),
            "growth": build_targets(
                panel.dropna(subset=["growth_score"]), score_col="growth_score", spec=spec
            ),
        }
        sleeves_by_width[width] = sleeves
        variants[f"sleeve_equal_{width}"] = combine_targets(
            sleeves, {"small": 1 / 3, "lowturn": 1 / 3, "growth": 1 / 3}
        )
        metadata["width_definition"][width] = (
            "top 20% within every industry" if width == "q4" else f"top {width} per sleeve"
        )

    variants["composite_211_30"] = build_targets(
        complete, score_col="composite_211", spec=SelectionSpec(top_k=30)
    )
    variants["sleeve_core_7030_100"] = combine_targets(
        {key: sleeves_by_width["100"][key] for key in ("small", "lowturn")},
        {"small": 0.30, "lowturn": 0.70},
    )
    for name, targets in sleeves_by_width["100"].items():
        variants[f"single_{name}_100"] = targets
    metadata["sleeves_100"] = sleeves_by_width["100"]
    return variants, metadata


def load_cached_variant_targets(outdir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    paths = {name: outdir / f"targets_{name}.parquet" for name in BASE_VARIANT_NAMES}
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"cached targets are missing: {missing}")
    variants = {name: pd.read_parquet(path) for name, path in paths.items()}
    for targets in variants.values():
        targets["rebalance_date"] = pd.to_datetime(targets["rebalance_date"])
    metadata: dict[str, Any] = {
        "width_definition": {
            width: ("top 20% within every industry" if width == "q4" else f"top {width} per sleeve")
            for width in ("30", "50", "100", "200", "q4")
        },
        "sleeves_100": {
            name: variants[f"single_{name}_100"] for name in ("small", "lowturn", "growth")
        },
    }
    return variants, metadata


def _read_pricing_file(
    path: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    columns = [
        "trade_date",
        "symbol",
        "adj_close",
        "amount",
        "is_suspended",
        "is_st",
        "is_limit_up",
        "is_limit_down",
        "listed_days",
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
    return frame


def load_pricing(
    data_root: Path,
    symbols: set[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    workers: int,
) -> pd.DataFrame:
    files = [data_root / CLEAN_DAILY / f"{symbol}.parquet" for symbol in sorted(symbols)]
    files = [path for path in files if path.exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(lambda path: _read_pricing_file(path, start, end), files))
    result = pd.concat([part for part in parts if not part.empty], ignore_index=True)
    result = result.drop_duplicates(["trade_date", "symbol"], keep="last")
    return result.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def _daily_returns(result: Any) -> pd.Series:
    daily = result.daily.copy()
    daily["trade_date"] = pd.to_datetime(daily["trade_date"].astype(str), format="%Y%m%d")
    return daily.set_index("trade_date")["executed_return"].astype(float).sort_index()


def return_stats(returns: pd.Series) -> dict[str, Any]:
    returns = returns.dropna().sort_index()
    nav = (1 + returns).cumprod()
    drawdown = nav / nav.cummax() - 1
    years = len(returns) / 252
    underwater = drawdown.lt(0)
    groups = underwater.ne(underwater.shift()).cumsum()
    runs = underwater.groupby(groups).agg(["first", "size"])
    longest = int(runs.loc[runs["first"], "size"].max()) if underwater.any() else 0
    return {
        "start": returns.index.min().date().isoformat(),
        "end": returns.index.max().date().isoformat(),
        "observations": int(len(returns)),
        "total_return": float(nav.iloc[-1] - 1),
        "annual_return": float(nav.iloc[-1] ** (1 / years) - 1),
        "annual_vol": float(returns.std() * np.sqrt(252)),
        "sharpe": float(returns.mean() / returns.std() * np.sqrt(252)),
        "max_drawdown": float(drawdown.min()),
        "longest_underwater_trading_days": longest,
    }


def active_stats(returns: pd.Series, benchmark: pd.Series) -> dict[str, float]:
    aligned = pd.concat(
        [returns.rename("strategy"), benchmark.rename("benchmark")], axis=1, sort=False
    )
    aligned = aligned.dropna()
    excess = aligned["strategy"] - aligned["benchmark"]
    tracking_error = float(excess.std() * np.sqrt(252))
    relative_nav = (1 + aligned["strategy"]).cumprod() / (1 + aligned["benchmark"]).cumprod()
    return {
        "relative_total_return": float(relative_nav.iloc[-1] - 1),
        "annualized_arithmetic_excess": float(excess.mean() * 252),
        "tracking_error": tracking_error,
        "information_ratio": float(excess.mean() * 252 / tracking_error),
    }


def _index_returns(path: Path, symbol: str) -> pd.Series:
    frame = pd.read_parquet(path)
    frame = frame.loc[frame["symbol"].eq(symbol)].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
    return frame.sort_values("trade_date").set_index("trade_date")["pct_chg"] / 100.0


def load_benchmarks(data_root: Path, equal_weight_csv: Path | None) -> dict[str, pd.Series]:
    benchmarks = {
        "csi300": _index_returns(data_root / CSI300, "000300.SH"),
        "csi800": _index_returns(data_root / CSI800, "000906.SH"),
    }
    if equal_weight_csv is not None and equal_weight_csv.exists():
        frame = pd.read_csv(equal_weight_csv)
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        benchmarks["equal_weight_800"] = frame.set_index("trade_date")["return"].astype(float)
    return benchmarks


def _source_factor_returns(data_root: Path) -> dict[str, pd.Series]:
    output = {}
    for name, sign in (("small", -1.0), ("lowturn", 1.0), ("growth", 1.0)):
        source = {"small": "size", "lowturn": "liquidity", "growth": "growth"}[name]
        frame = pd.read_csv(data_root / SOURCE_FACTOR_DIR / f"factor_{source}_daily.csv")
        dates = pd.to_datetime(frame.iloc[:, 0])
        values = pd.to_numeric(frame.iloc[:, 1], errors="coerce").to_numpy()
        output[name] = pd.Series(values * sign, index=dates, name=name)
    return output


def _risk_budget_allocations(
    daily_returns: pd.DataFrame,
    rebalance_dates: Iterable[pd.Timestamp],
    *,
    small_cap: float = 0.30,
) -> pd.DataFrame:
    rows = []
    sleeves = ["small", "lowturn"]
    for date in sorted(pd.to_datetime(list(rebalance_dates))):
        history = daily_returns.loc[:date, sleeves].tail(252)
        vols = (
            history.std() * np.sqrt(252) if len(history) >= 126 else pd.Series(1.0, index=sleeves)
        )
        inverse = 1 / vols.replace(0, np.nan)
        raw_small = float(inverse["small"] / inverse.sum()) if inverse.notna().all() else 0.5
        small = min(raw_small, small_cap)
        rows.extend(
            [
                {"rebalance_date": date, "sleeve": "small", "allocation": small},
                {"rebalance_date": date, "sleeve": "lowturn", "allocation": 1 - small},
            ]
        )
    return pd.DataFrame(rows)


def _position_diagnostics(targets: pd.DataFrame, panel: pd.DataFrame) -> dict[str, float]:
    merged = targets[["rebalance_date", "symbol", "weight"]].merge(
        panel[["trade_date", "symbol", "small_score", "lowturn_score", "growth_score"]],
        left_on=["rebalance_date", "symbol"],
        right_on=["trade_date", "symbol"],
        how="left",
    )
    result = {
        "mean_names": float(targets.groupby("rebalance_date")["symbol"].nunique().mean()),
        "max_single_weight": float(targets["weight"].max()),
        "mean_target_turnover": float(target_turnover(targets).iloc[1:].mean()),
    }
    for factor in ("small_score", "lowturn_score", "growth_score"):
        result[f"weighted_{factor}"] = float(
            (merged["weight"] * merged[factor]).sum() / merged["weight"].sum()
        )
    return result


def _run_ideal(
    targets: pd.DataFrame,
    pricing: pd.DataFrame,
    trade_dates: pd.DatetimeIndex,
    *,
    cost_bps: float,
    portfolio_value: float,
) -> tuple[pd.Series, dict[str, Any]]:
    positions = attach_entry_dates(targets, trade_dates)
    target_symbols = set(targets["symbol"].unique())
    local_pricing = pricing.loc[pricing["symbol"].isin(target_symbols)]
    result = simulate_ideal_daily_nav(
        positions,
        local_pricing,
        price_col="adj_close",
        transaction_cost_bps=cost_bps,
        portfolio_value=portfolio_value,
    )
    if result.summary.get("status") != "ok":
        raise RuntimeError(f"ideal simulation failed: {result.summary}")
    return _daily_returns(result), result.summary


def _run_capacity(
    targets: pd.DataFrame,
    pricing: pd.DataFrame,
    trade_dates: pd.DatetimeIndex,
    *,
    cost_bps: float,
    portfolio_value: float,
    participation_rate: float,
) -> tuple[pd.Series, dict[str, Any]]:
    positions = attach_entry_dates(targets, trade_dates)
    target_symbols = set(targets["symbol"].unique())
    local_pricing = pricing.loc[pricing["symbol"].isin(target_symbols)]
    config = ExecutionSimConfig(
        enabled=True,
        portfolio_value=portfolio_value,
        participation_rate=participation_rate,
        liquidity_cols=("medadv20_cny", "amount_cny"),
        buy_max_days=10,
        sell_max_days=SELL_UNTIL_NEXT_REBALANCE,
        zero_fill_abort_days_buy=5,
        unfilled_buy_action="keep_cash",
        unfilled_sell_action="keep_position",
    )
    result = simulate_execution_adjusted_nav(
        positions,
        local_pricing,
        config,
        price_col="adj_close",
        buy_tradable_col="buy_tradable",
        sell_tradable_col="sell_tradable",
        transaction_cost_bps=cost_bps,
    )
    if result.summary.get("status") != "ok":
        raise RuntimeError(f"capacity simulation failed: {result.summary}")
    return _daily_returns(result), result.summary


def _quality_report(
    panel: pd.DataFrame,
    pricing: pd.DataFrame,
    variants: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    returns = (
        pricing.sort_values(["symbol", "trade_date"]).groupby("symbol")["adj_close"].pct_change()
    )
    return {
        "factor_duplicate_rows": int(panel.duplicated(["trade_date", "symbol"]).sum()),
        "pricing_duplicate_rows": int(pricing.duplicated(["trade_date", "symbol"]).sum()),
        "factor_dates": int(panel["trade_date"].nunique()),
        "eligible_names_median": float(panel.groupby("trade_date")["symbol"].nunique().median()),
        "growth_coverage": float(panel["growth_score"].notna().mean()),
        "industry_coverage": float(panel["industry_l1"].notna().mean()),
        "nonpositive_prices": int(pricing["adj_close"].le(0).sum()),
        "seasoned_price_returns_over_50pct": int(returns.abs().gt(0.50).sum()),
        "target_contracts": len(variants),
    }


def run(args: argparse.Namespace) -> None:
    data_root = Path(args.data_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp(args.start_date)
    end = pd.Timestamp(args.end_date)

    panel_path = outdir / "eligible_factor_panel.parquet"
    if args.reuse_panel and panel_path.exists():
        print(f"[1-2/7] reusing {panel_path}", flush=True)
        panel = pd.read_parquet(panel_path)
        panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    else:
        print("[1/7] building monthly factor panel", flush=True)
        factors = build_factor_panel(data_root, start - pd.offsets.MonthEnd(1), end)
        print("[2/7] loading point-in-time eligibility", flush=True)
        eligibility = load_formation_eligibility(
            data_root, pd.DatetimeIndex(factors["trade_date"].unique()), workers=args.workers
        )
        panel = eligible_factor_panel(
            factors,
            eligibility,
            min_listed_days=args.min_listed_days,
            min_medadv_cny=args.min_medadv_cny,
        )
        panel = panel.loc[panel["trade_date"].ge(start - pd.offsets.MonthEnd(1))].copy()
        panel.to_parquet(panel_path, index=False)

    print("[3/7] constructing composite and sleeve target matrix", flush=True)
    if args.reuse_targets:
        variants, construction_meta = load_cached_variant_targets(outdir)
    else:
        variants, construction_meta = build_variant_targets(panel)
    for name, targets in variants.items():
        targets.to_parquet(outdir / f"targets_{name}.parquet", index=False)
    symbols = {symbol for target in variants.values() for symbol in target["symbol"].unique()}
    calendar_dates = sorted(
        date
        for path in (data_root / RAW_DAILY).glob("trade_date=*")
        if (date := _partition_date(path)) is not None and start <= date <= end
    )
    trade_dates = pd.DatetimeIndex(calendar_dates)

    print(f"[4/7] loading pricing for {len(symbols)} selected symbols", flush=True)
    pricing = load_pricing(data_root, symbols, start, end, workers=args.workers)
    benchmarks = load_benchmarks(
        data_root, Path(args.equal_weight_csv) if args.equal_weight_csv else None
    )

    print(f"[5/7] simulating {len(variants)} ideal portfolios", flush=True)
    net_returns: dict[str, pd.Series] = {}
    gross_returns: dict[str, pd.Series] = {}
    summaries: dict[str, Any] = {}
    gross_required = {
        "composite_211_30",
        "composite_111_100",
        "sleeve_equal_100",
        "sleeve_core_7030_100",
    }
    for name, targets in variants.items():
        print(f"  ideal {name}", flush=True)
        cache_path = outdir / f"cache_ideal_net_{name}.parquet"
        if cache_path.exists():
            cached = pd.read_parquet(cache_path)
            net = cached.set_index("trade_date")["return"]
            summary = {"status": "ok", "cache": str(cache_path.name)}
        else:
            net, summary = _run_ideal(
                targets,
                pricing,
                trade_dates,
                cost_bps=args.cost_bps,
                portfolio_value=args.portfolio_value,
            )
            net.rename("return").rename_axis("trade_date").reset_index().to_parquet(
                cache_path, index=False
            )
        if name in gross_required:
            gross_cache = outdir / f"cache_ideal_gross_{name}.parquet"
            if gross_cache.exists():
                cached = pd.read_parquet(gross_cache)
                gross = cached.set_index("trade_date")["return"]
            else:
                gross, _ = _run_ideal(
                    targets,
                    pricing,
                    trade_dates,
                    cost_bps=0.0,
                    portfolio_value=args.portfolio_value,
                )
                gross.rename("return").rename_axis("trade_date").reset_index().to_parquet(
                    gross_cache, index=False
                )
            gross_returns[name] = gross
        net_returns[name] = net
        summaries[name] = {"ideal_engine": summary}

    sleeve_return_frame = pd.DataFrame(
        {
            name.removeprefix("single_").removesuffix("_100"): net_returns[name]
            for name in ("single_small_100", "single_lowturn_100", "single_growth_100")
        }
    )
    sleeve_targets = construction_meta.pop("sleeves_100")
    allocations = _risk_budget_allocations(
        sleeve_return_frame,
        sleeve_targets["small"]["rebalance_date"].unique(),
        small_cap=0.30,
    )
    variants["sleeve_risk_budget_100"] = combine_targets(
        {key: sleeve_targets[key] for key in ("small", "lowturn")}, allocations
    )
    variants["sleeve_risk_budget_100"].to_parquet(
        outdir / "targets_sleeve_risk_budget_100.parquet", index=False
    )
    risk_net_cache = outdir / "cache_ideal_net_sleeve_risk_budget_100.parquet"
    risk_gross_cache = outdir / "cache_ideal_gross_sleeve_risk_budget_100.parquet"
    if risk_net_cache.exists():
        cached = pd.read_parquet(risk_net_cache)
        risk_net = cached.set_index("trade_date")["return"]
        risk_summary = {"status": "ok", "cache": str(risk_net_cache.name)}
    else:
        risk_net, risk_summary = _run_ideal(
            variants["sleeve_risk_budget_100"],
            pricing,
            trade_dates,
            cost_bps=args.cost_bps,
            portfolio_value=args.portfolio_value,
        )
        risk_net.rename("return").rename_axis("trade_date").reset_index().to_parquet(
            risk_net_cache, index=False
        )
    if risk_gross_cache.exists():
        cached = pd.read_parquet(risk_gross_cache)
        risk_gross = cached.set_index("trade_date")["return"]
    else:
        risk_gross, _ = _run_ideal(
            variants["sleeve_risk_budget_100"],
            pricing,
            trade_dates,
            cost_bps=0.0,
            portfolio_value=args.portfolio_value,
        )
        risk_gross.rename("return").rename_axis("trade_date").reset_index().to_parquet(
            risk_gross_cache, index=False
        )
    net_returns["sleeve_risk_budget_100"] = risk_net
    gross_returns["sleeve_risk_budget_100"] = risk_gross
    summaries["sleeve_risk_budget_100"] = {"ideal_engine": risk_summary}
    allocations.to_csv(outdir / "risk_budget_allocations.csv", index=False)

    execution_names = [
        "composite_211_30",
        "composite_111_100",
        "sleeve_equal_100",
        "sleeve_core_7030_100",
        "sleeve_risk_budget_100",
    ]
    execution_returns: dict[str, pd.Series] = {}
    print(f"[6/7] capacity simulation for {execution_names}", flush=True)
    for name in execution_names:
        return_cache = outdir / f"cache_capacity_{name}.parquet"
        summary_cache = outdir / f"cache_capacity_{name}.json"
        if return_cache.exists() and summary_cache.exists():
            cached = pd.read_parquet(return_cache)
            executed = cached.set_index("trade_date")["return"]
            summary = json.loads(summary_cache.read_text(encoding="utf-8"))
        else:
            executed, summary = _run_capacity(
                variants[name],
                pricing,
                trade_dates,
                cost_bps=args.cost_bps,
                portfolio_value=args.portfolio_value,
                participation_rate=args.participation_rate,
            )
            executed.rename("return").rename_axis("trade_date").reset_index().to_parquet(
                return_cache, index=False
            )
            summary_cache.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        execution_returns[name] = executed
        summaries[name]["capacity_engine"] = summary

    print("[7/7] writing decision tables and audit artifacts", flush=True)
    metrics = []
    for name, returns in net_returns.items():
        row: dict[str, Any] = {"variant": name, "mode": "ideal_net", **return_stats(returns)}
        row.update(_position_diagnostics(variants[name], panel))
        if name in gross_returns:
            row["cost_drag_total_return"] = (
                return_stats(gross_returns[name])["total_return"] - row["total_return"]
            )
        for benchmark_name, benchmark in benchmarks.items():
            row.update(
                {
                    f"{benchmark_name}_{key}": value
                    for key, value in active_stats(returns, benchmark).items()
                }
            )
        metrics.append(row)
    for name, returns in execution_returns.items():
        row = {"variant": name, "mode": "capacity_net", **return_stats(returns)}
        row.update(_position_diagnostics(variants[name], panel))
        row["execution_drag_total_return"] = (
            return_stats(net_returns[name])["total_return"] - row["total_return"]
        )
        row["fill_ratio"] = summaries[name]["capacity_engine"].get("fill_ratio")
        for benchmark_name, benchmark in benchmarks.items():
            row.update(
                {
                    f"{benchmark_name}_{key}": value
                    for key, value in active_stats(returns, benchmark).items()
                }
            )
        metrics.append(row)
    metrics_frame = pd.DataFrame(metrics)
    metrics_frame.to_csv(outdir / "variant_metrics.csv", index=False)
    pd.DataFrame(net_returns).to_parquet(outdir / "ideal_net_daily_returns.parquet")
    pd.DataFrame(gross_returns).to_parquet(outdir / "ideal_gross_daily_returns.parquet")
    pd.DataFrame(execution_returns).to_parquet(outdir / "capacity_daily_returns.parquet")
    for name, targets in variants.items():
        targets.to_parquet(outdir / f"targets_{name}.parquet", index=False)

    source_stats = {
        name: return_stats(series.loc[series.index >= start])
        for name, series in _source_factor_returns(data_root).items()
    }
    benchmark_stats = {
        name: return_stats(series.loc[(series.index >= start) & (series.index <= end)])
        for name, series in benchmarks.items()
    }
    quality = _quality_report(panel, pricing, variants)
    manifest = {
        "parameters": {
            "start_date": args.start_date,
            "end_date": args.end_date,
            "min_listed_days": args.min_listed_days,
            "min_medadv_cny": args.min_medadv_cny,
            "cost_bps": args.cost_bps,
            "portfolio_value": args.portfolio_value,
            "participation_rate": args.participation_rate,
            "entry_rule": "next market trading day close",
            "industry_rule": "select within SW L1 and restore eligible-universe industry weights",
        },
        "construction": construction_meta,
        "source_q5_minus_q1": source_stats,
        "benchmarks": benchmark_stats,
        "data_quality": quality,
        "engine_summaries": summaries,
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(
        metrics_frame.sort_values(["mode", "annual_return"], ascending=[True, False]).to_string(
            index=False
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    parser.add_argument("--start-date", default="2016-01-01")
    parser.add_argument("--end-date", default="2026-08-11")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--equal-weight-csv")
    parser.add_argument("--min-listed-days", type=int, default=180)
    parser.add_argument("--min-medadv-cny", type=float, default=20_000_000)
    parser.add_argument("--cost-bps", type=float, default=30.0)
    parser.add_argument("--portfolio-value", type=float, default=10_000_000)
    parser.add_argument("--participation-rate", type=float, default=0.10)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--reuse-panel", action="store_true")
    parser.add_argument("--reuse-targets", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
