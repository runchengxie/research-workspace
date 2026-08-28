from __future__ import annotations

import pandas as pd
import pytest

from experiments.macro_context_shadow.fund_context import (
    build_fund_context_features,
)


def test_build_fund_context_features_is_explicit_and_bounded() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["A", "B", "C", "D"],
            "trade_date": pd.to_datetime(["2026-01-02"] * 4),
            "fund_hold_mv_to_float_mv": [0.01, 0.02, 0.20, 0.30],
            "fund_hold_mv_to_float_mv_qoq_change": [0.10, -0.10, 0.20, -0.20],
            "fund_count_holding_stock_qoq_change": [1.0, 0.0, 2.0, -1.0],
            "fund_top10_hold_mv_to_float_mv": [0.005, 0.01, 0.19, 0.29],
        }
    )

    result = build_fund_context_features(frame)

    assert {
        "fund_crowding_level",
        "fund_ownership_change",
        "fund_holder_count_change",
        "fund_low_crowding_accumulation",
        "fund_top10_concentration",
        "fund_accumulation_without_crowding",
    }.issubset(result.columns)
    assert result["fund_low_crowding_accumulation"].isin([0.0, 1.0]).all()
    assert result["fund_accumulation_without_crowding"].isin([0.0, 1.0]).all()
    assert result["fund_top10_concentration"].between(0.0, 1.0).all()


def test_fund_context_features_require_available_date_when_requested() -> None:
    with pytest.raises(ValueError, match="available_date"):
        build_fund_context_features(
            pd.DataFrame(
                {
                    "symbol": ["A"],
                    "trade_date": [pd.Timestamp("2026-01-02")],
                    "fund_hold_mv_to_float_mv": [0.1],
                }
            ),
            require_available_date=True,
        )
