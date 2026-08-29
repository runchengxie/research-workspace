from __future__ import annotations

import numpy as np
import pandas as pd

from style_factors.size_turnover_double_sort import (
    build_double_sort,
    build_size_turnover_double_sort,
)


def test_generic_double_sort_matches_legacy_without_ties() -> None:
    formation = pd.Timestamp("2024-01-05")
    symbols = [f"S{i:02d}" for i in range(25)]
    panel = pd.DataFrame(
        {
            "trade_date": formation,
            "symbol": symbols,
            "size_score": np.arange(25, dtype=float),
            "turnover_lagged_mean_60d": np.arange(25, dtype=float)[::-1],
        }
    )
    returns = pd.DataFrame(
        0.01,
        index=pd.bdate_range("2024-01-08", periods=2),
        columns=symbols,
    )
    dates = pd.DatetimeIndex([formation])
    legacy = build_size_turnover_double_sort(panel, returns, formation_dates=dates)
    generic = build_double_sort(
        panel,
        returns,
        formation_dates=dates,
        first_column="size_score",
        second_column="turnover_lagged_mean_60d",
    ).rename(columns={"first_bucket": "size_bucket", "second_bucket": "turnover_bucket"})
    pd.testing.assert_frame_equal(
        legacy.reset_index(drop=True),
        generic.reset_index(drop=True),
    )


def test_generic_double_sort_ties_are_resolved_by_symbol() -> None:
    formation = pd.Timestamp("2024-01-05")
    panel = pd.DataFrame(
        {
            "trade_date": formation,
            "symbol": ["D", "C", "B", "A"],
            "x": [1.0, 1.0, 1.0, 1.0],
            "y": [1.0, 2.0, 3.0, 4.0],
        }
    )
    returns = pd.DataFrame(
        0.01,
        index=pd.bdate_range("2024-01-08", periods=2),
        columns=list("ABCD"),
    )
    dates = pd.DatetimeIndex([formation])
    first = build_double_sort(
        panel,
        returns,
        formation_dates=dates,
        first_column="x",
        second_column="y",
        bucket_count=2,
    )
    second = build_double_sort(
        panel.sample(frac=1.0, random_state=3),
        returns,
        formation_dates=dates,
        first_column="x",
        second_column="y",
        bucket_count=2,
    )
    pd.testing.assert_frame_equal(first, second)
