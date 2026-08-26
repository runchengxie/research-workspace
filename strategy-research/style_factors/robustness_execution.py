"""Daily execution mechanics for constrained style-factor robustness tests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class LegSimulation:
    returns: pd.Series
    traded_notional: pd.Series
    blocked_entry_days: int
    blocked_exit_days: int
    terminal_events: int


def _validated_trade_weight_matrix(
    max_trade_weight: np.ndarray | None,
    expected_shape: tuple[int, ...],
) -> np.ndarray | None:
    if max_trade_weight is None:
        return None
    matrix = np.asarray(max_trade_weight, dtype=float)
    if matrix.shape != expected_shape:
        raise ValueError("max_trade_weight must have the expected shape")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("max_trade_weight must contain only finite values")
    if np.any(matrix < 0):
        raise ValueError("max_trade_weight must be non-negative")
    return matrix


def daily_return_matrix(daily_clean: pd.DataFrame) -> pd.DataFrame:
    """Build the stock-by-date return matrix used by the simulator."""
    returns = daily_clean.pivot(
        index="trade_date",
        columns="symbol",
        values="pct_chg",
    ).sort_index()
    return returns.astype(float) / 100.0


def execution_matrices(
    daily_clean: pd.DataFrame,
    returns: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build tradability and price-limit matrices aligned to returns."""
    index = returns.index
    columns = returns.columns

    def flag_matrix(column: str) -> np.ndarray:
        matrix = daily_clean.pivot(
            index="trade_date",
            columns="symbol",
            values=column,
        ).reindex(index=index, columns=columns)
        return matrix.fillna(False).to_numpy(dtype=bool)

    tradable_source = daily_clean[["trade_date", "symbol"]].copy()
    tradable_source["tradable"] = daily_clean["amount"].fillna(0).gt(0).to_numpy()
    tradable = tradable_source.pivot(
        index="trade_date",
        columns="symbol",
        values="tradable",
    ).reindex(index=index, columns=columns)
    return (
        tradable.fillna(False).to_numpy(dtype=bool),
        flag_matrix("is_limit_up"),
        flag_matrix("is_limit_down"),
    )


def terminal_event_positions(
    instruments: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    symbol_positions: dict[str, int],
) -> dict[pd.Timestamp, np.ndarray]:
    """Map each known delisting to its first on-calendar terminal-mark date."""
    events: dict[pd.Timestamp, list[int]] = {}
    for row in instruments.dropna(subset=["delist_date"]).itertuples(index=False):
        symbol = str(row.symbol)  # ty: ignore[unresolved-attribute]
        if symbol not in symbol_positions:
            continue
        delist_date = pd.Timestamp(row.delist_date).normalize()  # ty: ignore[unresolved-attribute]
        position = int(trading_dates.searchsorted(delist_date, side="left"))  # ty: ignore[no-matching-overload]
        if position >= len(trading_dates):
            continue
        event_date = pd.Timestamp(trading_dates[position]).normalize()  # ty: ignore[unresolved-attribute]
        events.setdefault(event_date, []).append(symbol_positions[symbol])
    return {date: np.asarray(positions, dtype=int) for date, positions in events.items()}


def attempt_pending_orders(
    weights: np.ndarray,
    target: np.ndarray,
    pending: np.ndarray,
    *,
    tradable: np.ndarray,
    limit_up: np.ndarray,
    limit_down: np.ndarray,
    side: str,
    max_trade_weight: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, float, bool, bool]:
    """Attempt one day's pending orders under suspension and limit constraints."""
    before = weights.copy()
    decreasing = pending & (target < weights - 1e-12)
    increasing = pending & (target > weights + 1e-12)
    exit_allowed = tradable & ~(limit_down if side == "long" else limit_up)
    entry_allowed = tradable & ~(limit_up if side == "long" else limit_down)
    trade_limit = _validated_trade_weight_matrix(max_trade_weight, weights.shape)
    if trade_limit is None:
        trade_limit = np.full(weights.shape, np.inf, dtype=float)

    executable_decreases = decreasing & exit_allowed
    decreases = (
        np.minimum(
            np.maximum(weights - target, 0.0),
            trade_limit,
        )
        * executable_decreases
    )
    weights -= decreases
    pending[executable_decreases & (np.abs(target - weights) <= 1e-12)] = False

    executable_increases = increasing & entry_allowed
    desired = np.maximum(target - weights, 0.0) * executable_increases
    desired = np.minimum(desired, trade_limit)
    desired_total = float(desired.sum())
    capacity = max(0.0, 1.0 - float(weights.sum()))
    scale = min(1.0, capacity / desired_total) if desired_total > 0 else 0.0
    weights += desired * scale
    filled = executable_increases & (weights >= target - 1e-12)
    pending[filled] = False

    settled = pending & (np.abs(target - weights) <= 1e-12)
    pending[settled] = False
    traded_notional = float(np.abs(weights - before).sum())
    blocked_entry = bool((increasing & ~entry_allowed).any())
    blocked_exit = bool((decreasing & ~exit_allowed).any())
    return weights, pending, traded_notional, blocked_entry, blocked_exit


def simulate_leg(
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    targets: dict[pd.Timestamp, dict[str, float]],
    terminal_events: dict[pd.Timestamp, np.ndarray],
    *,
    side: str,
    terminal_return: float,
    max_trade_weight: np.ndarray | None = None,
) -> LegSimulation:
    """Simulate one long-only leg with causal close execution."""
    symbols = returns.columns
    symbol_positions = {str(symbol): index for index, symbol in enumerate(symbols)}
    weights = np.zeros(len(symbols), dtype=float)
    target = weights.copy()
    pending = np.zeros(len(symbols), dtype=bool)
    daily_returns: list[float] = []
    daily_turnover: list[float] = []
    blocked_entry_days = 0
    blocked_exit_days = 0
    terminal_events_applied = 0

    tradable_matrix, limit_up_matrix, limit_down_matrix = matrices
    max_trade_weight = _validated_trade_weight_matrix(max_trade_weight, returns.shape)
    for row_number, (date, row) in enumerate(
        zip(returns.index, returns.to_numpy(dtype=float), strict=True)
    ):
        normalized_date = pd.Timestamp(date).normalize()  # ty: ignore[unresolved-attribute]
        if normalized_date in targets:
            target = np.zeros(len(symbols), dtype=float)
            for symbol, value in targets[normalized_date].items():
                position = symbol_positions.get(symbol)
                if position is not None:
                    target[position] = value
            pending = np.abs(target - weights) > 1e-12

        asset_returns = np.nan_to_num(row, nan=0.0, posinf=0.0, neginf=0.0)
        event_positions = terminal_events.get(normalized_date)
        held_terminal_positions = np.asarray([], dtype=int)
        if event_positions is not None:
            held_terminal_positions = event_positions[weights[event_positions] > 0]
            asset_returns[held_terminal_positions] = terminal_return
            terminal_events_applied += len(held_terminal_positions)

        leg_return = float(weights @ asset_returns)
        daily_returns.append(leg_return)
        gross_total = 1.0 + leg_return
        if gross_total > 0:
            weights = weights * (1.0 + asset_returns) / gross_total
        if held_terminal_positions.size:
            weights[held_terminal_positions] = 0.0
            target[held_terminal_positions] = 0.0
            pending[held_terminal_positions] = False

        traded_notional = 0.0
        if pending.any():
            weights, pending, traded_notional, blocked_entry, blocked_exit = attempt_pending_orders(
                weights,
                target,
                pending,
                tradable=tradable_matrix[row_number],
                limit_up=limit_up_matrix[row_number],
                limit_down=limit_down_matrix[row_number],
                side=side,
                max_trade_weight=(
                    max_trade_weight[row_number] if max_trade_weight is not None else None
                ),
            )
            blocked_entry_days += int(blocked_entry)
            blocked_exit_days += int(blocked_exit)
        daily_turnover.append(traded_notional)

    index = pd.DatetimeIndex(returns.index, name="trade_date")
    return LegSimulation(
        returns=pd.Series(daily_returns, index=index, dtype=float),
        traded_notional=pd.Series(daily_turnover, index=index, dtype=float),
        blocked_entry_days=blocked_entry_days,
        blocked_exit_days=blocked_exit_days,
        terminal_events=terminal_events_applied,
    )


def profile_results(
    long_leg: LegSimulation,
    short_leg: LegSimulation,
    *,
    cost_bps: float,
    active_dates: pd.DatetimeIndex | None = None,
) -> dict[str, pd.Series]:
    """Combine two simulated legs and deduct traded-notional costs."""
    gross_long_short = long_leg.returns - short_leg.returns
    costs = (long_leg.traded_notional + short_leg.traded_notional) * cost_bps / 10_000.0
    result = {
        "long_short": gross_long_short - costs,
        "long": long_leg.returns,
        "short": short_leg.returns,
        "transaction_cost": costs,
    }
    if active_dates is not None:
        result = {
            name: series.loc[series.index.isin(active_dates)] for name, series in result.items()
        }
    return result
