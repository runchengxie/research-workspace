"""Formation-universe-aware size and low-volatility controls for microcap research."""

from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_research.style_factors.helpers import merge_sw_industry_pit

from .liquidity_signals import _standardize_signal


def build_variant_liquidity_controls(
    daily: pd.DataFrame,
    basics: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    variants: dict[float, pd.DataFrame],
    *,
    sw_membership: pd.DataFrame | None = None,
) -> dict[float, pd.DataFrame]:
    """Compute rolling controls once, then standardize inside each formation universe."""
    required_daily = {"trade_date", "symbol", "close", "amount"}
    required_basics = {"trade_date", "symbol", "total_mv"}
    missing_daily = sorted(required_daily - set(daily.columns))
    missing_basics = sorted(required_basics - set(basics.columns))
    if missing_daily:
        raise ValueError("daily is missing required columns: " + ", ".join(missing_daily))
    if missing_basics:
        raise ValueError("basics is missing required columns: " + ", ".join(missing_basics))

    prices = daily[["trade_date", "symbol", "close", "amount"]].copy()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"]).dt.normalize()
    prices = prices[prices["amount"] > 0].sort_values(["symbol", "trade_date"])
    prices["return_1d"] = prices.groupby("symbol", sort=False)["close"].pct_change()
    prices["volatility_21d"] = prices.groupby("symbol", sort=False)["return_1d"].transform(
        lambda series: series.rolling(21, min_periods=10).std().shift(1)
    )

    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    raw = prices.loc[
        prices["trade_date"].isin(dates),
        ["trade_date", "symbol", "volatility_21d"],
    ].copy()
    basic_work = basics[["trade_date", "symbol", "total_mv"]].copy()
    basic_work["trade_date"] = pd.to_datetime(basic_work["trade_date"]).dt.normalize()
    raw = raw.merge(
        basic_work,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    raw["total_mv"] = pd.to_numeric(raw["total_mv"], errors="coerce")
    raw = raw.loc[np.isfinite(raw["total_mv"]) & raw["total_mv"].gt(0)].copy()
    raw["size_raw"] = np.log(raw["total_mv"] + 1.0)
    raw["lowvol_raw"] = -raw["volatility_21d"]
    raw = merge_sw_industry_pit(raw, sw_membership)

    outputs: dict[float, pd.DataFrame] = {}
    for exclusion, variant in variants.items():
        keys = variant[["trade_date", "symbol"]].copy()
        keys["trade_date"] = pd.to_datetime(keys["trade_date"]).dt.normalize()
        if keys.duplicated(["trade_date", "symbol"]).any():
            raise ValueError("variant contains duplicate trade_date/symbol keys")
        controls = raw.merge(
            keys,
            on=["trade_date", "symbol"],
            how="inner",
            validate="one_to_one",
        )
        controls["size_score"] = _standardize_signal(
            controls["size_raw"],
            controls["trade_date"],
            controls["industry_l1"],
        )
        controls["lowvol_score"] = _standardize_signal(
            controls["lowvol_raw"],
            controls["trade_date"],
            controls["industry_l1"],
        )
        outputs[float(exclusion)] = controls[
            ["trade_date", "symbol", "industry_l1", "size_score", "lowvol_score"]
        ].copy()
    return outputs


__all__ = ["build_variant_liquidity_controls"]
