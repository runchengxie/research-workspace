"""Formation-date size × turnover double-sort diagnostics."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


def _bucket(values: pd.Series, bucket_count: int) -> pd.Series:
    rank = values.rank(method="first", ascending=True)
    return np.ceil(rank * bucket_count / len(values)).astype(int)


def build_size_turnover_double_sort(
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    size_column: str = "size_score",
    turnover_column: str = "turnover_lagged_mean_60d",
    bucket_count: int = 5,
    sort_method: Literal["independent", "sequential"] = "independent",
) -> pd.DataFrame:
    """Return long-form forward returns for size × turnover buckets.

    Bucket 1 is the smallest/lowest-turnover side of each raw input column.
    Forward returns begin strictly after the formation date and end at the
    next formation date, preventing the formation observation from leaking.
    """
    required = {"trade_date", "symbol", size_column, turnover_column}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError("panel is missing required columns: " + ", ".join(missing))
    if bucket_count < 2:
        raise ValueError("bucket_count must be at least 2")
    if sort_method not in {"independent", "sequential"}:
        raise ValueError("sort_method must be 'independent' or 'sequential'")
    dates = pd.DatetimeIndex(formation_dates).normalize()  # ty: ignore[unresolved-attribute]
    dates = dates.sort_values().unique()
    if dates.empty:
        return pd.DataFrame(
            columns=pd.Index(
                [
                    "formation_date",
                    "size_bucket",
                    "turnover_bucket",
                    "observations",
                    "forward_return",
                ]
            )
        )
    returns = daily_returns.copy()
    returns.index = pd.DatetimeIndex(returns.index).normalize()  # ty: ignore[unresolved-attribute]
    rows: list[dict[str, object]] = []
    for index, formation_date in enumerate(dates):
        next_date = dates[index + 1] if index + 1 < len(dates) else returns.index.max()
        cross = panel.loc[
            pd.to_datetime(panel["trade_date"]).dt.normalize().eq(formation_date),
            ["symbol", size_column, turnover_column],
        ].copy()
        cross[size_column] = pd.to_numeric(cross[size_column], errors="coerce")
        cross[turnover_column] = pd.to_numeric(cross[turnover_column], errors="coerce")
        cross = cross.dropna(subset=["symbol", size_column, turnover_column]).drop_duplicates(
            "symbol"
        )
        if cross.empty:
            continue
        cross["size_bucket"] = _bucket(cross[size_column], bucket_count)
        if sort_method == "independent":
            cross["turnover_bucket"] = _bucket(cross[turnover_column], bucket_count)
        else:
            cross["turnover_bucket"] = cross.groupby("size_bucket", sort=False)[
                turnover_column
            ].transform(lambda values: _bucket(values, bucket_count))
        window = returns.loc[(returns.index > formation_date) & (returns.index <= next_date)]
        forward = (1.0 + window).prod(axis=0, min_count=1) - 1.0
        cross["forward_return"] = cross["symbol"].map(forward)
        grouped = cross.groupby(["size_bucket", "turnover_bucket"], as_index=False).agg(
            observations=("forward_return", "count"),
            forward_return=("forward_return", "mean"),
        )
        grid = pd.MultiIndex.from_product(
            [range(1, bucket_count + 1), range(1, bucket_count + 1)],
            names=["size_bucket", "turnover_bucket"],
        )
        grouped = grouped.set_index(["size_bucket", "turnover_bucket"]).reindex(grid).reset_index()
        grouped["observations"] = grouped["observations"].fillna(0).astype(int)
        grouped.insert(0, "formation_date", formation_date)
        rows.extend(grouped.to_dict("records"))
    return pd.DataFrame(rows)


__all__ = ["build_size_turnover_double_sort"]
