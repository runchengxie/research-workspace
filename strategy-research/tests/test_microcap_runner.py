from __future__ import annotations

import pandas as pd

from experiments.style_factors.microcap_robustness_20260829 import (
    build_microcap_run_manifest,
)
from style_factors.microcap_robustness import build_microcap_capacity_matrix


def test_microcap_manifest_freezes_primary_matrix() -> None:
    manifest = build_microcap_run_manifest(
        data_start="2015-01-01",
        data_end="2026-07-31",
        alpha_commit="abc",
        portfolio_commit="def",
        minimum_listed_days=180,
    )
    assert manifest["exclusion_percentiles"] == [0.0, 0.1, 0.2, 0.3]
    assert manifest["weighting_modes"] == ["equal", "value"]
    assert manifest["rebalance_frequency"] == "monthly"
    assert manifest["development_end"] == "2023-12-31"
    assert manifest["holdout_start"] == "2024-01-01"
    assert manifest["alpha_commit"] == "abc"
    assert manifest["portfolio_commit"] == "def"


def test_capacity_matrix_runs_only_frozen_buffered_arms() -> None:
    formation_a = pd.Timestamp("2024-01-02")
    formation_b = pd.Timestamp("2024-01-05")
    target_plans = {
        ("small_cap", 0.0, "equal", "buffered"): {
            formation_a: {"A": 1.0},
            formation_b: {"B": 1.0},
        },
        ("small_cap", 0.1, "equal", "buffered"): {
            formation_a: {"A": 1.0},
        },
        ("small_cap", 0.0, "equal", "no_buffer"): {
            formation_a: {"A": 1.0},
        },
    }
    dates = pd.bdate_range("2024-01-02", "2024-01-12")
    daily = pd.DataFrame(
        [
            {
                "trade_date": date,
                "symbol": symbol,
                "tr_close": 10.0 + index,
                "pct_chg": 0.1 * (index + 1),
                "amount": 1_000_000.0,
                "is_limit_up": False,
                "is_limit_down": False,
            }
            for date in dates
            for index, symbol in enumerate(["A", "B"])
        ]
    )

    result = build_microcap_capacity_matrix(
        target_plans,
        daily,
        transaction_cost_bps=10.0,
        capitals=(1_000_000.0,),
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert row["candidate"] == "small_cap"
    assert row["exclusion_percentile"] == 0.0
    assert row["weighting"] == "equal"
    assert row["capital"] == 1_000_000.0
    assert 0 <= row["fill_ratio"] <= 1
