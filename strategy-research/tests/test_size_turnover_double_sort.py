from __future__ import annotations

import numpy as np
import pandas as pd

from style_factors.size_turnover_double_sort import build_size_turnover_double_sort


def test_double_sort_assigns_deterministic_five_by_five_buckets() -> None:
    formation = pd.Timestamp("2024-01-05")
    symbols = [f"S{index:02d}" for index in range(25)]
    panel = pd.DataFrame(
        {
            "trade_date": formation,
            "symbol": symbols,
            "size_score": np.repeat(np.arange(5, dtype=float), 5),
            "turnover_lagged_mean_60d": np.tile(np.arange(5, dtype=float), 5),
        }
    )
    returns = pd.DataFrame(
        0.01,
        index=pd.date_range("2024-01-06", periods=2, freq="B"),
        columns=symbols,
    )

    result = build_size_turnover_double_sort(
        panel,
        returns,
        formation_dates=pd.DatetimeIndex([formation]),
    )

    assert result.shape[0] == 25
    assert set(result["size_bucket"]) == {1, 2, 3, 4, 5}
    assert set(result["turnover_bucket"]) == {1, 2, 3, 4, 5}
    assert result["observations"].sum() == 25
    assert result["forward_return"].notna().all()


def test_double_sort_ignores_rows_with_missing_signal_inputs() -> None:
    panel = pd.DataFrame(
        {
            "trade_date": pd.Timestamp("2024-01-05"),
            "symbol": ["AAA", "BBB", "CCC"],
            "size_score": [1.0, np.nan, 3.0],
            "turnover_lagged_mean_60d": [1.0, 2.0, 3.0],
        }
    )
    returns = pd.DataFrame(
        0.01,
        index=pd.date_range("2024-01-06", periods=2, freq="B"),
        columns=["AAA", "BBB", "CCC"],
    )

    result = build_size_turnover_double_sort(
        panel,
        returns,
        formation_dates=pd.DatetimeIndex(["2024-01-05"]),
        bucket_count=2,
    )

    assert result["observations"].sum() == 2
