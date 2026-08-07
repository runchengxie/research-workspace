"""Shared configuration helpers for next-open-to-high research scripts."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

NEXT_EXEC_COLUMNS = [
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "amount",
    "turnover_rate",
    "is_suspended",
    "is_st",
    "is_limit_up",
    "is_limit_down",
    "up_limit",
    "down_limit",
]
LIMIT_BANDS_PCT = np.array([5.0, 10.0, 20.0, 30.0])


@dataclass(frozen=True)
class BacktestConfig:
    daily_dir: str
    outdir: str
    start_date: str
    end_date: str | None
    train_end: str
    test_start: str | None
    test_end: str | None
    target: str
    markets: list[str]
    max_symbols: int
    train_sample_per_date: int
    top_k: list[int]
    take_profit_pct: list[float]
    frozen_top_k: int | None
    frozen_take_profit_pct: float | None
    include_close_exit: bool
    participation_rate: float
    entry_slippage_bps: float
    exit_slippage_bps: float
    round_trip_cost_bps: float
    cost_stress_bps: list[float]
    block_limit_up_open: bool
    random_state: int


@dataclass(frozen=True)
class MinuteAuditConfig:
    selections: str
    minute_root: str
    coverage_manifest: str
    outdir: str
    top_k: int
    take_profit_pct: float
    entry_bar_index: int
    strict_cross: bool
    markets: list[str]
    start_date: str | None
    end_date: str | None
    entry_slippage_bps: float
    exit_slippage_bps: float
    round_trip_cost_bps: float
    participation_rate: float
    benchmark_daily: str | None
    benchmark_universe: str | None
    cost_stress_bps: list[float]


def parse_pct_list(text: str) -> list[float]:
    values = sorted({float(part.strip()) for part in text.split(",") if part.strip()})
    if not values or min(values) <= 0.0:
        raise argparse.ArgumentTypeError("percent list must contain positive decimals")
    return values


def parse_bps_list(text: str) -> list[float]:
    values = sorted({float(part.strip()) for part in text.split(",") if part.strip()})
    if not values or min(values) < 0.0:
        raise argparse.ArgumentTypeError("bps list must contain non-negative numbers")
    return values


def parse_markets(text: str) -> list[str]:
    values = sorted({part.strip().upper() for part in text.split(",") if part.strip()})
    unsupported = set(values) - {"SH", "SZ", "BJ"}
    if not values or unsupported:
        raise argparse.ArgumentTypeError(
            f"--markets must contain one or more of SH,SZ,BJ; unsupported={sorted(unsupported)}"
        )
    return values


def policy_name(take_profit_pct: float | None) -> str:
    if take_profit_pct is None:
        return "close"
    return f"tp_{take_profit_pct:.2%}".replace(".", "p")


def hac_mean_t(values: pd.Series, lags: int = 5) -> float | None:
    """Return a Bartlett-kernel Newey-West t-statistic for the sample mean."""
    clean = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    count = len(clean)
    if count < 2:
        return None
    centered = clean - clean.mean()
    long_run_variance = float(np.dot(centered, centered) / count)
    for lag in range(1, min(lags, count - 1) + 1):
        weight = 1.0 - lag / (lags + 1.0)
        covariance = float(np.dot(centered[lag:], centered[:-lag]) / count)
        long_run_variance += 2.0 * weight * covariance
    variance_of_mean = max(long_run_variance / count, 0.0)
    if variance_of_mean <= 0.0:
        return None
    return float(clean.mean() / math.sqrt(variance_of_mean))


def add_signal_limit_band(frame: pd.DataFrame) -> pd.DataFrame:
    """Classify the signal-day price-limit regime from contemporaneous prices."""
    output = frame.copy()
    pre_close = pd.to_numeric(output["pre_close"], errors="coerce")
    up_limit = pd.to_numeric(output["up_limit"], errors="coerce")
    raw_pct = (up_limit / pre_close - 1.0) * 100.0
    distances = np.abs(raw_pct.to_numpy(dtype=float)[:, None] - LIMIT_BANDS_PCT[None, :])
    nearest_index = np.nanargmin(np.where(np.isnan(distances), np.inf, distances), axis=1)
    nearest = LIMIT_BANDS_PCT[nearest_index]
    recognized = pre_close.gt(0) & up_limit.gt(0) & (np.abs(raw_pct - nearest) <= 1.0)
    output["signal_limit_pct_raw"] = raw_pct
    output["limit_band"] = pd.Series("unknown", index=output.index, dtype="string")
    output.loc[recognized, "limit_band"] = [f"{value:02.0f}pct" for value in nearest[recognized]]
    return output


def _bool_series(frame: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    return frame[column].astype("boolean").fillna(default).astype(bool)


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def add_execution_next_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values(["symbol", "trade_date"]).copy()
    grouped = out.groupby("symbol", sort=False)
    for column in NEXT_EXEC_COLUMNS:
        if column in out.columns:
            out[f"exec_next_{column}"] = grouped[column].shift(-1)
    return out


def add_execution_fields(
    frame: pd.DataFrame,
    *,
    block_limit_up_open: bool,
) -> pd.DataFrame:
    out = frame.copy()
    observed_next_date = pd.to_datetime(out["exec_next_trade_date"])
    out["observed_next_trade_date"] = observed_next_date
    out["entry_date"] = (
        pd.to_datetime(out["market_next_date"])
        if "market_next_date" in out.columns
        else observed_next_date
    )
    out["entry_price"] = pd.to_numeric(out["next_adj_open"], errors="coerce")
    out["next_high_price"] = pd.to_numeric(out["next_adj_high"], errors="coerce")
    out["next_close_price"] = pd.to_numeric(out["next_adj_close"], errors="coerce")
    out["next_amount_cny"] = pd.to_numeric(out["exec_next_amount"], errors="coerce") * 1000.0
    raw_next_open = _numeric_series(out, "exec_next_open")
    raw_next_up_limit = _numeric_series(out, "exec_next_up_limit")
    raw_open_available = raw_next_open.gt(0) & np.isfinite(raw_next_open)
    limit_ratio = raw_next_up_limit / raw_next_open
    out["entry_limit_available"] = (
        raw_open_available
        & raw_next_up_limit.gt(0)
        & np.isfinite(raw_next_up_limit)
        & limit_ratio.between(0.5, 1.5)
    )
    if "market_next_date" in out.columns:
        same_next_session = observed_next_date.eq(out["entry_date"])
    else:
        same_next_session = pd.Series(True, index=out.index)
    out["blocked_not_next_session"] = ~same_next_session

    entry_observable = (
        out["entry_date"].notna()
        & same_next_session
        & out["entry_price"].gt(0)
        & raw_open_available
        & ~_bool_series(out, "exec_next_is_suspended")
        & ~_bool_series(out, "exec_next_is_st")
    )
    out["blocked_limit_up_open"] = False
    if {"exec_next_open", "exec_next_up_limit"}.issubset(out.columns):
        out["blocked_limit_up_open"] = out["entry_limit_available"] & raw_next_open.ge(
            raw_next_up_limit * 0.999
        )

    out["same_next_session"] = same_next_session
    out["execution_eligible"] = entry_observable
    if block_limit_up_open:
        out["execution_eligible"] &= out["entry_limit_available"] & ~out["blocked_limit_up_open"]
    out["outcome_available"] = (
        out["next_high_price"].gt(0) & out["next_close_price"].gt(0) & out["next_amount_cny"].gt(0)
    )
    out["evaluation_eligible"] = out["execution_eligible"] & out["outcome_available"]
    out["open_to_high"] = out["next_high_price"] / out["entry_price"] - 1.0
    out["open_to_close"] = out["next_close_price"] / out["entry_price"] - 1.0
    return out


def filter_signal_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep rows using only information observable at the signal-day close."""
    tradable = (
        pd.to_numeric(frame["amount"], errors="coerce").gt(0)
        & pd.to_numeric(frame["total_mv"], errors="coerce").gt(0)
        & pd.to_numeric(frame["turnover_rate"], errors="coerce").gt(0)
        & ~frame["is_suspended"].astype("boolean").fillna(False).astype(bool)
        & ~frame["is_st"].astype("boolean").fillna(False).astype(bool)
        & pd.to_numeric(frame["listed_days"], errors="coerce").fillna(0).ge(60)
    )
    return frame.loc[tradable].copy()


def label_available_mask(frame: pd.DataFrame, target: str) -> pd.Series:
    target_value = pd.to_numeric(frame[target], errors="coerce")
    return (
        frame["same_next_session"]
        & frame["outcome_available"]
        & target_value.notna()
        & np.isfinite(target_value)
    )


def write_test_predictions(outdir: Path, test: pd.DataFrame, target: str) -> None:
    columns = [
        "trade_date",
        "symbol",
        "pred",
        target,
        "entry_date",
        "observed_next_trade_date",
        "same_next_session",
        "execution_eligible",
        "outcome_available",
        "evaluation_eligible",
        "blocked_limit_up_open",
        "entry_limit_available",
        "blocked_not_next_session",
        "pre_close",
        "up_limit",
        "board",
        "exec_next_up_limit",
        "exec_next_down_limit",
        "signal_limit_pct_raw",
        "limit_band",
    ]
    test[columns].to_parquet(outdir / "test_predictions.parquet", index=False)


def build_stress_daily(
    stressed: pd.DataFrame,
    daily_selection: pd.DataFrame | None,
) -> pd.DataFrame:
    keys = ["signal_date", "entry_date", "top_k", "exit_policy"]
    grouped = (
        stressed.groupby(keys, sort=False)
        .agg(
            filled=("symbol", "count"),
            avg_trade_return=("stress_return", "mean"),
        )
        .reset_index()
    )
    if daily_selection is None:
        output = grouped
    else:
        selection_keys = ["signal_date", "entry_date", "top_k"]
        policies = stressed[["exit_policy"]].drop_duplicates()
        base = daily_selection[selection_keys].merge(policies, how="cross")
        output = base.merge(grouped, on=keys, how="left")
        output["filled"] = output["filled"].fillna(0).astype(int)
        output["avg_trade_return"] = output["avg_trade_return"].fillna(0.0)
    output["portfolio_return"] = output["avg_trade_return"] * (output["filled"] / output["top_k"])
    return output
