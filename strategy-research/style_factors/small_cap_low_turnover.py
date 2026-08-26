"""Bounded small-cap and low-turnover strategy exploration helpers.

This module is deliberately an exploration layer.  It does not register a
production strategy or change the shared portfolio-backtester API.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

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


@dataclass(frozen=True)
class _LongOnlyExecutionContext:
    return_matrix: pd.DataFrame
    matrix_tuple: tuple[np.ndarray, np.ndarray, np.ndarray]
    trading_dates: pd.DatetimeIndex
    capacity_matrix: np.ndarray | None
    terminal_events: dict[pd.Timestamp, np.ndarray]
    active_dates: pd.DatetimeIndex


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
    statistic: Literal["mean", "median"] = "mean",
) -> pd.DataFrame:
    """Build turnover lookbacks that exclude the formation day's observation."""
    if window <= 0:
        raise ValueError("window must be positive")
    if not 1 <= minimum_observations <= window:
        raise ValueError("minimum_observations must be between 1 and window")
    if statistic not in {"mean", "median"}:
        raise ValueError("statistic must be 'mean' or 'median'")
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
    turnover_column = f"turnover_lagged_{statistic}_{window}d"
    calendar = pd.DatetimeIndex(sorted(frame["trade_date"].unique()))
    turnover_matrix = frame.pivot(
        index="trade_date",
        columns="symbol",
        values="turnover_rate",
    ).reindex(index=calendar)
    lagged = getattr(
        turnover_matrix.shift(1).rolling(
            window,
            min_periods=minimum_observations,
        ),
        statistic,
    )()
    available = frame.loc[
        frame["trade_date"].isin(dates),
        ["trade_date", "symbol"],
    ].drop_duplicates()
    values = (
        lagged.loc[lagged.index.isin(dates)]
        .rename_axis(index="trade_date", columns="symbol")
        .reset_index()
        .melt(
            id_vars="trade_date",
            var_name="symbol",
            value_name=turnover_column,
        )
    )
    return (
        available.merge(
            values,
            on=["trade_date", "symbol"],
            how="left",
            validate="one_to_one",
        )
        .sort_values(["trade_date", "symbol"])
        .reset_index(drop=True)
    )


def build_trade_capacity_matrix(
    daily_clean: pd.DataFrame,
    returns: pd.DataFrame,
    *,
    initial_capital: float,
    participation_rate: float,
) -> np.ndarray:
    """Convert daily traded amount into a per-symbol maximum trade weight.

    The clean-data contract stores ``amount`` in thousand CNY.  The matrix is
    a research approximation that uses each symbol's prior observed amount,
    holds capital constant, and limits daily traded notional to an ADV
    participation fraction.
    """
    _require_columns(daily_clean, {"trade_date", "symbol", "amount"}, label="daily_clean")
    if not np.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if not 0 <= participation_rate <= 1:
        raise ValueError("participation_rate must be between 0 and 1")
    amount_frame = daily_clean[["trade_date", "symbol", "amount"]].copy()
    amount_frame["trade_date"] = pd.to_datetime(amount_frame["trade_date"]).dt.normalize()
    amount_frame["symbol"] = amount_frame["symbol"].astype(str)
    amount_frame["amount"] = pd.to_numeric(amount_frame["amount"], errors="coerce")
    amount_frame = amount_frame.sort_values(["symbol", "trade_date"])
    amount_frame["available_amount"] = amount_frame.groupby("symbol", sort=False)["amount"].shift(1)
    amounts = amount_frame.pivot(
        index="trade_date",
        columns="symbol",
        values="available_amount",
    ).reindex(index=returns.index, columns=returns.columns)
    amounts = amounts.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return amounts.to_numpy(dtype=float) * 1_000.0 * participation_rate / initial_capital


def round_target_weights_to_lots(
    targets: dict[pd.Timestamp, dict[str, float]],
    daily_clean: pd.DataFrame,
    *,
    initial_capital: float,
    lot_size: int = 100,
) -> dict[pd.Timestamp, dict[str, float]]:
    """Floor target share counts using the prior close and A-share lot size."""
    _require_columns(daily_clean, {"trade_date", "symbol", "close"}, label="daily_clean")
    if not np.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if lot_size <= 0:
        raise ValueError("lot_size must be positive")
    price_frame = daily_clean[["trade_date", "symbol", "close"]].copy()
    price_frame["trade_date"] = pd.to_datetime(price_frame["trade_date"]).dt.normalize()
    price_frame["symbol"] = price_frame["symbol"].astype(str)
    price_frame["close"] = pd.to_numeric(price_frame["close"], errors="coerce")
    price_frame = price_frame.sort_values(["symbol", "trade_date"])
    price_frame["available_close"] = price_frame.groupby("symbol", sort=False)["close"].shift(1)
    prices = price_frame.pivot(
        index="trade_date",
        columns="symbol",
        values="available_close",
    ).apply(pd.to_numeric, errors="coerce")
    rounded: dict[pd.Timestamp, dict[str, float]] = {}
    for date, target in targets.items():
        execution_date = pd.Timestamp(date).normalize()  # ty: ignore[unresolved-attribute]
        if execution_date not in prices.index:
            rounded[execution_date] = {}
            continue
        row = prices.loc[execution_date]
        target_after_rounding: dict[str, float] = {}
        for symbol, weight in target.items():
            price = row.get(symbol, np.nan)
            if not np.isfinite(price) or price <= 0 or weight <= 0:
                continue
            shares = np.floor(initial_capital * weight / (price * lot_size)) * lot_size
            if shares > 0:
                target_after_rounding[str(symbol)] = float(shares * price / initial_capital)
        rounded[execution_date] = target_after_rounding
    return rounded


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


def _build_long_only_execution_context(
    daily_clean: pd.DataFrame,
    instruments: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    *,
    initial_capital: float | None,
    participation_rate: float | None,
    returns: pd.DataFrame | None,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
) -> _LongOnlyExecutionContext:
    if returns is None:
        return_matrix = daily_return_matrix(daily_clean)
        matrix_tuple = execution_matrices(daily_clean, return_matrix)
    else:
        assert matrices is not None
        return_matrix = returns
        matrix_tuple = matrices
    trading_dates = pd.DatetimeIndex(return_matrix.index).normalize()  # ty: ignore[unresolved-attribute]
    capacity_matrix = (
        build_trade_capacity_matrix(
            daily_clean,
            return_matrix,
            initial_capital=initial_capital,
            participation_rate=participation_rate,
        )
        if participation_rate is not None and initial_capital is not None
        else None
    )
    symbol_positions = {str(symbol): index for index, symbol in enumerate(return_matrix.columns)}
    return _LongOnlyExecutionContext(
        return_matrix=return_matrix,
        matrix_tuple=matrix_tuple,
        trading_dates=trading_dates,
        capacity_matrix=capacity_matrix,
        terminal_events=terminal_event_positions(instruments, trading_dates, symbol_positions),
        active_dates=_active_dates(formation_dates, trading_dates),
    )


def _simulate_long_only_candidate(
    *,
    name: str,
    signal_column: str,
    eligible: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    daily_clean: pd.DataFrame,
    context: _LongOnlyExecutionContext,
    target_count: int,
    buffer_count: int,
    initial_capital: float | None,
    lot_size: int | None,
    terminal_return: float,
) -> LongOnlySimulation | None:
    _require_columns(eligible, {signal_column}, label=f"candidate {name}")
    formation_targets = build_buffered_targets(
        eligible,
        formation_dates,
        signal_column=signal_column,
        target_count=target_count,
        buffer_count=buffer_count,
    )
    execution_targets = map_targets_to_execution_dates(
        formation_targets,
        context.trading_dates,
    )
    if lot_size is not None and initial_capital is not None:
        execution_targets = round_target_weights_to_lots(
            execution_targets,
            daily_clean,
            initial_capital=initial_capital,
            lot_size=lot_size,
        )
    if not execution_targets:
        return None
    return LongOnlySimulation(
        name=name,
        signal_column=signal_column,
        targets=execution_targets,
        leg=simulate_leg(
            context.return_matrix,
            context.matrix_tuple,
            execution_targets,
            context.terminal_events,
            side="long",
            terminal_return=terminal_return,
            max_trade_weight=context.capacity_matrix,
        ),
        active_dates=context.active_dates,
        eligible_rows=len(eligible),
    )


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
    initial_capital: float | None = None,
    lot_size: int | None = None,
    participation_rate: float | None = None,
    returns: pd.DataFrame | None = None,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> dict[str, LongOnlySimulation]:
    """Run constrained long-only candidates using the shared execution engine."""
    candidates = candidates or dict(SIGNAL_COLUMNS)
    _require_columns(instruments, {"symbol", "delist_date"}, label="instruments")
    if lot_size is not None and initial_capital is None:
        raise ValueError("initial_capital is required when lot_size is supplied")
    if participation_rate is not None and initial_capital is None:
        raise ValueError("initial_capital is required when participation_rate is supplied")
    if initial_capital is not None and (not np.isfinite(initial_capital) or initial_capital <= 0):
        raise ValueError("initial_capital must be positive")
    if (returns is None) != (matrices is None):
        raise ValueError("returns and matrices must be supplied together")
    eligible = filter_candidate_eligibility(
        signal_panel,
        universe,
        daily_clean,
        st_history,
        minimum_listed_days=minimum_listed_days,
    )
    formation_dates = pd.DatetimeIndex(sorted(eligible["trade_date"].unique())).normalize()  # ty: ignore[unresolved-attribute]
    context = _build_long_only_execution_context(
        daily_clean,
        instruments,
        formation_dates,
        initial_capital=initial_capital,
        participation_rate=participation_rate,
        returns=returns,
        matrices=matrices,
    )
    simulations: dict[str, LongOnlySimulation] = {}
    for name, signal_column in candidates.items():
        simulation = _simulate_long_only_candidate(
            name=name,
            signal_column=signal_column,
            eligible=eligible,
            formation_dates=formation_dates,
            daily_clean=daily_clean,
            context=context,
            target_count=target_count,
            buffer_count=buffer_count,
            initial_capital=initial_capital,
            lot_size=lot_size,
            terminal_return=terminal_return,
        )
        if simulation is not None:
            simulations[name] = simulation
    return simulations
