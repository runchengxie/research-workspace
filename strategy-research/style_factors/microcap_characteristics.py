"""PIT-safe rolling characteristics for A-share microcap decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd

CHARACTERISTIC_COLUMNS = (
    "log_market_cap",
    "illiquidity_60d",
    "max_return_21d",
    "ivol_60d",
)


def _require_columns(frame: pd.DataFrame, columns: set[str], *, label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def _long_from_matrix(
    matrix: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    *,
    value_name: str,
) -> pd.DataFrame:
    requested = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    selected = matrix.loc[matrix.index.isin(requested)]
    return (
        selected.rename_axis(index="trade_date", columns="symbol")
        .reset_index()
        .melt(id_vars="trade_date", var_name="symbol", value_name=value_name)
    )


def build_microcap_characteristics(
    daily_clean: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    *,
    market_return: pd.Series | None = None,
) -> pd.DataFrame:
    """Build lagged ILLIQ, MAX, IVOL, and log market cap at formation dates.

    ILLIQ uses the previous 60 market sessions with at least 45 valid stock
    observations. MAX uses the previous 21 sessions with at least 15 valid
    observations. IVOL uses a 60-session rolling single-market-factor residual
    variance with at least 40 valid stock observations. Every rolling input is
    shifted one market session, so the formation observation is excluded.
    """
    required = {"trade_date", "symbol", "pct_chg", "amount", "total_mv"}
    _require_columns(daily_clean, required, label="daily_clean")
    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    if dates.empty:
        raise ValueError("formation_dates is empty")

    frame = daily_clean[["trade_date", "symbol", "pct_chg", "amount", "total_mv"]].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str)
    if frame.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("daily_clean contains duplicate trade_date/symbol keys")

    calendar = pd.DatetimeIndex(sorted(frame["trade_date"].unique()))
    returns = (
        frame.pivot(index="trade_date", columns="symbol", values="pct_chg")
        .reindex(calendar)
        .apply(pd.to_numeric, errors="coerce")
        / 100.0
    )
    amount_cny = (
        frame.pivot(index="trade_date", columns="symbol", values="amount")
        .reindex(calendar)
        .apply(pd.to_numeric, errors="coerce")
        * 1_000.0
    )

    valid_amount = amount_cny.where(amount_cny > 0)
    daily_illiquidity = returns.abs() / valid_amount
    illiquidity = daily_illiquidity.shift(1).rolling(60, min_periods=45).mean()
    max_return = returns.shift(1).rolling(21, min_periods=15).max()

    if market_return is None:
        broad_market = returns.mean(axis=1)
    else:
        broad_market = pd.to_numeric(market_return, errors="coerce")
        broad_market.index = pd.to_datetime(broad_market.index).normalize()
        broad_market = broad_market.reindex(calendar)

    lagged_returns = returns.shift(1)
    lagged_market = broad_market.shift(1)
    stock_var = lagged_returns.rolling(60, min_periods=40).var()
    covariance = lagged_returns.rolling(60, min_periods=40).cov(lagged_market)
    market_var = lagged_market.rolling(60, min_periods=40).var()
    # ``market_var`` is indexed by formation date, so the division must be
    # row-wise.  The default DataFrame alignment is column-wise and silently
    # produces NaNs when the stock symbols do not match the date labels.
    residual_var = stock_var.sub(
        covariance.pow(2).div(market_var, axis=0),
        axis=0,
    ).clip(lower=0)
    ivol = np.sqrt(residual_var)

    result = _long_from_matrix(
        illiquidity,
        dates,
        value_name="illiquidity_60d",
    )
    result = result.merge(
        _long_from_matrix(max_return, dates, value_name="max_return_21d"),
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    result = result.merge(
        _long_from_matrix(ivol, dates, value_name="ivol_60d"),
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )

    caps = frame.loc[
        frame["trade_date"].isin(dates),
        ["trade_date", "symbol", "total_mv"],
    ].copy()
    caps["total_mv"] = pd.to_numeric(caps["total_mv"], errors="coerce")
    result = result.merge(
        caps,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    valid_cap = result["total_mv"].where(
        np.isfinite(result["total_mv"].to_numpy(dtype=float)) & result["total_mv"].gt(0)
    )
    result["log_market_cap"] = np.log(valid_cap)
    return (
        result.drop(columns="total_mv").sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    )


__all__ = ["CHARACTERISTIC_COLUMNS", "build_microcap_characteristics"]
