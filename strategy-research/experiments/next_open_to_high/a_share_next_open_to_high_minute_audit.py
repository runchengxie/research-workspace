#!/usr/bin/env python3
"""Audit a frozen next-open-to-high candidate list against canonical minute bars.

The audit deliberately does not retrain or select a take-profit policy. It enters
after a configurable completed minute bar, requires a later bar to trade through
the target price, and leaves unavailable or unfilled slots in cash.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from a_share_next_open_to_high_common import (
    MinuteAuditConfig,
    hac_mean_t,
    parse_bps_list,
    policy_name,
)
from a_share_next_open_to_high_coverage_manifest import coverage_manifest_for_minute_root
from a_share_next_open_to_high_minute_benchmark import (
    attach_exposure_matched_benchmark,
    attach_limit_band_matched_benchmark,
    audit_benchmark_day_with_bands,
    benchmark_execution_diagnostic_summary,
    load_benchmark_universe,
    summarize_limit_band_exposure,
    validate_benchmark_decomposition,
)
from a_share_next_open_to_high_minute_execution import (
    audit_candidate,
    execution_diagnostic_summary,
    load_minute_source_contracts,
    source_contract_summary,
)

DATA_ROOT = Path("/home/richard/data/market-data-platform")
DEFAULT_MINUTE_ROOT = DATA_ROOT / "assets/derived/a_share/minute_1m"
DEFAULT_SELECTIONS = Path(
    "artifacts/reports/a_share_next_oth_backtest_20260703/selected_candidates.csv"
)
DEFAULT_OUT_BASE = Path("artifacts/reports")


def _float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _parse_markets(text: str) -> list[str]:
    values = sorted({part.strip().upper() for part in text.split(",") if part.strip()})
    unsupported = set(values) - {"SH", "SZ", "BJ"}
    if not values or unsupported:
        raise argparse.ArgumentTypeError(
            f"--markets must contain one or more of SH,SZ,BJ; unsupported={sorted(unsupported)}"
        )
    return values


def _load_selections(
    path: Path, args: argparse.Namespace
) -> tuple[pd.DataFrame, bool, dict[str, Any]]:
    frame = pd.read_csv(path)
    required = {"signal_date", "entry_date", "symbol", "top_k"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Selection artifact is missing columns: {sorted(missing)}")
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="coerce")
    frame["entry_date"] = pd.to_datetime(frame["entry_date"], errors="coerce")
    frame = frame.loc[frame["top_k"].eq(args.top_k)].copy()
    suffix = frame["symbol"].str.rsplit(".", n=1).str[-1].str.upper()
    frame = frame.loc[suffix.isin(args.markets)].copy()
    if frame["signal_date"].isna().any():
        raise ValueError("Selection artifact contains invalid signal_date values")
    duplicates = frame.duplicated(["signal_date", "symbol"], keep=False)
    if duplicates.any():
        raise ValueError("Selection artifact has duplicate signal_date/symbol keys")
    invalid_entry_date = frame["entry_date"].isna()
    before_start = pd.Series(False, index=frame.index)
    after_end = pd.Series(False, index=frame.index)
    if args.start_date:
        before_start = frame["entry_date"].lt(pd.Timestamp(args.start_date))
    if args.end_date:
        after_end = frame["entry_date"].gt(pd.Timestamp(args.end_date))
    load_audit = {
        "input_rows_after_policy_market": len(frame),
        "input_signal_days": int(frame["signal_date"].nunique()),
        "invalid_entry_date_rows": int(invalid_entry_date.sum()),
        "before_start_rows": int(before_start.sum()),
        "after_end_rows": int(after_end.sum()),
        "after_end_signal_days": int(frame.loc[after_end, "signal_date"].nunique()),
    }
    frame = frame.loc[~invalid_entry_date & ~before_start & ~after_end].copy()
    if frame.empty:
        raise ValueError("No selections remain after policy, market, and date filters")
    daily_candidate_counts = frame.groupby("signal_date", sort=False).size()
    if daily_candidate_counts.gt(args.top_k).any():
        offending = daily_candidate_counts.loc[daily_candidate_counts.gt(args.top_k)]
        raise ValueError(
            "Selection artifact exceeds fixed Top-K denominator on signal dates: "
            f"{offending.to_dict()}"
        )
    load_audit["audit_rows"] = len(frame)
    load_audit["audit_signal_days"] = int(frame["signal_date"].nunique())
    load_audit["audit_entry_days"] = int(frame["entry_date"].nunique())
    legacy_future_filtered = "outcome_available" not in frame.columns
    if "execution_eligible" not in frame.columns:
        frame["execution_eligible"] = True
    else:
        frame["execution_eligible"] = (
            frame["execution_eligible"].astype("boolean").fillna(False).astype(bool)
        )
    for column, default in (
        ("entry_limit_available", True),
        ("blocked_limit_up_open", False),
        ("blocked_not_next_session", False),
    ):
        if column not in frame.columns:
            frame[column] = default
        else:
            frame[column] = frame[column].astype("boolean").fillna(default).astype(bool)
    if "limit_band" not in frame.columns:
        frame["limit_band"] = "unknown"
    frame["limit_band"] = frame["limit_band"].astype("string").fillna("unknown")
    return frame.sort_values(["entry_date", "symbol"]), legacy_future_filtered, load_audit


def _minute_file(minute_root: Path, entry_date: pd.Timestamp) -> Path:
    partition = minute_root / f"trade_date={entry_date:%Y%m%d}"
    files = sorted(partition.glob("*.parquet"))
    if len(files) != 1:
        raise FileNotFoundError(
            f"Expected exactly one minute parquet for {entry_date:%Y-%m-%d}, found {len(files)}"
        )
    return files[0]


def _load_day(path: Path, symbols: list[str]) -> pd.DataFrame:
    if not symbols:
        return pd.DataFrame(
            {
                column: pd.Series(dtype="object")
                for column in (
                    "ts_code",
                    "trade_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "vol",
                    "amount",
                )
            }
        )
    table = ds.dataset(path, format="parquet").to_table(
        filter=ds.field("ts_code").isin(symbols),
        columns=["ts_code", "trade_time", "open", "high", "low", "close", "vol", "amount"],
    )
    frame = table.to_pandas()
    if frame.empty:
        return frame
    frame["trade_time"] = pd.to_datetime(frame["trade_time"])
    duplicate = frame.duplicated(["ts_code", "trade_time"], keep=False)
    if duplicate.any():
        raise ValueError(f"Duplicate minute keys in {path}")
    return frame.sort_values(["ts_code", "trade_time"])


def _daily_returns(trades: pd.DataFrame, top_k: int) -> pd.DataFrame:
    base = trades[["signal_date", "entry_date"]].drop_duplicates().sort_values("signal_date")
    audited = trades.loc[trades["status"].eq("audited")].copy()
    if "target_crossed" not in audited.columns:
        audited["target_crossed"] = False
    audited_daily = (
        audited.groupby(["signal_date", "entry_date"], sort=True)
        .agg(
            audited_names=("symbol", "size"),
            target_cross_rate=("target_crossed", "mean"),
            net_return_sum=("net_return", "sum"),
        )
        .reset_index()
    )
    grouped = base.merge(audited_daily, on=["signal_date", "entry_date"], how="left")
    grouped["audited_names"] = grouped["audited_names"].fillna(0).astype(int)
    grouped["net_return_sum"] = grouped["net_return_sum"].fillna(0.0)
    grouped["portfolio_return"] = grouped["net_return_sum"] / top_k
    if "daily_ohlc_net_return" in audited.columns:
        ohlc_sum = audited.groupby(["signal_date", "entry_date"], sort=True)[
            "daily_ohlc_net_return"
        ].sum()
        grouped = grouped.merge(
            ohlc_sum.rename("daily_ohlc_net_return_sum").reset_index(),
            on=["signal_date", "entry_date"],
            how="left",
        )
        grouped["daily_ohlc_net_return_sum"] = grouped["daily_ohlc_net_return_sum"].fillna(0.0)
        grouped["daily_ohlc_portfolio_return"] = grouped["daily_ohlc_net_return_sum"] / top_k
        grouped["minute_minus_daily_ohlc"] = (
            grouped["portfolio_return"] - grouped["daily_ohlc_portfolio_return"]
        )
    grouped["cash_weight"] = 1.0 - grouped["audited_names"] / top_k
    return grouped


def _attach_daily_open_diagnostic(
    daily: pd.DataFrame,
    benchmark_path: Path | None,
    take_profit_pct: float,
) -> pd.DataFrame:
    if benchmark_path is None:
        return daily
    benchmark = pd.read_csv(benchmark_path)
    benchmark["signal_date"] = pd.to_datetime(benchmark["signal_date"])
    benchmark = benchmark.loc[benchmark["exit_policy"].eq(policy_name(take_profit_pct))]
    columns = ["signal_date", "benchmark_slots", "benchmark_return"]
    if benchmark.empty or benchmark.duplicated("signal_date").any():
        raise ValueError("Daily matched-universe benchmark is empty or has duplicate dates")
    benchmark = benchmark[columns].rename(
        columns={
            "benchmark_slots": "daily_open_benchmark_slots",
            "benchmark_return": "daily_open_benchmark_return",
        }
    )
    output = daily.merge(benchmark, on="signal_date", how="left", validate="one_to_one")
    if output["daily_open_benchmark_return"].isna().any():
        raise ValueError("Daily matched-universe benchmark does not cover every minute audit date")
    return output


def _stressed_limit_band_benchmark(
    trades: pd.DataFrame,
    benchmark_bands: pd.DataFrame,
    top_k: int,
    drag_bps: float,
) -> pd.DataFrame:
    audited = trades.loc[trades["status"].eq("audited")]
    selected_counts = (
        audited.groupby(["signal_date", "entry_date", "limit_band"], observed=True, sort=True)
        .size()
        .rename("selected_band_audited")
        .reset_index()
    )
    bands = benchmark_bands.copy()
    stressed_sum = (
        bands["benchmark_gross_return_sum"] - drag_bps / 10000.0 * bands["benchmark_audited"]
    )
    bands["stressed_executed_mean"] = (
        stressed_sum / bands["benchmark_audited"].replace(0, np.nan)
    ).fillna(0.0)
    weighted = bands.merge(
        selected_counts,
        on=["signal_date", "entry_date", "limit_band"],
        how="left",
        validate="one_to_one",
    )
    weighted["selected_band_audited"] = weighted["selected_band_audited"].fillna(0)
    weighted["contribution"] = (
        weighted["stressed_executed_mean"] * weighted["selected_band_audited"] / top_k
    )
    return (
        weighted.groupby(["signal_date", "entry_date"], sort=True)["contribution"]
        .sum()
        .rename("limit_band_matched_return")
        .reset_index()
    )


def _stress_comparison_metrics(
    selected: pd.Series,
    benchmark: pd.Series,
    broad_matched: pd.Series,
    limit_band_matched: pd.Series,
) -> dict[str, Any]:
    broad_active = selected - broad_matched
    within_band_active = selected - limit_band_matched
    benchmark_vol = benchmark.std(ddof=0)
    within_band_vol = within_band_active.std(ddof=0)
    selected_nav = (1.0 + selected).prod()
    limit_band_nav = (1.0 + limit_band_matched).prod()
    return {
        "benchmark_return_mean": _float_or_none(benchmark.mean()),
        "benchmark_sharpe": _float_or_none(benchmark.mean() / benchmark_vol * math.sqrt(252.0))
        if benchmark_vol > 0
        else None,
        "benchmark_hac_mean_t_5": hac_mean_t(benchmark, lags=5),
        "broad_exposure_matched_benchmark_mean": _float_or_none(broad_matched.mean()),
        "broad_active_return_mean": _float_or_none(broad_active.mean()),
        "limit_band_matched_benchmark_mean": _float_or_none(limit_band_matched.mean()),
        "within_band_active_return_mean": _float_or_none(within_band_active.mean()),
        "within_band_active_sharpe": _float_or_none(
            within_band_active.mean() / within_band_vol * math.sqrt(252.0)
        )
        if within_band_vol > 0
        else None,
        "within_band_active_hac_mean_t_5": hac_mean_t(within_band_active, lags=5),
        "relative_nav_vs_limit_band_matched_benchmark": _float_or_none(
            selected_nav / limit_band_nav - 1.0
        ),
    }


def _minute_cost_stress(
    trades: pd.DataFrame,
    daily: pd.DataFrame,
    benchmark_bands: pd.DataFrame,
    top_k: int,
    stress_bps: list[float],
) -> pd.DataFrame:
    base = daily[["signal_date", "entry_date"]]
    audited = trades.loc[trades["status"].eq("audited")].copy()
    if "gross_return" not in audited.columns:
        audited["gross_return"] = pd.Series(dtype=float)
    rows: list[dict[str, Any]] = []
    for drag_bps in stress_bps:
        audited["stress_return"] = audited["gross_return"] - drag_bps / 10000.0
        sums = (
            audited.groupby(["signal_date", "entry_date"], sort=True)["stress_return"]
            .sum()
            .rename("stress_return_sum")
            .reset_index()
        )
        stressed_daily = base.merge(sums, on=["signal_date", "entry_date"], how="left")
        selected_returns = stressed_daily["stress_return_sum"].fillna(0.0) / top_k
        daily_vol = selected_returns.std(ddof=0)
        selected_row = {
            "drag_bps": drag_bps,
            "days": len(selected_returns),
            "selected_return_mean": _float_or_none(selected_returns.mean()),
            "selected_sharpe": _float_or_none(
                selected_returns.mean() / daily_vol * math.sqrt(252.0)
            )
            if daily_vol > 0
            else None,
            "selected_hac_mean_t_5": hac_mean_t(selected_returns, lags=5),
        }
        if "benchmark_gross_return_sum" not in daily.columns:
            rows.append(selected_row)
            continue
        benchmark_returns = (
            daily["benchmark_gross_return_sum"] - drag_bps / 10000.0 * daily["benchmark_audited"]
        ) / daily["benchmark_slots"]
        benchmark_mean = (
            benchmark_returns / daily["benchmark_invested_weight"].replace(0.0, np.nan)
        ).fillna(0.0)
        matched_benchmark = benchmark_mean * daily["selected_invested_weight"]
        if benchmark_bands.empty:
            limit_band_matched = matched_benchmark
        else:
            band_daily = _stressed_limit_band_benchmark(trades, benchmark_bands, top_k, drag_bps)
            aligned = base.merge(
                band_daily, on=["signal_date", "entry_date"], how="left", validate="one_to_one"
            )
            limit_band_matched = aligned["limit_band_matched_return"].fillna(0.0)
        rows.append(
            {
                **selected_row,
                **_stress_comparison_metrics(
                    selected_returns,
                    benchmark_returns,
                    matched_benchmark,
                    limit_band_matched,
                ),
            }
        )
    return pd.DataFrame(rows)


def _series_stats(series: pd.Series, prefix: str) -> dict[str, Any]:
    volatility = series.std(ddof=0)
    return {
        f"{prefix}_return_mean": _float_or_none(series.mean()),
        f"{prefix}_sharpe": _float_or_none(series.mean() / volatility * math.sqrt(252.0))
        if volatility > 0
        else None,
        f"{prefix}_hac_mean_t_5": hac_mean_t(series, lags=5),
    }


def _benchmark_summary(daily: pd.DataFrame, selected_returns: pd.Series) -> dict[str, Any]:
    if "benchmark_exposure_matched_return" not in daily.columns:
        return {}
    benchmark_returns = daily["benchmark_return"]
    broad_matched = daily["benchmark_exposure_matched_return"]
    broad_active = daily["broad_active_return"]
    selected_nav = (1.0 + selected_returns).prod()
    broad_nav = (1.0 + broad_matched).prod()
    result = {
        "benchmark_execution_basis": "same_universe_same_09_31_minute_entry",
        **_series_stats(benchmark_returns, "benchmark"),
        **_series_stats(broad_matched, "broad_exposure_matched_benchmark"),
        **_series_stats(broad_active, "broad_active"),
        "relative_nav_vs_broad_exposure_matched_benchmark": _float_or_none(
            selected_nav / broad_nav - 1.0
        ),
    }
    if "benchmark_limit_band_matched_return" not in daily.columns:
        return result
    limit_band_matched = daily["benchmark_limit_band_matched_return"]
    within_band_active = daily["within_band_active_return"]
    limit_band_nav = (1.0 + limit_band_matched).prod()
    result.update(
        {
            "primary_active_basis": "signal_day_limit_band_and_invested_weight_matched",
            **_series_stats(limit_band_matched, "limit_band_matched_benchmark"),
            **_series_stats(within_band_active, "within_band_active"),
            "relative_nav_vs_limit_band_matched_benchmark": _float_or_none(
                selected_nav / limit_band_nav - 1.0
            ),
        }
    )
    return result


def _summary(
    trades: pd.DataFrame,
    daily: pd.DataFrame,
    config: MinuteAuditConfig,
    legacy_future_filtered: bool,
) -> dict[str, Any]:
    returns = daily["portfolio_return"] if not daily.empty else pd.Series(dtype=float)
    daily_vol = returns.std(ddof=0)
    reconciled = trades.loc[trades["status"].eq("audited")]
    result: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "candidate_rows": len(trades),
        "audited_rows": int(trades["status"].eq("audited").sum()),
        "status_counts": trades["status"].value_counts().to_dict(),
        "days": len(daily),
        "daily_return_mean": _float_or_none(returns.mean()),
        "daily_win_rate": _float_or_none(returns.gt(0).mean()),
        "sharpe": _float_or_none(returns.mean() / daily_vol * math.sqrt(252.0))
        if daily_vol > 0
        else None,
        "hac_mean_t_5": hac_mean_t(returns, lags=5),
        "total_return": _float_or_none((1.0 + returns).prod() - 1.0),
        "target_cross_rate": _float_or_none(reconciled["target_crossed"].mean())
        if not reconciled.empty
        else None,
        "legacy_input_was_future_filtered": legacy_future_filtered,
        "promotion_eligible": False,
        "limitations": [
            "Take-profit fills are bar-level upper bounds: a later minute high must strictly "
            "cross the target, but queue position and executable volume are unknown.",
            "A 09:31 entry at the available daily up limit or with non-positive bar amount is "
            "blocked and its fixed slot remains cash; no after-open replacement is allowed.",
            "Missing or implausible daily up-limit fields fail closed: the fixed slot remains "
            "cash.",
            "The primary entry uses the 09:31 completed-bar close and assumes execution at that "
            "reference; this same-bar-close assumption is an additional upper bound.",
            "A close exit at the available daily down limit is marked to the close but is not "
            "proven executable, so reported returns remain an execution upper bound.",
            "Missing or implausible daily down-limit fields are explicitly unavailable rather "
            "than inferred from future prices.",
            "The supplied candidate artifact may already have been inspected in earlier research.",
            "A frozen model and policy need later untouched dates before promotion.",
            "The selected list is heavily concentrated in the 20% signal-day price-limit band.",
            "Broad-universe active return is not stock-selection attribution; "
            "use within-band active.",
            "Within-band matching does not control volatility, size, liquidity, or industry.",
        ],
    }
    if "daily_ohlc_portfolio_return" in daily.columns:
        ohlc_returns = daily["daily_ohlc_portfolio_return"]
        ohlc_vol = ohlc_returns.std(ddof=0)
        result.update(
            {
                "daily_ohlc_return_mean": _float_or_none(ohlc_returns.mean()),
                "daily_ohlc_sharpe": _float_or_none(
                    ohlc_returns.mean() / ohlc_vol * math.sqrt(252.0)
                )
                if ohlc_vol > 0
                else None,
                "daily_ohlc_total_return": _float_or_none((1.0 + ohlc_returns).prod() - 1.0),
                "daily_ohlc_target_hit_rate": _float_or_none(
                    reconciled["daily_ohlc_target_hit"].mean()
                ),
                "minute_minus_daily_ohlc_mean": _float_or_none((returns - ohlc_returns).mean()),
            }
        )
    result.update(_benchmark_summary(daily, returns))
    if "daily_open_benchmark_return" in daily.columns:
        result.update(
            {
                "daily_open_benchmark_is_diagnostic_only": True,
                "daily_open_benchmark_return_mean": _float_or_none(
                    daily["daily_open_benchmark_return"].mean()
                ),
            }
        )
    for daily_column, minute_column, name in (
        ("exec_next_open", "minute_open", "open"),
        ("exec_next_high", "minute_high", "high"),
        ("exec_next_close", "minute_close", "close"),
    ):
        if daily_column in reconciled.columns:
            daily_value = pd.to_numeric(reconciled[daily_column], errors="coerce")
            minute_value = pd.to_numeric(reconciled[minute_column], errors="coerce")
            diff_bps = (minute_value / daily_value - 1.0).abs() * 10000.0
            result[f"daily_minute_{name}_max_abs_diff_bps"] = _float_or_none(diff_bps.max())
    return result


def _build_audit_config(
    args: argparse.Namespace,
    selection_path: Path,
    minute_root: Path,
    outdir: Path,
) -> MinuteAuditConfig:
    coverage_manifest = (
        Path(args.coverage_manifest).expanduser().resolve()
        if args.coverage_manifest
        else coverage_manifest_for_minute_root(minute_root, data_root=DATA_ROOT)
    )
    return MinuteAuditConfig(
        selections=str(selection_path),
        minute_root=str(minute_root),
        coverage_manifest=str(coverage_manifest),
        outdir=str(outdir),
        top_k=int(args.top_k),
        take_profit_pct=float(args.take_profit_pct),
        entry_bar_index=int(args.entry_bar_index),
        strict_cross=bool(args.strict_cross),
        markets=list(args.markets),
        start_date=args.start_date,
        end_date=args.end_date,
        entry_slippage_bps=float(args.entry_slippage_bps),
        exit_slippage_bps=float(args.exit_slippage_bps),
        round_trip_cost_bps=float(args.round_trip_cost_bps),
        participation_rate=float(args.participation_rate),
        benchmark_daily=str(Path(args.benchmark_daily).expanduser().resolve())
        if args.benchmark_daily
        else None,
        benchmark_universe=str(Path(args.benchmark_universe).expanduser().resolve())
        if args.benchmark_universe
        else None,
        cost_stress_bps=list(args.cost_stress_bps),
    )


def _audit_all_dates(
    selections: pd.DataFrame,
    benchmark_universe: pd.DataFrame,
    minute_root: Path,
    config: MinuteAuditConfig,
    source_contracts: dict[pd.Timestamp, str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    benchmark_groups: dict[Any, pd.DataFrame] = {}
    if not benchmark_universe.empty:
        for entry_date, group in benchmark_universe.groupby("entry_date", sort=True):
            benchmark_groups[entry_date] = group
    rows: list[dict[str, Any]] = []
    benchmark_rows: list[dict[str, Any]] = []
    benchmark_band_rows: list[dict[str, Any]] = []
    grouped_dates = list(selections.groupby("entry_date", sort=True))
    for date_index, (entry_date, candidates) in enumerate(grouped_dates, start=1):
        entry_timestamp = cast(pd.Timestamp, entry_date)
        minute_source = source_contracts[entry_timestamp]
        benchmark_candidates = benchmark_groups.get(entry_timestamp, pd.DataFrame())
        requested_symbols = set(candidates.loc[candidates["execution_eligible"], "symbol"])
        if not benchmark_candidates.empty:
            requested_symbols.update(
                benchmark_candidates.loc[
                    benchmark_candidates["execution_eligible"], "symbol"
                ].tolist()
            )
        if date_index == 1 or date_index % 10 == 0 or date_index == len(grouped_dates):
            print(
                f"[minute] {date_index}/{len(grouped_dates)} entry_date={entry_timestamp:%Y-%m-%d} "
                f"source={minute_source} symbols={len(requested_symbols):,}",
                flush=True,
            )
        try:
            minute = _load_day(
                _minute_file(minute_root, entry_timestamp), sorted(requested_symbols)
            )
        except FileNotFoundError:
            minute = pd.DataFrame()
        for _, candidate in candidates.iterrows():
            bars = (
                minute.loc[minute["ts_code"].eq(candidate["symbol"])]
                if not minute.empty
                else pd.DataFrame()
            )
            row = audit_candidate(
                candidate,
                bars,
                entry_bar_index=config.entry_bar_index,
                take_profit_pct=config.take_profit_pct,
                strict_cross=config.strict_cross,
                entry_slippage_bps=config.entry_slippage_bps,
                exit_slippage_bps=config.exit_slippage_bps,
                round_trip_cost_bps=config.round_trip_cost_bps,
                participation_rate=config.participation_rate,
                minute_source=minute_source,
            )
            for column in ("exec_next_open", "exec_next_high", "exec_next_close"):
                if column in candidate.index:
                    row[column] = candidate[column]
            rows.append(row)
        if not benchmark_candidates.empty:
            broad, bands = audit_benchmark_day_with_bands(
                benchmark_candidates,
                minute,
                entry_bar_index=config.entry_bar_index,
                take_profit_pct=config.take_profit_pct,
                strict_cross=config.strict_cross,
                entry_slippage_bps=config.entry_slippage_bps,
                exit_slippage_bps=config.exit_slippage_bps,
                round_trip_cost_bps=config.round_trip_cost_bps,
                minute_source=minute_source,
            )
            broad["minute_source"] = minute_source
            for band in bands:
                band["minute_source"] = minute_source
            benchmark_rows.append(broad)
            benchmark_band_rows.extend(bands)
    return (
        pd.DataFrame(rows),
        pd.DataFrame(benchmark_rows),
        pd.DataFrame(benchmark_band_rows),
    )


def _write_audit_outputs(
    outdir: Path,
    trades: pd.DataFrame,
    daily: pd.DataFrame,
    minute_benchmark: pd.DataFrame,
    minute_benchmark_bands: pd.DataFrame,
    limit_band_exposure: pd.DataFrame,
    cost_stress: pd.DataFrame,
    summary: dict[str, Any],
) -> None:
    trades.to_csv(outdir / "minute_trade_audit.csv", index=False)
    daily.to_csv(outdir / "minute_daily_returns.csv", index=False)
    minute_benchmark.to_csv(outdir / "minute_benchmark_daily.csv", index=False)
    minute_benchmark_bands.to_csv(outdir / "minute_limit_band_benchmark_daily.csv", index=False)
    limit_band_exposure.to_csv(outdir / "minute_limit_band_exposure.csv", index=False)
    cost_stress.to_csv(outdir / "minute_cost_stress.csv", index=False)
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    (outdir / "report.md").write_text(
        "# Next-open-to-high minute-path audit\n\n"
        "This is a fixed-policy execution audit, not promotion evidence.\n\n"
        "```json\n" + json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n```\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> Path:
    selection_path = Path(args.selections).expanduser().resolve()
    minute_root = Path(args.minute_root).expanduser().resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    outdir = (
        Path(args.outdir or DEFAULT_OUT_BASE / f"a_share_next_oth_minute_audit_{timestamp}")
        .expanduser()
        .resolve()
    )
    outdir.mkdir(parents=True, exist_ok=True)
    config = _build_audit_config(args, selection_path, minute_root, outdir)
    selections, legacy_future_filtered, selection_load_audit = _load_selections(
        selection_path, args
    )
    benchmark_universe = (
        load_benchmark_universe(Path(config.benchmark_universe), args)
        if config.benchmark_universe
        else pd.DataFrame()
    )
    source_contracts = load_minute_source_contracts(Path(config.coverage_manifest), minute_root)
    requested_entry_dates = {
        cast(pd.Timestamp, date) for date in selections["entry_date"].dropna().unique()
    }
    missing_contracts = requested_entry_dates - set(source_contracts)
    if missing_contracts:
        raise ValueError(
            "Minute coverage manifest lacks requested entry dates: "
            f"{sorted(str(date) for date in missing_contracts)}"
        )
    selected_source_contracts = {date: source_contracts[date] for date in requested_entry_dates}
    trades, minute_benchmark, minute_benchmark_bands = _audit_all_dates(
        selections,
        benchmark_universe,
        minute_root,
        config,
        selected_source_contracts,
    )
    daily = _daily_returns(trades, config.top_k)
    if not minute_benchmark.empty:
        daily = attach_exposure_matched_benchmark(daily, minute_benchmark)
    if not minute_benchmark_bands.empty:
        validate_benchmark_decomposition(minute_benchmark, minute_benchmark_bands)
        daily = attach_limit_band_matched_benchmark(
            daily,
            trades,
            minute_benchmark_bands,
            config.top_k,
        )
        limit_band_exposure = summarize_limit_band_exposure(
            trades, minute_benchmark_bands, config.top_k
        )
    else:
        limit_band_exposure = pd.DataFrame()
    daily = _attach_daily_open_diagnostic(
        daily,
        Path(config.benchmark_daily) if config.benchmark_daily else None,
        config.take_profit_pct,
    )
    cost_stress = _minute_cost_stress(
        trades,
        daily,
        minute_benchmark_bands,
        config.top_k,
        config.cost_stress_bps,
    )
    summary = _summary(trades, daily, config, legacy_future_filtered)
    summary["selection_load_audit"] = selection_load_audit
    summary["minute_source_contract_days"] = source_contract_summary(selected_source_contracts)
    summary["execution_diagnostics"] = execution_diagnostic_summary(trades)
    if not minute_benchmark.empty:
        summary["benchmark_execution_diagnostics"] = benchmark_execution_diagnostic_summary(
            minute_benchmark
        )
    summary["limit_band_exposure"] = limit_band_exposure.to_dict(orient="records")
    summary["cost_stress"] = cost_stress.to_dict(orient="records")
    _write_audit_outputs(
        outdir,
        trades,
        daily,
        minute_benchmark,
        minute_benchmark_bands,
        limit_band_exposure,
        cost_stress,
        summary,
    )
    print(f"[done] {outdir}")
    return outdir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selections", default=str(DEFAULT_SELECTIONS))
    parser.add_argument("--minute-root", default=str(DEFAULT_MINUTE_ROOT))
    parser.add_argument(
        "--coverage-manifest",
        help="Versioned coverage receipt derived from the resolved --minute-root alias by default.",
    )
    parser.add_argument("--outdir")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--take-profit-pct", type=float, default=0.08)
    parser.add_argument(
        "--entry-bar-index",
        type=int,
        default=1,
        help="Completed minute bar used for entry; 1 means 09:31 on canonical data",
    )
    parser.add_argument("--strict-cross", action="store_true", default=True)
    parser.add_argument("--allow-touch-fill", dest="strict_cross", action="store_false")
    parser.add_argument("--markets", type=_parse_markets, default=_parse_markets("SH,SZ"))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--entry-slippage-bps", type=float, default=5.0)
    parser.add_argument("--exit-slippage-bps", type=float, default=5.0)
    parser.add_argument("--round-trip-cost-bps", type=float, default=12.0)
    parser.add_argument("--participation-rate", type=float, default=0.05)
    parser.add_argument("--benchmark-daily")
    parser.add_argument("--benchmark-universe")
    parser.add_argument(
        "--cost-stress-bps",
        type=parse_bps_list,
        default=parse_bps_list("22,50,100,150,200"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.entry_bar_index < 0:
        raise SystemExit("--entry-bar-index must be non-negative")
    run(args)


if __name__ == "__main__":
    main()
