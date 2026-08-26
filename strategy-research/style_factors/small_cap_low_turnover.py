"""Bounded small-cap and low-turnover strategy exploration helpers.

This module is deliberately an exploration layer.  It does not register a
production strategy or change the shared portfolio-backtester API.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd

from .liquidity_signals import _residualize_by_date, _standardize_signal
from .robustness_execution import (
    LegSimulation,
    daily_return_matrix,
    execution_matrices,
    simulate_leg,
    terminal_event_positions,
)

SIGNAL_COLUMNS = {
    "small_cap": "signal_small_cap",
    "low_turnover": "signal_low_turnover",
    "low_turnover_residual": "signal_low_turnover_residual",
    "composite": "signal_composite",
    "composite_residual": "signal_composite_residual",
    "large_cap_control": "signal_large_cap_control",
    "lowvol_control": "signal_lowvol_control",
}


@dataclass(frozen=True)
class LongOnlySimulation:
    """One candidate's constrained long-only simulation and diagnostics."""

    name: str
    signal_column: str
    targets: dict[pd.Timestamp, dict[str, float]]
    leg: LegSimulation
    active_dates: pd.DatetimeIndex
    eligible_rows: int


def _require_columns(frame: pd.DataFrame, columns: set[str], *, label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def build_lagged_turnover_panel(
    daily_clean: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    *,
    window: int = 60,
    minimum_observations: int = 45,
) -> pd.DataFrame:
    """Build turnover lookbacks that exclude the formation day's observation."""
    if window <= 0:
        raise ValueError("window must be positive")
    if not 1 <= minimum_observations <= window:
        raise ValueError("minimum_observations must be between 1 and window")
    _require_columns(
        daily_clean,
        {"trade_date", "symbol", "turnover_rate"},
        label="daily_clean",
    )
    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()  # ty: ignore[unresolved-attribute]
    if dates.empty:
        raise ValueError("formation_dates is empty")

    frame = daily_clean[["trade_date", "symbol", "turnover_rate"]].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str)
    frame["turnover_rate"] = pd.to_numeric(frame["turnover_rate"], errors="coerce")
    frame = frame.sort_values(["symbol", "trade_date"])
    turnover_column = f"turnover_lagged_mean_{window}d"
    frame[turnover_column] = frame.groupby("symbol", sort=False)["turnover_rate"].transform(
        lambda values: (
            values.shift(1)
            .rolling(
                window,
                min_periods=minimum_observations,
            )
            .mean()
        )
    )
    return frame.loc[
        frame["trade_date"].isin(dates),
        ["trade_date", "symbol", turnover_column],
    ].reset_index(drop=True)


def build_candidate_signal_panel(
    controls: pd.DataFrame,
    turnover: pd.DataFrame,
    *,
    turnover_column: str = "turnover_lagged_mean_60d",
    minimum_sample: int = 30,
) -> pd.DataFrame:
    """Create sector-neutral candidate signals and two composite variants.

    ``size_score`` is the existing large-cap score, so its sign is reversed
    for the small-cap candidate.  The raw composite combines raw low-turnover
    with small-cap; the residual composite uses a turnover signal after its
    linear size and low-volatility components have been removed.
    """
    _require_columns(
        controls,
        {"trade_date", "symbol", "industry_l1", "size_score", "lowvol_score"},
        label="controls",
    )
    _require_columns(turnover, {"trade_date", "symbol", turnover_column}, label="turnover")
    if minimum_sample < 3:
        raise ValueError("minimum_sample must be at least 3")

    panel = controls.merge(
        turnover[["trade_date", "symbol", turnover_column]],
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    ).copy()
    dates = panel["trade_date"]
    industries = panel["industry_l1"]
    panel["signal_small_cap"] = _standardize_signal(-panel["size_score"], dates, industries)
    panel["signal_low_turnover"] = _standardize_signal(-panel[turnover_column], dates, industries)
    panel["signal_low_turnover_residual"] = _residualize_by_date(
        panel,
        "signal_low_turnover",
        ("size_score", "lowvol_score"),
        minimum_sample=minimum_sample,
    )
    panel["signal_composite"] = _standardize_signal(
        panel[["signal_small_cap", "signal_low_turnover"]].mean(axis=1),
        dates,
        industries,
    )
    panel["signal_composite_residual"] = _standardize_signal(
        panel[["signal_small_cap", "signal_low_turnover_residual"]].mean(axis=1),
        dates,
        industries,
    )
    panel["signal_large_cap_control"] = _standardize_signal(panel["size_score"], dates, industries)
    panel["signal_lowvol_control"] = _standardize_signal(panel["lowvol_score"], dates, industries)
    return panel


def filter_candidate_eligibility(
    signal_panel: pd.DataFrame,
    universe: pd.DataFrame,
    daily_clean: pd.DataFrame,
    st_history: pd.DataFrame,
    *,
    minimum_listed_days: int = 180,
) -> pd.DataFrame:
    """Apply the formation-date universe, listing-age, suspension, and ST rules."""
    _require_columns(signal_panel, {"trade_date", "symbol"}, label="signal_panel")
    _require_columns(universe, {"trade_date", "symbol"}, label="universe")
    _require_columns(
        daily_clean,
        {"trade_date", "symbol", "listed_days", "amount"},
        label="daily_clean",
    )
    _require_columns(st_history, {"trade_date", "symbol"}, label="st_history")
    if minimum_listed_days < 0:
        raise ValueError("minimum_listed_days must be non-negative")

    eligible = signal_panel.merge(
        universe[["trade_date", "symbol"]].drop_duplicates(),
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    formation = daily_clean[["trade_date", "symbol", "listed_days", "amount"]].drop_duplicates(
        ["trade_date", "symbol"]
    )
    eligible = eligible.merge(
        formation,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    st_keys = pd.MultiIndex.from_frame(st_history[["trade_date", "symbol"]])
    eligible["is_st"] = pd.MultiIndex.from_frame(eligible[["trade_date", "symbol"]]).isin(st_keys)
    mask = (
        eligible["listed_days"].fillna(-1).ge(minimum_listed_days)
        & eligible["amount"].fillna(0).gt(0)
        & ~eligible["is_st"]
    )
    return eligible.loc[mask].drop(columns=["is_st"]).reset_index(drop=True)


def build_buffered_targets(
    signal_panel: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    *,
    signal_column: str,
    target_count: int = 40,
    buffer_count: int = 60,
) -> dict[pd.Timestamp, dict[str, float]]:
    """Build equal-weight targets while retaining holdings within the buffer rank."""
    _require_columns(signal_panel, {"trade_date", "symbol", signal_column}, label="signal_panel")
    if target_count <= 0:
        raise ValueError("target_count must be positive")
    if buffer_count < target_count:
        raise ValueError("buffer_count must be greater than or equal to target_count")

    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()  # ty: ignore[unresolved-attribute]
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    previous: set[str] = set()
    for date in dates:
        group = signal_panel.loc[
            signal_panel["trade_date"].eq(date),
            ["symbol", signal_column],
        ].dropna(subset=[signal_column])
        ranked = group.assign(symbol=group["symbol"].astype(str)).sort_values(
            [signal_column, "symbol"],
            ascending=[False, True],
        )
        ranked["rank"] = np.arange(1, len(ranked) + 1)
        retained = ranked.loc[
            ranked["symbol"].isin(previous) & ranked["rank"].le(buffer_count), "symbol"
        ].tolist()
        selected = retained + [symbol for symbol in ranked["symbol"] if symbol not in set(retained)]
        selected = selected[:target_count]
        if selected:
            weight = 1.0 / len(selected)
            targets[
                pd.Timestamp(date).normalize()  # ty: ignore[unresolved-attribute]
            ] = dict.fromkeys(selected, weight)
        else:
            targets[
                pd.Timestamp(date).normalize()  # ty: ignore[unresolved-attribute]
            ] = {}
        previous = set(selected)
    return targets


def _next_trading_date(
    formation_date: pd.Timestamp,
    trading_dates: pd.DatetimeIndex,
) -> pd.Timestamp | None:
    position = int(trading_dates.searchsorted(formation_date, side="right"))  # ty: ignore[no-matching-overload]
    if position >= len(trading_dates):
        return None
    return pd.Timestamp(trading_dates[position]).normalize()  # ty: ignore[unresolved-attribute]


def map_targets_to_execution_dates(
    formation_targets: dict[pd.Timestamp, dict[str, float]],
    trading_dates: pd.DatetimeIndex,
) -> dict[pd.Timestamp, dict[str, float]]:
    """Move month-end formation targets to the following trading session."""
    mapped: dict[pd.Timestamp, dict[str, float]] = {}
    for formation_date, target in formation_targets.items():
        execution_date = _next_trading_date(
            pd.Timestamp(formation_date),  # ty: ignore[invalid-argument-type]
            trading_dates,
        )
        if execution_date is not None:
            mapped[execution_date] = target
    return mapped


def _active_dates(
    formation_dates: pd.DatetimeIndex,
    trading_dates: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    if len(formation_dates) < 2:
        return pd.DatetimeIndex([])
    active: list[pd.Timestamp] = []
    for first, second in pairwise(formation_dates):
        active.extend(
            pd.Timestamp(date).normalize()  # ty: ignore[unresolved-attribute]
            for date in trading_dates[(trading_dates > first) & (trading_dates <= second)]
        )
    return pd.DatetimeIndex(active).drop_duplicates()


def _long_only_metrics(
    gross: pd.Series,
    net: pd.Series,
    turnover: pd.Series,
    *,
    blocked_entry_days: int,
    blocked_exit_days: int,
) -> dict[str, float | int]:
    clean_gross = gross.dropna()
    clean_net = net.dropna()

    def annual_return(values: pd.Series) -> float:
        if not len(values):
            return float("nan")
        return float(((1.0 + values).prod() ** (252 / len(values)) - 1.0) * 100)

    def max_drawdown(values: pd.Series) -> float:
        if values.empty:
            return float("nan")
        curve = (1.0 + values).cumprod()
        return float((curve / curve.cummax() - 1.0).min() * 100)

    def sharpe(values: pd.Series) -> float:
        if len(values) <= 1 or values.std() <= 0:
            return float("nan")
        return float(values.mean() / values.std() * np.sqrt(252))

    return {
        "days": len(clean_net),
        "gross_annual_return": annual_return(clean_gross),
        "net_annual_return": annual_return(clean_net),
        "gross_max_drawdown": max_drawdown(clean_gross),
        "net_max_drawdown": max_drawdown(clean_net),
        "net_sharpe": sharpe(clean_net),
        "cumulative_gross_return": float(((1.0 + clean_gross).prod() - 1.0) * 100)
        if len(clean_gross)
        else float("nan"),
        "cumulative_net_return": float(((1.0 + clean_net).prod() - 1.0) * 100)
        if len(clean_net)
        else float("nan"),
        "average_daily_turnover": float(turnover.mean()) if len(turnover) else float("nan"),
        "annualized_turnover": float(turnover.mean() * 252) if len(turnover) else float("nan"),
        "blocked_entry_days": blocked_entry_days,
        "blocked_exit_days": blocked_exit_days,
    }


def summarize_long_only_simulations(
    simulations: dict[str, LongOnlySimulation],
    *,
    transaction_cost_bps: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return candidate metrics and aligned daily gross/net/turnover series."""
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
    summary_rows: list[dict[str, Any]] = []
    daily: dict[str, pd.Series] = {}
    for name, simulation in simulations.items():
        active = simulation.active_dates
        gross = simulation.leg.returns.loc[simulation.leg.returns.index.isin(active)]
        turnover = simulation.leg.traded_notional.loc[
            simulation.leg.traded_notional.index.isin(active)
        ]
        costs = turnover * transaction_cost_bps / 10_000.0
        net = gross - costs
        metrics = _long_only_metrics(
            gross,
            net,
            turnover,
            blocked_entry_days=simulation.leg.blocked_entry_days,
            blocked_exit_days=simulation.leg.blocked_exit_days,
        )
        summary_rows.append(
            {
                "candidate": name,
                "signal_column": simulation.signal_column,
                "eligible_rows": simulation.eligible_rows,
                **metrics,
            }
        )
        daily[f"{name}_gross"] = gross
        daily[f"{name}_net"] = net
        daily[f"{name}_turnover"] = turnover
        daily[f"{name}_cost"] = costs
    return pd.DataFrame(summary_rows), pd.DataFrame(daily).sort_index()


def simulate_long_only_candidates(
    signal_panel: pd.DataFrame,
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    candidates: dict[str, str] | None = None,
    *,
    target_count: int = 40,
    buffer_count: int = 60,
    minimum_listed_days: int = 180,
    terminal_return: float = -0.50,
) -> dict[str, LongOnlySimulation]:
    """Run constrained long-only candidates using the shared execution engine."""
    candidates = candidates or dict(SIGNAL_COLUMNS)
    _require_columns(instruments, {"symbol", "delist_date"}, label="instruments")
    eligible = filter_candidate_eligibility(
        signal_panel,
        universe,
        daily_clean,
        st_history,
        minimum_listed_days=minimum_listed_days,
    )
    formation_dates = pd.DatetimeIndex(sorted(eligible["trade_date"].unique())).normalize()  # ty: ignore[unresolved-attribute]
    returns = daily_return_matrix(daily_clean)
    trading_dates = pd.DatetimeIndex(returns.index).normalize()  # ty: ignore[unresolved-attribute]
    matrices = execution_matrices(daily_clean, returns)
    symbol_positions = {str(symbol): index for index, symbol in enumerate(returns.columns)}
    terminal_events = terminal_event_positions(instruments, trading_dates, symbol_positions)
    active_dates = _active_dates(formation_dates, trading_dates)
    simulations: dict[str, LongOnlySimulation] = {}
    for name, signal_column in candidates.items():
        _require_columns(eligible, {signal_column}, label=f"candidate {name}")
        formation_targets = build_buffered_targets(
            eligible,
            formation_dates,
            signal_column=signal_column,
            target_count=target_count,
            buffer_count=buffer_count,
        )
        execution_targets = map_targets_to_execution_dates(formation_targets, trading_dates)
        if not execution_targets:
            continue
        leg = simulate_leg(
            returns,
            matrices,
            execution_targets,
            terminal_events,
            side="long",
            terminal_return=terminal_return,
        )
        simulations[name] = LongOnlySimulation(
            name=name,
            signal_column=signal_column,
            targets=execution_targets,
            leg=leg,
            active_dates=active_dates,
            eligible_rows=len(eligible),
        )
    return simulations
