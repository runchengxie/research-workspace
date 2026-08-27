from __future__ import annotations

import pandas as pd
import pytest

from portfolio_backtester.position_backtest import PositionBacktestConfig
from style_factors.portfolio_backtester_adapter import (
    periods_from_positions,
    run_native_position_replay,
    targets_to_positions_by_rebalance,
)


def test_targets_to_positions_by_rebalance_normalizes_and_sorts_targets() -> None:
    targets = {
        pd.Timestamp("2024-02-01"): {"BBB": 0.25, "AAA": 0.5},
        pd.Timestamp("2024-01-02"): {"AAA": 0.75},
    }

    positions = targets_to_positions_by_rebalance(
        targets,
        entry_dates={
            pd.Timestamp("2024-02-01"): pd.Timestamp("2024-02-02"),
            pd.Timestamp("2024-01-02"): pd.Timestamp("2024-01-03"),
        },
    )

    assert positions.to_dict("records") == [
        {
            "rebalance_date": pd.Timestamp("2024-01-02"),
            "entry_date": pd.Timestamp("2024-01-03"),
            "symbol": "AAA",
            "weight": 0.75,
            "side": "long",
        },
        {
            "rebalance_date": pd.Timestamp("2024-02-01"),
            "entry_date": pd.Timestamp("2024-02-02"),
            "symbol": "AAA",
            "weight": 0.5,
            "side": "long",
        },
        {
            "rebalance_date": pd.Timestamp("2024-02-01"),
            "entry_date": pd.Timestamp("2024-02-02"),
            "symbol": "BBB",
            "weight": 0.25,
            "side": "long",
        },
    ]


def test_targets_to_positions_by_rebalance_rejects_duplicate_symbols() -> None:
    targets = pd.DataFrame(
        [
            {"rebalance_date": "20240102", "symbol": "AAA", "weight": 0.5},
            {"rebalance_date": "20240102", "symbol": "AAA", "weight": 0.5},
        ]
    )

    with pytest.raises(ValueError, match="duplicate"):
        targets_to_positions_by_rebalance(targets)


def test_run_native_position_replay_returns_canonical_performance() -> None:
    positions = targets_to_positions_by_rebalance(
        {pd.Timestamp("2024-01-02"): {"AAA": 1.0}},
        entry_dates={pd.Timestamp("2024-01-02"): pd.Timestamp("2024-01-03")},
    )
    pricing = pd.DataFrame(
        [
            {"trade_date": "20240103", "symbol": "AAA", "close": 10.0},
            {"trade_date": "20240104", "symbol": "AAA", "close": 11.0},
        ]
    )
    periods = pd.DataFrame(
        [{"rebalance_date": "20240102", "entry_date": "20240103", "exit_date": "20240104"}]
    )

    result = run_native_position_replay(
        positions,
        pricing,
        periods,
        config=PositionBacktestConfig(price_col="close"),
    )

    assert result.backend_name == "native.position_replay"
    assert result.performance.loc[0, "net_return"] == pytest.approx(0.1)
    assert result.orders.empty


def test_periods_from_positions_closes_each_target_at_next_entry() -> None:
    positions = targets_to_positions_by_rebalance(
        {
            pd.Timestamp("2024-01-02"): {"AAA": 1.0},
            pd.Timestamp("2024-02-01"): {"AAA": 1.0},
        },
        entry_dates={
            pd.Timestamp("2024-01-02"): pd.Timestamp("2024-01-03"),
            pd.Timestamp("2024-02-01"): pd.Timestamp("2024-02-02"),
        },
    )
    pricing = pd.DataFrame(
        [
            {"trade_date": "20240103", "symbol": "AAA", "close": 10.0},
            {"trade_date": "20240202", "symbol": "AAA", "close": 11.0},
            {"trade_date": "20240205", "symbol": "AAA", "close": 12.0},
        ]
    )

    periods = periods_from_positions(positions, pricing)

    assert periods.to_dict("records") == [
        {
            "rebalance_date": pd.Timestamp("2024-01-02"),
            "entry_date": pd.Timestamp("2024-01-03"),
            "exit_date": pd.Timestamp("2024-02-02"),
        },
        {
            "rebalance_date": pd.Timestamp("2024-02-01"),
            "entry_date": pd.Timestamp("2024-02-02"),
            "exit_date": pd.Timestamp("2024-02-05"),
        },
    ]
