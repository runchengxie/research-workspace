from __future__ import annotations

import pandas as pd

from style_factors.loaders.fund_portfolio import materialize_fund_portfolio_state


def test_materialize_fund_portfolio_state_is_pit_and_formation_aligned() -> None:
    events = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                [
                    "2025-01-10",
                    "2025-01-15",
                    "2025-02-20",
                    "2025-03-10",
                ]
            ),
            "symbol": ["000001.SZ", "000002.SZ", "000001.SZ", "000001.SZ"],
            "fund_top10_count_holding_stock": [10.0, 3.0, 7.0, 20.0],
            "fund_top10_stk_float_ratio_sum": [1.5, 0.2, 1.0, 2.5],
            "report_period": ["20241231", "20241231", "20241231", "20241231"],
            "disclosure_date": ["20250109", "20250114", "20250219", "20250309"],
        }
    )
    formation_panel = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                [
                    "2025-01-31",
                    "2025-01-31",
                    "2025-01-31",
                    "2025-02-28",
                    "2025-02-28",
                    "2025-02-28",
                ]
            ),
            "symbol": [
                "000001.SZ",
                "000002.SZ",
                "000003.SZ",
                "000001.SZ",
                "000002.SZ",
                "000003.SZ",
            ],
        }
    )

    result = materialize_fund_portfolio_state(events, formation_panel).set_index(
        ["trade_date", "symbol"]
    )

    jan_a = result.loc[(pd.Timestamp("2025-01-31"), "000001.SZ")]
    feb_a = result.loc[(pd.Timestamp("2025-02-28"), "000001.SZ")]
    feb_b = result.loc[(pd.Timestamp("2025-02-28"), "000002.SZ")]
    feb_c = result.loc[(pd.Timestamp("2025-02-28"), "000003.SZ")]

    assert jan_a["fund_top10_count_holding_stock"] == 10.0
    assert feb_a["fund_top10_count_holding_stock"] == 7.0
    assert feb_a["fund_top10_count_holding_stock_change"] == -3.0
    assert feb_a["fund_top10_stk_float_ratio_sum_change"] == -0.5
    assert feb_a["fund_available_date"] == pd.Timestamp("2025-02-20")
    assert feb_a["fund_state_age_days"] == 8

    # No new disclosure for B in February: carry the latest known PIT state.
    assert feb_b["fund_top10_count_holding_stock"] == 3.0
    assert feb_b["fund_top10_count_holding_stock_change"] == 0.0

    # C has no top-10 fund event after asset coverage starts, so it remains in
    # the cross-section as zero ownership instead of being silently excluded.
    assert feb_c["fund_top10_count_holding_stock"] == 0.0
    assert feb_c["fund_top10_stk_float_ratio_sum"] == 0.0
    assert feb_c["fund_top10_count_holding_stock_change"] == 0.0

    # The March 10 disclosure must not leak into the February formation date.
    assert feb_a["fund_top10_count_holding_stock"] != 20.0
