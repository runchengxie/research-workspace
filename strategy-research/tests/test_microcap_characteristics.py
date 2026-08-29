from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from style_factors.microcap_characteristics import build_microcap_characteristics


def test_characteristics_exclude_formation_day() -> None:
    dates = pd.bdate_range("2024-01-02", periods=61)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": np.arange(61, dtype=float),
            "amount": 1000.0,
            "total_mv": 100.0,
        }
    )
    result = build_microcap_characteristics(daily, pd.DatetimeIndex([dates[-1]]))
    assert result.loc[0, "max_return_21d"] == pytest.approx(0.59)


def test_amihud_uses_amount_cny_and_ignores_zero_amount() -> None:
    dates = pd.bdate_range("2024-01-02", periods=61)
    amount = np.full(61, 1000.0)
    amount[10] = 0.0
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": 1.0,
            "amount": amount,
            "total_mv": 100.0,
        }
    )
    result = build_microcap_characteristics(daily, pd.DatetimeIndex([dates[-1]]))
    assert np.isfinite(result.loc[0, "illiquidity_60d"])
    assert result.loc[0, "illiquidity_60d"] == pytest.approx(0.01 / 1_000_000.0)


def test_ivol_matches_ols_residual_std_on_complete_fixture() -> None:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-02", periods=61)
    market = rng.normal(0.0, 0.01, len(dates))
    epsilon = rng.normal(0.0, 0.005, len(dates))
    stock = 0.0002 + 1.3 * market + epsilon
    rows: list[dict[str, object]] = []
    for date, stock_return in zip(dates, stock, strict=True):
        rows.append(
            {
                "trade_date": date,
                "symbol": "A",
                "pct_chg": stock_return * 100.0,
                "amount": 1000.0,
                "total_mv": 100.0,
            }
        )
    daily = pd.DataFrame(rows)
    market_series = pd.Series(market, index=dates)
    result = build_microcap_characteristics(
        daily,
        pd.DatetimeIndex([dates[-1]]),
        market_return=market_series,
    )
    prior = pd.DataFrame({"r": stock[:-1], "m": market[:-1]}).tail(60)
    fit = sm.OLS(prior["r"], sm.add_constant(prior["m"])).fit()
    observed = result.loc[0, "ivol_60d"]
    assert observed == pytest.approx(fit.resid.std(ddof=1), rel=1e-6)


def test_invalid_market_cap_yields_missing_log_market_cap() -> None:
    dates = pd.bdate_range("2024-01-02", periods=61)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": 1.0,
            "amount": 1000.0,
            "total_mv": [100.0] * 60 + [0.0],
        }
    )
    result = build_microcap_characteristics(daily, pd.DatetimeIndex([dates[-1]]))
    assert np.isnan(result.loc[0, "log_market_cap"])
