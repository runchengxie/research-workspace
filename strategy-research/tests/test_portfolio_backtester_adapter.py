from __future__ import annotations

import pandas as pd
import pytest

from portfolio_backtester.execution import ParticipationSlippageModel
from portfolio_backtester.execution_sim import ExecutionSimConfig
from portfolio_backtester.position_backtest import PositionBacktestConfig
from style_factors.portfolio_backtester_adapter import (
    attribute_delayed_fills,
    owner_execution_receipt,
    periods_from_positions,
    run_native_position_replay,
    targets_to_positions_by_rebalance,
)


def test_attribute_delayed_fills_separates_delay_and_impact() -> None:
    orders = pd.DataFrame(
        [
            {
                "rebalance_date": "20240102",
                "entry_date": "20240103",
                "symbol": "AAA",
                "side": "buy",
                "requested_notional": 1000.0,
                "filled_notional": 600.0,
                "unfilled_notional": 400.0,
            }
        ]
    )
    fills = pd.DataFrame(
        [
            {
                "rebalance_date": "20240102",
                "entry_date": "20240103",
                "symbol": "AAA",
                "side": "buy",
                "trade_date": "20240104",
                "filled_notional": 600.0,
                "cost_temporary_impact": 6.0,
            }
        ]
    )
    pricing = pd.DataFrame(
        [
            {"trade_date": "20240103", "symbol": "AAA", "close": 10.0},
            {"trade_date": "20240104", "symbol": "AAA", "close": 9.0},
        ]
    )

    attribution = attribute_delayed_fills(orders, fills, pricing)

    row = attribution.iloc[0]
    assert row["delay_days"] == 1
    assert row["reference_return_to_first_fill"] == pytest.approx(-0.1)
    assert row["delay_opportunity_cost"] == pytest.approx(-40.0)
    assert row["temporary_impact"] == pytest.approx(6.0)


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


def test_native_position_replay_passes_slippage_to_owner_ledger() -> None:
    positions = targets_to_positions_by_rebalance(
        {pd.Timestamp("2024-01-02"): {"AAA": 1.0}},
        entry_dates={pd.Timestamp("2024-01-02"): pd.Timestamp("2024-01-03")},
    )
    pricing = pd.DataFrame(
        [
            {"trade_date": "20240103", "symbol": "AAA", "close": 10.0, "amount": 10_000.0},
            {"trade_date": "20240104", "symbol": "AAA", "close": 11.0, "amount": 10_000.0},
        ]
    )
    periods = pd.DataFrame(
        [{"rebalance_date": "20240102", "entry_date": "20240103", "exit_date": "20240104"}]
    )
    result = run_native_position_replay(
        positions,
        pricing,
        periods,
        config=PositionBacktestConfig(price_col="close", tradable_col="amount"),
        ledger=True,
        ledger_config=ExecutionSimConfig(
            enabled=True,
            portfolio_value=1_000.0,
            participation_rate=1.0,
            liquidity_cols=("amount",),
        ),
        slippage_model=ParticipationSlippageModel(
            impact_bps=100.0,
            amount_col="amount",
            portfolio_value=1_000.0,
        ),
    )

    assert result.capabilities.daily_ledger is True
    assert result.fills["cost_temporary_impact"].sum() > 0.0
    receipt = owner_execution_receipt(result)
    assert receipt["daily_ledger"] is True
    assert receipt["partial_fills_supported"] is True
    assert receipt["canonical_status"] == "comparison_only"
