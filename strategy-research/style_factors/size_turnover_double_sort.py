"""Formation-date double-sort diagnostics for style-factor research."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _stable_bucket(cross: pd.DataFrame, column: str, bucket_count: int) -> pd.Series:
    ordered = cross[["symbol", column]].sort_values([column, "symbol"], kind="stable")
    ranks = pd.Series(np.arange(1, len(ordered) + 1), index=ordered.index)
    buckets = np.ceil(ranks * bucket_count / len(ordered)).astype(int)
    return buckets.reindex(cross.index)


def build_double_sort(
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    first_column: str,
    second_column: str,
    bucket_count: int = 5,
) -> pd.DataFrame:
    """Return long-form forward returns for two formation-date characteristics."""
    required = {"trade_date", "symbol", first_column, second_column}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError("panel is missing required columns: " + ", ".join(missing))
    if bucket_count < 2:
        raise ValueError("bucket_count must be at least 2")

    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    if dates.empty:
        return pd.DataFrame(
            columns=[
                "formation_date",
                "first_bucket",
                "second_bucket",
                "observations",
                "forward_return",
            ]
        )
    returns = daily_returns.copy()
    returns.index = pd.to_datetime(returns.index).normalize()

    rows: list[dict[str, object]] = []
    for index, formation_date in enumerate(dates):
        next_date = dates[index + 1] if index + 1 < len(dates) else returns.index.max()
        cross = panel.loc[
            pd.to_datetime(panel["trade_date"]).dt.normalize().eq(formation_date),
            ["symbol", first_column, second_column],
        ].copy()
        cross[first_column] = pd.to_numeric(cross[first_column], errors="coerce")
        cross[second_column] = pd.to_numeric(cross[second_column], errors="coerce")
        cross = cross.dropna(
            subset=["symbol", first_column, second_column]
        ).drop_duplicates("symbol")
        if cross.empty:
            continue

        cross["first_bucket"] = _stable_bucket(cross, first_column, bucket_count)
        cross["second_bucket"] = _stable_bucket(cross, second_column, bucket_count)
        window = returns.loc[(returns.index > formation_date) & (returns.index <= next_date)]
        forward = (1.0 + window).prod(axis=0, min_count=1) - 1.0
        cross["forward_return"] = cross["symbol"].map(forward)
        grouped = cross.groupby(["first_bucket", "second_bucket"], as_index=False).agg(
            observations=("forward_return", "count"),
            forward_return=("forward_return", "mean"),
        )
        grid = pd.MultiIndex.from_product(
            [range(1, bucket_count + 1), range(1, bucket_count + 1)],
            names=["first_bucket", "second_bucket"],
        )
        grouped = (
            grouped.set_index(["first_bucket", "second_bucket"])
            .reindex(grid)
            .reset_index()
        )
        grouped["observations"] = grouped["observations"].fillna(0).astype(int)
        grouped.insert(0, "formation_date", formation_date)
        rows.extend(grouped.to_dict("records"))
    return pd.DataFrame(rows)


def build_size_turnover_double_sort(
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    size_column: str = "size_score",
    turnover_column: str = "turnover_lagged_mean_60d",
    bucket_count: int = 5,
) -> pd.DataFrame:
    """Compatibility wrapper for the historical size × turnover API."""
    result = build_double_sort(
        panel,
        daily_returns,
        formation_dates=formation_dates,
        first_column=size_column,
        second_column=turnover_column,
        bucket_count=bucket_count,
    )
    return result.rename(
        columns={
            "first_bucket": "size_bucket",
            "second_bucket": "turnover_bucket",
        }
    )


__all__ = ["build_double_sort", "build_size_turnover_double_sort"]
