"""Restricted cash-ledger capacity checks for the microcap robustness study."""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio_backtester.execution_sim import (
    ExecutionSimConfig,
    simulate_execution_adjusted_nav,
)

from .portfolio_backtester_adapter import targets_to_positions_by_rebalance


def _entry_dates_for_targets(
    targets: dict[pd.Timestamp, dict[str, float]],
    trading_dates: pd.DatetimeIndex,
) -> dict[pd.Timestamp, pd.Timestamp]:
    entries: dict[pd.Timestamp, pd.Timestamp] = {}
    calendar = pd.DatetimeIndex(trading_dates).normalize().sort_values().unique()
    for formation_date in targets:
        formation = pd.Timestamp(formation_date).normalize()
        position = int(calendar.searchsorted(formation, side="right"))
        if position < len(calendar):
            entries[formation] = pd.Timestamp(calendar[position]).normalize()
    return entries


def build_microcap_capacity_matrix(
    target_plans: dict[
        tuple[str, float, str, str],
        dict[pd.Timestamp, dict[str, float]],
    ],
    daily_clean: pd.DataFrame,
    *,
    transaction_cost_bps: float,
    capitals: tuple[float, ...] = (
        10_000_000.0,
        100_000_000.0,
        500_000_000.0,
    ),
) -> pd.DataFrame:
    """Run only the pre-registered high-value microcap capacity arms."""
    required = {
        "trade_date",
        "symbol",
        "tr_close",
        "amount",
        "pct_chg",
        "is_limit_up",
        "is_limit_down",
    }
    missing = sorted(required - set(daily_clean.columns))
    if missing:
        raise ValueError("daily_clean is missing required columns: " + ", ".join(missing))
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
    if any(not np.isfinite(capital) or capital <= 0 for capital in capitals):
        raise ValueError("capitals must contain only finite positive values")

    pricing = daily_clean[
        [
            "trade_date",
            "symbol",
            "tr_close",
            "amount",
            "pct_chg",
            "is_limit_up",
            "is_limit_down",
        ]
    ].rename(columns={"tr_close": "close"})
    trading_dates = pd.DatetimeIndex(
        pd.to_datetime(pricing["trade_date"]).dt.normalize().unique()
    ).sort_values()

    rows: list[dict[str, object]] = []
    for key, targets in target_plans.items():
        candidate, exclusion, weighting, buffer_setting = key
        if buffer_setting != "buffered":
            continue
        if candidate not in {"small_cap", "composite"}:
            continue
        if float(exclusion) not in {0.0, 0.3}:
            continue

        entry_dates = _entry_dates_for_targets(targets, trading_dates)
        usable_targets = {
            pd.Timestamp(date).normalize(): target
            for date, target in targets.items()
            if pd.Timestamp(date).normalize() in entry_dates
        }
        if not usable_targets:
            continue
        positions = targets_to_positions_by_rebalance(
            usable_targets,
            entry_dates=entry_dates,
        )
        if positions.empty:
            continue

        for capital in capitals:
            config = ExecutionSimConfig(
                enabled=True,
                portfolio_value=float(capital),
                participation_rate=0.05,
                liquidity_cols=("amount",),
                liquidity_notional_multiplier=1_000.0,
                buy_max_days=3,
                sell_max_days=5,
                round_lot=100,
                enforce_t1=True,
            )
            result = simulate_execution_adjusted_nav(
                positions,
                pricing,
                config,
                price_col="close",
                tradable_col="amount",
                transaction_cost_bps=transaction_cost_bps,
            )
            stats = result.summary.get("stats", {})
            annual_return = stats.get("ann_return")
            max_drawdown = stats.get("max_drawdown")
            rows.append(
                {
                    "candidate": candidate,
                    "exclusion_percentile": float(exclusion),
                    "weighting": weighting,
                    "buffer_setting": buffer_setting,
                    "capital": float(capital),
                    "net_annual_return": (
                        float(annual_return) * 100.0 if annual_return is not None else np.nan
                    ),
                    "net_sharpe": stats.get("sharpe"),
                    "max_drawdown": (
                        float(max_drawdown) * 100.0 if max_drawdown is not None else np.nan
                    ),
                    "fill_ratio": result.summary.get("fill_ratio"),
                    "avg_cash_weight": result.summary.get("avg_cash_weight"),
                    "cumulative_turnover": (
                        float(result.summary.get("filled_notional", 0.0)) / float(capital)
                    ),
                }
            )
    return pd.DataFrame(rows)


__all__ = ["build_microcap_capacity_matrix"]
