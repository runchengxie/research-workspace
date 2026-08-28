"""Pure transformations for the Shibor regime exploration."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def build_shibor_regimes(context_pit: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Return the latest visible Shibor 3M observation and its five-row regime."""

    required = {
        "series_id",
        "period_end",
        "value",
        "available_at",
        "source_retrieved_at",
        "revision_covered",
        "reconstructed",
    }
    missing = required.difference(context_pit.columns)
    if missing:
        raise ValueError(f"context PIT missing columns: {', '.join(sorted(missing))}")
    cutoff = pd.Timestamp(as_of)
    cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff.tz_convert("UTC")
    frame = context_pit.loc[context_pit["series_id"].eq("rates.shibor_3m")].copy()
    for column in ("period_end", "available_at", "source_retrieved_at"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    frame = frame.loc[
        (frame["available_at"] <= cutoff) & (frame["source_retrieved_at"] <= cutoff)
    ].sort_values(["period_end", "available_at", "revision_covered"], kind="stable")
    frame = frame.drop_duplicates("period_end", keep="last").reset_index(drop=True)
    if frame.empty:
        return pd.DataFrame(
            columns=["period_end", "shibor_3m", "change_5d", "regime", "strict_pit"]
        )
    frame["change_5d"] = frame["value"].diff(5)
    frame["regime"] = frame["change_5d"].map(
        lambda value: "up" if value > 0 else "down" if value < 0 else "flat"
    )
    frame["strict_pit"] = frame["revision_covered"] & ~frame["reconstructed"]
    return frame.rename(columns={"value": "shibor_3m"})[
        ["period_end", "shibor_3m", "change_5d", "regime", "strict_pit"]
    ]


def build_shibor_exposure_interactions(
    stock_frame: pd.DataFrame, regimes: pd.DataFrame
) -> pd.DataFrame:
    """As-of join regimes and multiply them by available stock exposures."""

    required = {"trade_date", "symbol"}
    missing = required.difference(stock_frame.columns)
    if missing:
        raise ValueError(f"stock frame missing columns: {', '.join(sorted(missing))}")
    result = stock_frame.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], utc=True)
    context = regimes.sort_values("period_end").copy()
    result = pd.merge_asof(
        result.sort_values("trade_date"),
        context,
        left_on="trade_date",
        right_on="period_end",
        direction="backward",
    )
    result["ctx__shibor_3m__x__leverage"] = result["shibor_3m"] * result.get(
        "leverage", pd.Series(index=result.index, dtype=float)
    )
    result["ctx__shibor_3m__x__value_score"] = result["shibor_3m"] * result.get(
        "value_score", pd.Series(index=result.index, dtype=float)
    )
    return result


def build_forward_labels(prices: pd.DataFrame, horizons: Sequence[int]) -> pd.DataFrame:
    """Build forward close-to-close labels within each symbol."""

    required = {"symbol", "trade_date", "adj_close"}
    missing = required.difference(prices.columns)
    if missing:
        raise ValueError(f"prices missing columns: {', '.join(sorted(missing))}")
    result = prices.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], utc=True)
    result = result.sort_values(["symbol", "trade_date"], kind="stable")
    grouped = result.groupby("symbol", sort=False)["adj_close"]
    for horizon in horizons:
        if horizon <= 0:
            raise ValueError("label horizons must be positive")
        result[f"fwd_{horizon}d"] = grouped.shift(-horizon) / result["adj_close"] - 1.0
    return result.reset_index(drop=True)
