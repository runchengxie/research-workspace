#!/usr/bin/env python3
"""Backtest dividend-versus-growth ETF momentum with portfolio-backtester.

At each signal-day close, compare the trailing adjusted-close return of
515180.SH and 159967.SZ. Hold the stronger ETF from the next trading-day open.
The core/satellite variant keeps 60% in 512890.SH and rotates the other 40%.

This is an in-sample research diagnostic. It does not publish execution targets.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, NamedTuple, cast

import numpy as np
import pandas as pd

from portfolio_backtester import PositionBacktestConfig, run_position_backtest
from strategy_pipeline import (
    dividend_growth_momentum_audit as audit,
    dividend_growth_momentum_config as research_config,
    dividend_growth_momentum_report as report_builder,
    dividend_growth_momentum_reporting as reporting,
)
from strategy_pipeline.dividend_growth_momentum_audit import return_metrics as _return_metrics
from strategy_pipeline.dividend_growth_momentum_config import (
    ALL_STRATEGIES,
    ANNUAL_REPORT_STRATEGIES,
    AUDIT_STRATEGIES,
    BENCHMARK_PAIRS,
    DIVIDEND,
    GENERIC_DIVIDEND,
    GENERIC_GROWTH,
    GROWTH,
    LOW_VOL,
    SCREENSHOT_SYMBOL_NAMES,
    STRATEGIES,
    SYMBOL_NAMES,
    Frequency,
    StrategyDefinition,
)


@dataclass(frozen=True)
class BaseSuiteResult:
    metrics: pd.DataFrame
    sensitivity: pd.DataFrame
    daily: pd.DataFrame
    positions: pd.DataFrame
    nav: pd.DataFrame
    errors: dict[str, float]
    reference_periods: pd.DataFrame


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-prices", type=Path)
    source.add_argument("--refresh-tushare", action="store_true")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--token-env", default="TUSHARE_TOKEN_2")
    parser.add_argument("--start-date", default="20180101")
    parser.add_argument("--end-date", default="20260730")
    parser.add_argument("--lookback-days", type=int, default=20)
    parser.add_argument("--lookback-grid-days", default="10,20,40,60,120")
    parser.add_argument("--base-cost-bps", type=float, default=10.0)
    parser.add_argument("--cost-grid-bps", default="0,10,25,50")
    return parser


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_ready(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_tushare_prices(
    *,
    start_date: str,
    end_date: str,
    token_env: str,
    env_file: Path | None = None,
) -> pd.DataFrame:
    if env_file is not None:
        from dotenv import load_dotenv

        resolved = env_file.expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"environment file does not exist: {resolved}")
        load_dotenv(resolved, override=False)
    from market_data_platform.providers.tushare_common import get_tushare_client

    client = get_tushare_client(token_env=token_env)
    parts: list[pd.DataFrame] = []
    for symbol in SYMBOL_NAMES:
        daily = client.fund_daily(
            ts_code=symbol,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,trade_date,open,high,low,close,pre_close,vol,amount",
        )
        adjustment = client.fund_adj(
            ts_code=symbol,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,trade_date,adj_factor",
        )
        if daily.empty or adjustment.empty:
            raise ValueError(f"TuShare returned incomplete data for {symbol}")
        parts.append(
            daily.merge(
                adjustment,
                on=["ts_code", "trade_date"],
                how="inner",
                validate="one_to_one",
            )
        )
    return prepare_prices(pd.concat(parts, ignore_index=True))


def prepare_prices(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ts_code", "trade_date", "open", "close", "adj_factor"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"source prices are missing columns: {missing}")
    prices = frame.copy()
    prices["symbol"] = prices["ts_code"].astype(str)
    prices["trade_date"] = pd.to_datetime(prices["trade_date"], format="%Y%m%d", errors="coerce")
    for column in ("open", "close", "adj_factor"):
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    prices["adj_open"] = prices["open"] * prices["adj_factor"]
    prices["adj_close"] = prices["close"] * prices["adj_factor"]
    prices = prices.dropna(subset=["trade_date", "symbol", "adj_open", "adj_close"])
    prices = prices.loc[prices["symbol"].isin(SYMBOL_NAMES)].copy()
    prices = prices.sort_values(["trade_date", "symbol"]).drop_duplicates(
        ["trade_date", "symbol"],
        keep="last",
    )
    if set(prices["symbol"]) != set(SYMBOL_NAMES):
        raise ValueError("source prices do not contain all required ETFs and benchmarks")
    if (prices[["adj_open", "adj_close"]] <= 0).any().any():
        raise ValueError("adjusted prices must be positive")
    return prices.reset_index(drop=True)


def common_price_panel(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = prices.pivot(index="trade_date", columns="symbol", values="adj_close")
    open_ = prices.pivot(index="trade_date", columns="symbol", values="adj_open")
    common = close.dropna(subset=list(SYMBOL_NAMES)).index.intersection(
        open_.dropna(subset=list(SYMBOL_NAMES)).index
    )
    common = common.sort_values()
    columns = list(SYMBOL_NAMES)
    return close.loc[common, columns], open_.loc[common, columns]


def momentum_frame(
    close: pd.DataFrame,
    lookback_days: int,
    pair_symbols: tuple[str, str] = (DIVIDEND, GROWTH),
) -> pd.DataFrame:
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    dividend_symbol, growth_symbol = pair_symbols
    momentum = (
        close[[dividend_symbol, growth_symbol]].div(
            close[[dividend_symbol, growth_symbol]].shift(lookback_days)
        )
        - 1.0
    )
    momentum.columns = ["dividend_momentum", "growth_momentum"]
    momentum["stronger_symbol"] = np.where(
        momentum["growth_momentum"] > momentum["dividend_momentum"],
        growth_symbol,
        dividend_symbol,
    )
    return momentum.dropna().copy()


def scheduled_signal_dates(
    dates: pd.DatetimeIndex,
    *,
    frequency: Frequency | Literal["initial"],
) -> pd.DatetimeIndex:
    if len(dates) < 3:
        raise ValueError("at least three common trading dates are required")
    eligible = dates[: len(dates) - 2]
    if frequency == "initial":
        return pd.DatetimeIndex([eligible[0]])
    if frequency == "daily":
        return eligible
    frame = pd.DataFrame({"trade_date": eligible})
    periods = (
        frame["trade_date"].dt.to_period("W-FRI")
        if frequency == "weekly"
        else frame["trade_date"].dt.to_period("M")
    )
    scheduled = frame.groupby(periods, sort=True)["trade_date"].max().tolist()
    return pd.DatetimeIndex(sorted({eligible[0], *scheduled}))


def target_weights(
    definition: StrategyDefinition,
    *,
    signal_dates: pd.DatetimeIndex,
    momentum: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    satellite_weight = 1.0 - definition.core_weight
    for signal_date in signal_dates:
        if definition.kind == "single":
            selected = str(definition.single_symbol)
            weights = {selected: 1.0}
        elif definition.kind == "balanced":
            selected = "balanced"
            dividend_symbol, growth_symbol = definition.pair_symbols
            weights = {
                LOW_VOL: definition.core_weight,
                dividend_symbol: satellite_weight / 2.0,
                growth_symbol: satellite_weight / 2.0,
            }
        else:
            selected = str(momentum.loc[signal_date, "stronger_symbol"])
            weights = {LOW_VOL: definition.core_weight, selected: satellite_weight}
        for symbol, weight in weights.items():
            if weight <= 0:
                continue
            rows.append(
                {
                    "rebalance_date": signal_date,
                    "symbol": symbol,
                    "weight": weight,
                    "side": "long",
                    "selected_leg": selected,
                    "strategy": definition.name,
                }
            )
    return pd.DataFrame(rows)


def build_periods(
    signal_dates: pd.DatetimeIndex,
    *,
    common_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    locations = {date: location for location, date in enumerate(common_dates)}
    rows: list[dict[str, Any]] = []
    for index, signal_date in enumerate(signal_dates):
        entry_location = locations[signal_date] + 1
        exit_location = (
            locations[signal_dates[index + 1]] + 1
            if index + 1 < len(signal_dates)
            else len(common_dates) - 1
        )
        if entry_location >= exit_location:
            continue
        rows.append(
            {
                "rebalance_date": signal_date,
                "entry_date": common_dates[entry_location],
                "exit_date": common_dates[exit_location],
            }
        )
    return pd.DataFrame(rows)


class _ReconstructRow(NamedTuple):
    rebalance_date: str
    entry_date: str
    exit_date: str
    gross_return: float
    net_return: float


def reconstruct_daily_returns(
    *,
    result_periods: pd.DataFrame,
    positions: pd.DataFrame,
    open_prices: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    position_groups = {
        cast(pd.Timestamp, date): group.set_index("symbol")["weight"].astype(float)
        for date, group in positions.groupby("rebalance_date", sort=False)
    }
    rows: list[dict[str, Any]] = []
    max_error = 0.0
    for period in result_periods.itertuples(index=False):
        row = cast(_ReconstructRow, period)
        rebalance_date = pd.to_datetime(str(row.rebalance_date), format="%Y%m%d")
        entry_date = pd.to_datetime(str(row.entry_date), format="%Y%m%d")
        exit_date = pd.to_datetime(str(row.exit_date), format="%Y%m%d")
        weights = position_groups[rebalance_date]
        window = open_prices.loc[entry_date:exit_date, weights.index]
        gross_nav = window.mul(weights / window.iloc[0], axis=1).sum(axis=1)
        gross_daily = gross_nav.pct_change().dropna()
        gross_period = float(gross_nav.iloc[-1] / gross_nav.iloc[0] - 1.0)
        if not math.isclose(gross_period, float(row.gross_return), abs_tol=1e-10):
            raise ValueError("daily reconstruction does not match framework gross return")
        net_factor = (1.0 + float(row.net_return)) / (1.0 + gross_period)
        net_daily = gross_daily.copy()
        net_daily.iloc[0] = (1.0 + net_daily.iloc[0]) * net_factor - 1.0
        reconstructed = float((1.0 + net_daily).prod() - 1.0)
        max_error = max(max_error, abs(reconstructed - float(row.net_return)))
        for date, gross_return, net_return in zip(
            gross_daily.index,
            gross_daily.to_numpy(),
            net_daily.to_numpy(),
            strict=True,
        ):
            rows.append(
                {
                    "period_end": date,
                    "gross_return": gross_return,
                    "net_return": net_return,
                    "rebalance_date": rebalance_date,
                }
            )
    return pd.DataFrame(rows), max_error


def summarize_backtest(
    *,
    definition: StrategyDefinition,
    cost_bps: float,
    result_periods: pd.DataFrame,
    daily: pd.DataFrame,
    positions: pd.DataFrame,
) -> dict[str, Any]:
    metrics = _return_metrics(daily["net_return"], daily["period_end"])
    gross_total = float((1.0 + daily["gross_return"]).prod() - 1.0)
    selected = positions.groupby("rebalance_date", sort=True)["selected_leg"].first()
    return {
        "strategy": definition.name,
        "label": definition.label,
        "frequency": definition.frequency,
        "core_weight": definition.core_weight,
        "cost_bps_per_side": cost_bps,
        **metrics,
        "gross_total_return": gross_total,
        "cost_drag_total_return": gross_total - metrics["total_return"],
        "framework_periods": len(result_periods),
        "target_updates": int(positions["rebalance_date"].nunique()),
        "selected_leg_switches": int(selected.ne(selected.shift()).sum() - 1),
        "turnover_sum": float(result_periods["turnover"].sum()),
        "turnover_annualized": float(result_periods["turnover"].sum() / metrics["years"]),
        "fee_cost_sum": float(result_periods["fee_cost"].sum()),
    }


def run_one(
    *,
    definition: StrategyDefinition,
    prices: pd.DataFrame,
    close_prices: pd.DataFrame,
    open_prices: pd.DataFrame,
    momentum: pd.DataFrame,
    cost_bps: float,
    analysis_start: pd.Timestamp | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:
    start = momentum.index[0] if analysis_start is None else analysis_start
    analysis_dates = close_prices.loc[start:].index
    signals = scheduled_signal_dates(analysis_dates, frequency=definition.frequency)
    positions = target_weights(definition, signal_dates=signals, momentum=momentum)
    periods = build_periods(signals, common_dates=analysis_dates)
    positions = positions.loc[
        positions["rebalance_date"].isin(set(periods["rebalance_date"]))
    ].copy()
    pricing = prices.loc[
        prices["trade_date"].isin(analysis_dates),
        ["trade_date", "symbol", "adj_open"],
    ]
    result = run_position_backtest(
        positions=positions,
        pricing=pricing,
        periods=periods,
        config=PositionBacktestConfig(
            price_col="adj_open",
            entry_price_col="adj_open",
            exit_price_col="adj_open",
            transaction_cost_bps=cost_bps,
        ),
    )
    daily, error = reconstruct_daily_returns(
        result_periods=result.periods,
        positions=positions,
        open_prices=open_prices,
    )
    summary = summarize_backtest(
        definition=definition,
        cost_bps=cost_bps,
        result_periods=result.periods,
        daily=daily,
        positions=positions,
    )
    return summary, daily, positions, periods, result.periods, error


def stress_existing_result(
    *,
    definition: StrategyDefinition,
    base_result_periods: pd.DataFrame,
    base_cost_bps: float,
    stress_cost_bps: float,
    positions: pd.DataFrame,
    open_prices: pd.DataFrame,
) -> tuple[dict[str, Any], float]:
    if base_cost_bps <= 0:
        raise ValueError("base_cost_bps must be positive for linear cost stress")
    stressed = base_result_periods.copy()
    stressed["fee_cost"] *= stress_cost_bps / base_cost_bps
    stressed["net_return"] = stressed["gross_return"] - stressed["fee_cost"]
    daily, error = reconstruct_daily_returns(
        result_periods=stressed,
        positions=positions,
        open_prices=open_prices,
    )
    return (
        summarize_backtest(
            definition=definition,
            cost_bps=stress_cost_bps,
            result_periods=stressed,
            daily=daily,
            positions=positions,
        ),
        error,
    )


def _parse_float_grid(value: str) -> list[float]:
    values = sorted({float(item.strip()) for item in value.split(",") if item.strip()})
    if not values or any(item < 0 for item in values):
        raise ValueError("cost grid must contain non-negative bps values")
    return values


def _parse_int_grid(value: str) -> list[int]:
    values = sorted({int(item.strip()) for item in value.split(",") if item.strip()})
    if not values or any(item <= 0 for item in values):
        raise ValueError("lookback grid must contain positive trading-day counts")
    return values


def run_lookback_sensitivity(
    *,
    prices: pd.DataFrame,
    close_prices: pd.DataFrame,
    open_prices: pd.DataFrame,
    lookbacks: list[int],
    cost_bps: float,
) -> tuple[pd.DataFrame, dict[str, float]]:
    momentum_by_lookback = {
        lookback: momentum_frame(close_prices, lookback) for lookback in lookbacks
    }
    common_start = max(frame.index[0] for frame in momentum_by_lookback.values())
    bases = [
        definition
        for definition in STRATEGIES
        if definition.name in {"momentum20_weekly", "core60_momentum20_weekly"}
    ]
    rows: list[dict[str, Any]] = []
    errors: dict[str, float] = {}
    for lookback, momentum in momentum_by_lookback.items():
        for base in bases:
            definition = StrategyDefinition(
                name=base.name.replace("momentum20", f"momentum{lookback}"),
                label=base.label.replace("20-day", f"{lookback}-day"),
                frequency=base.frequency,
                kind=base.kind,
                core_weight=base.core_weight,
            )
            summary, _, _, _, _, error = run_one(
                definition=definition,
                prices=prices,
                close_prices=close_prices,
                open_prices=open_prices,
                momentum=momentum,
                cost_bps=cost_bps,
                analysis_start=common_start,
            )
            rows.append({"lookback_days": lookback, "analysis_start": common_start, **summary})
            errors[f"{definition.name}@lookback{lookback}"] = error
    return pd.DataFrame(rows), errors


def run_base_suite(
    *,
    prices: pd.DataFrame,
    close_prices: pd.DataFrame,
    open_prices: pd.DataFrame,
    momentum: pd.DataFrame,
    generic_momentum: pd.DataFrame,
    base_cost_bps: float,
    cost_grid: list[float],
    output: Path,
) -> BaseSuiteResult:
    base_metrics: list[dict[str, Any]] = []
    sensitivity_metrics: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    position_parts: list[pd.DataFrame] = []
    errors: dict[str, float] = {}
    reference_periods: pd.DataFrame | None = None
    runs = [(definition, momentum) for definition in STRATEGIES]
    runs.extend((definition, generic_momentum) for definition in AUDIT_STRATEGIES)
    for definition, signal_momentum in runs:
        summary, daily, positions, periods, result_periods, error = run_one(
            definition=definition,
            prices=prices,
            close_prices=close_prices,
            open_prices=open_prices,
            momentum=signal_momentum,
            cost_bps=base_cost_bps,
        )
        base_metrics.append(summary)
        daily["strategy"] = definition.name
        daily_parts.append(daily)
        position_parts.append(positions)
        errors[definition.name] = error
        if definition.name == "momentum20_weekly":
            reference_periods = periods
            positions.drop(columns=["strategy"]).to_csv(
                output / "positions_by_rebalance.csv",
                index=False,
                date_format="%Y%m%d",
            )
        if definition not in STRATEGIES or definition.kind != "momentum":
            continue
        for cost_bps in cost_grid:
            if math.isclose(cost_bps, base_cost_bps):
                sensitivity_metrics.append(summary)
                continue
            stress, stress_error = stress_existing_result(
                definition=definition,
                base_result_periods=result_periods,
                base_cost_bps=base_cost_bps,
                stress_cost_bps=cost_bps,
                positions=positions,
                open_prices=open_prices,
            )
            sensitivity_metrics.append(stress)
            errors[f"{definition.name}@{cost_bps:g}bps"] = stress_error
    if reference_periods is None:
        raise AssertionError("weekly momentum periods were not generated")
    metrics = pd.DataFrame(base_metrics).sort_values("strategy")
    sensitivity = pd.DataFrame(sensitivity_metrics).sort_values(["strategy", "cost_bps_per_side"])
    daily = pd.concat(daily_parts, ignore_index=True)
    positions = pd.concat(position_parts, ignore_index=True)
    daily["nav"] = daily.groupby("strategy", sort=False)["net_return"].transform(
        lambda values: (1.0 + values).cumprod()
    )
    nav = daily.pivot(index="period_end", columns="strategy", values="nav").reset_index()
    return BaseSuiteResult(
        metrics=metrics,
        sensitivity=sensitivity,
        daily=daily,
        positions=positions,
        nav=nav,
        errors=errors,
        reference_periods=reference_periods,
    )


def _archive_research_sources(output: Path) -> None:
    sources = (
        (Path(__file__).resolve(), "research_script.py"),
        (Path(reporting.__file__).resolve(), "research_reporting.py"),
        (Path(report_builder.__file__).resolve(), "research_report.py"),
        (Path(audit.__file__).resolve(), "research_audit.py"),
        (Path(research_config.__file__).resolve(), "research_config.py"),
    )
    for source, name in sources:
        shutil.copy2(source, output / name)


def run_research(args: argparse.Namespace, output: Path) -> dict[str, Any]:
    if args.refresh_tushare:
        prices = fetch_tushare_prices(
            start_date=args.start_date,
            end_date=args.end_date,
            token_env=args.token_env,
            env_file=args.env_file,
        )
        source_mode = "tushare_fund_daily_and_fund_adj"
    else:
        prices = prepare_prices(pd.read_parquet(args.source_prices.expanduser().resolve()))
        source_mode = "provided_adjusted_etf_prices"
    if args.base_cost_bps <= 0:
        raise ValueError("base_cost_bps must be positive")
    prices.to_parquet(output / "source_prices.parquet", index=False)
    _archive_research_sources(output)
    close_prices, open_prices = common_price_panel(prices)
    momentum = momentum_frame(close_prices, args.lookback_days)
    generic_momentum = momentum_frame(
        close_prices,
        args.lookback_days,
        pair_symbols=(GENERIC_DIVIDEND, GENERIC_GROWTH),
    )
    cost_grid = _parse_float_grid(args.cost_grid_bps)
    lookback_grid = _parse_int_grid(args.lookback_grid_days)
    suite = run_base_suite(
        prices=prices,
        close_prices=close_prices,
        open_prices=open_prices,
        momentum=momentum,
        generic_momentum=generic_momentum,
        base_cost_bps=args.base_cost_bps,
        cost_grid=cost_grid,
        output=output,
    )
    lookbacks, lookback_errors = run_lookback_sensitivity(
        prices=prices,
        close_prices=close_prices,
        open_prices=open_prices,
        lookbacks=lookback_grid,
        cost_bps=args.base_cost_bps,
    )
    suite.errors.update(lookback_errors)
    reporting.write_outputs(
        output=output,
        prices=prices,
        screenshot_symbol_names=SCREENSHOT_SYMBOL_NAMES,
        strategy_labels={definition.name: definition.label for definition in ALL_STRATEGIES},
        metrics=suite.metrics,
        sensitivity=suite.sensitivity,
        daily=suite.daily,
        positions=suite.positions,
        nav=suite.nav,
        lookbacks=lookbacks,
        momentum=momentum,
        generic_momentum=generic_momentum,
        reference_periods=suite.reference_periods,
        cost_bps=args.base_cost_bps,
        benchmark_pairs=BENCHMARK_PAIRS,
        annual_report_strategies=ANNUAL_REPORT_STRATEGIES,
    )
    quality = reporting.write_quality(
        output=output,
        write_json=_write_json,
        symbol_names=SYMBOL_NAMES,
        source_mode=source_mode,
        prices=prices,
        close_prices=close_prices,
        momentum=momentum,
        lookback_days=args.lookback_days,
        errors=suite.errors,
    )
    return {
        "source_mode": source_mode,
        "data_quality": quality,
        "base_cost_bps_per_side": args.base_cost_bps,
        "cost_grid_bps_per_side": cost_grid,
        "lookback_grid_trading_days": lookback_grid,
    }


def _publish(args: argparse.Namespace) -> Path:
    output = args.output_dir.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"research output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.build-{uuid.uuid4().hex}")
    temporary.mkdir()
    try:
        run_metadata = run_research(args, temporary)
        artifacts = sorted(path for path in temporary.iterdir() if path.is_file())
        _write_json(
            temporary / "receipt.json",
            {
                "schema": "dividend_growth_momentum_research.v1",
                "status": "passed",
                "generated_at": datetime.now(UTC).isoformat(),
                "research_only": True,
                "hypothesis_preregistered": False,
                "strict_point_in_time": True,
                "eligible_as_new_oos_evidence": False,
                "automatic_promotion_allowed": False,
                "framework": {
                    "package": "portfolio-backtester",
                    "version": importlib.metadata.version("portfolio-backtester"),
                },
                "run": run_metadata,
                "artifacts": {path.name: _sha256(path) for path in artifacts},
            },
        )
        os.replace(temporary, output)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return output


def main() -> int:
    output = _publish(_parser().parse_args())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
