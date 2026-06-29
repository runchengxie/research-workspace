from __future__ import annotations

import numpy as np
import pandas as pd

from style_factors.factor_backtest import (
    available_factor_names,
    build_factor_returns,
    compute_summary,
    get_rebalance_dates,
)
from style_factors.factor_calc import compute_factors


def _sample_market_frames(days: int = 90, symbols: int = 60) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-01", periods=days)
    symbol_values = [f"{index:06d}.SZ" for index in range(1, symbols + 1)]
    rows = []
    basic_rows = []
    for symbol_index, symbol in enumerate(symbol_values, start=1):
        for day_index, trade_date in enumerate(dates):
            close = 10 + symbol_index * 0.1 + day_index * 0.03
            pct_chg = 0.1 + ((symbol_index + day_index) % 7) * 0.02
            rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": symbol,
                    "close": close,
                    "pct_chg": pct_chg,
                    "amount": 1000 + symbol_index * 10 + day_index,
                }
            )
            basic_rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": symbol,
                    "total_mv": 10000 + symbol_index * 100,
                    "pb": 0.8 + symbol_index / 100,
                    "pe_ttm": 8 + symbol_index / 5,
                    "turnover_rate": 0.5 + symbol_index / 200,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(basic_rows)


def test_compute_factors_without_fundamentals_skips_optional_factors() -> None:
    daily, basics = _sample_market_frames(days=50)

    factors = compute_factors(daily, basics)

    assert "factor_growth_z" not in factors.columns
    assert "factor_leverage_z" not in factors.columns
    assert {"size", "value", "momentum", "quality", "lowvol"} <= set(
        available_factor_names(factors)
    )


def test_build_factor_returns_handles_missing_optional_factors() -> None:
    daily, basics = _sample_market_frames()
    factors = compute_factors(daily, basics)
    rebalance_dates = get_rebalance_dates(pd.DatetimeIndex(sorted(factors["trade_date"].unique())))

    results = build_factor_returns(factors, daily, rebalance_dates)

    assert "size" in results
    assert "growth" not in results
    assert "leverage" not in results
    assert len(results["size"]["long_short"]) > 0


def test_compute_summary_reports_negative_drawdown() -> None:
    returns = pd.Series(
        np.array([0.02, -0.1, 0.03] * 20),
        index=pd.bdate_range("2024-01-01", periods=60),
        name="size",
    )

    summary = compute_summary({"size": {"long_short": returns}})

    assert summary.loc[0, "factor"] == "size"
    assert summary.loc[0, "max_drawdown"] < 0
