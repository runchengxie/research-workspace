from __future__ import annotations

import pandas as pd
import pytest

from experiments.macro_context_shadow.shibor_regime import (
    build_forward_labels,
    build_shibor_exposure_interactions,
    build_shibor_regimes,
)


def _context() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "series_id": ["rates.shibor_3m"] * 7,
            "period_end": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                ],
                utc=True,
            ),
            "value": [1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.2],
            "available_at": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                ],
                utc=True,
            ),
            "source_retrieved_at": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                ],
                utc=True,
            ),
            "revision_covered": [True, True, True, True, True, True, False],
            "reconstructed": [False, False, False, False, False, False, True],
        }
    )


def test_shibor_regimes_are_as_of_safe_and_mark_strict_rows() -> None:
    result = build_shibor_regimes(_context(), pd.Timestamp("2026-01-06T12:00:00Z"))
    assert result["period_end"].max() == pd.Timestamp("2026-01-06T00:00:00Z")
    assert result["regime"].tolist() == ["flat", "flat", "flat", "flat", "flat", "up"]
    assert result["strict_pit"].tolist() == [True] * 6


def test_exposure_interactions_use_latest_context_without_lookahead() -> None:
    stocks = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-02", "2026-01-03"], utc=True),
            "symbol": ["A", "A"],
            "leverage": [2.0, 3.0],
            "value_score": [0.5, 0.6],
        }
    )
    regimes = build_shibor_regimes(_context(), pd.Timestamp("2026-01-03T12:00:00Z"))
    result = build_shibor_exposure_interactions(stocks, regimes)
    assert result.loc[0, "ctx__shibor_3m__x__leverage"] == 2.0
    assert result.loc[1, "ctx__shibor_3m__x__value_score"] == 0.6


def test_forward_labels_shift_within_symbol() -> None:
    prices = pd.DataFrame(
        {
            "symbol": ["A", "A", "A", "B", "B"],
            "trade_date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-01", "2026-01-02"]
            ),
            "adj_close": [10.0, 11.0, 12.0, 20.0, 22.0],
        }
    )
    result = build_forward_labels(prices, [1, 2])
    assert result.loc[(result.symbol == "A") & (result.trade_date == "2026-01-01"), "fwd_1d"].iloc[
        0
    ] == pytest.approx(0.1)
    assert pd.isna(
        result.loc[(result.symbol == "B") & (result.trade_date == "2026-01-02"), "fwd_1d"].iloc[0]
    )
