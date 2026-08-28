"""PIT-aware public-fund ownership features for the shadow experiment."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def build_fund_context_features(
    frame: pd.DataFrame,
    *,
    require_available_date: bool = False,
    quantile_count: int = 5,
) -> pd.DataFrame:
    """Build bounded fund crowding/accumulation features from disclosed data.

    The input must already be restricted to rows visible on the scoring date.
    This function intentionally does not forward-fill or perform an as-of join.
    """

    required = {"symbol", "trade_date", "fund_hold_mv_to_float_mv"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"fund context frame missing columns: {', '.join(sorted(missing))}")
    if require_available_date and "available_date" not in frame.columns:
        raise ValueError("fund context frame requires available_date for PIT use")
    if require_available_date:
        available = pd.to_datetime(frame["available_date"], errors="coerce")
        trade = pd.to_datetime(frame["trade_date"], errors="coerce")
        if available.isna().any() or (available > trade).any():
            raise ValueError("fund context available_date must be present and not after trade_date")
    if quantile_count < 2:
        raise ValueError("quantile_count must be at least 2")

    result = frame.copy()
    group = ["trade_date"]
    crowd = pd.to_numeric(result["fund_hold_mv_to_float_mv"], errors="coerce")
    result["fund_crowding_level"] = crowd
    if "fund_hold_mv_to_float_mv_qoq_change" in result:
        result["fund_ownership_change"] = pd.to_numeric(
            result["fund_hold_mv_to_float_mv_qoq_change"], errors="coerce"
        )
    else:
        result["fund_ownership_change"] = float("nan")
    if "fund_count_holding_stock_qoq_change" in result:
        result["fund_holder_count_change"] = pd.to_numeric(
            result["fund_count_holding_stock_qoq_change"], errors="coerce"
        )
    else:
        result["fund_holder_count_change"] = float("nan")

    result["fund_crowding_level_q"] = _safe_ntile(crowd, result, group, quantile_count)
    result["fund_ownership_change_q"] = _safe_ntile(
        result["fund_ownership_change"], result, group, quantile_count
    )
    low = result["fund_crowding_level_q"].le(2)
    increasing = result["fund_ownership_change_q"].ge(quantile_count - 1)
    result["fund_low_crowding_accumulation"] = (low & increasing).astype(float)

    if "fund_top10_hold_mv_to_float_mv" in result:
        top10 = pd.to_numeric(result["fund_top10_hold_mv_to_float_mv"], errors="coerce")
        ratio = top10.div(crowd.where(crowd > 0))
        result["fund_top10_concentration"] = ratio.clip(lower=0.0, upper=1.0)
    else:
        result["fund_top10_concentration"] = float("nan")

    result["fund_accumulation_without_crowding"] = (
        low
        & increasing
        & result["fund_top10_concentration"].notna()
        & result["fund_top10_concentration"].le(0.8)
    ).astype(float)
    return result


def _safe_ntile(
    values: pd.Series,
    frame: pd.DataFrame,
    group: Iterable[str],
    quantile_count: int,
) -> pd.Series:
    """Return SQL-like ntile ranks while preserving nulls."""

    ranks = pd.Series(float("nan"), index=frame.index, dtype=float)
    valid = values.notna()
    if not valid.any():
        return ranks
    ranks.loc[valid] = (
        frame.loc[valid]
        .assign(_value=values.loc[valid])
        .groupby(list(group), sort=False, dropna=False)["_value"]
        .rank(method="first", pct=True)
        .mul(quantile_count)
        .clip(upper=quantile_count)
        .apply(lambda value: int(value) if pd.notna(value) else value)
    )
    return ranks
