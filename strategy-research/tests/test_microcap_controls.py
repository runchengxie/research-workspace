from __future__ import annotations

import numpy as np
import pandas as pd

from style_factors.microcap_robustness import build_variant_liquidity_controls


def test_liquidity_controls_filter_before_cross_sectional_standardization() -> None:
    dates = pd.bdate_range("2023-11-01", periods=70)
    formation = dates[-1]
    symbols = [f"S{i:03d}" for i in range(100)]
    daily_rows: list[dict[str, object]] = []
    basic_rows: list[dict[str, object]] = []
    for symbol_index, symbol in enumerate(symbols):
        for day_index, date in enumerate(dates):
            daily_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "close": 10.0 + symbol_index * 0.02 + day_index * 0.01,
                    "amount": 1000.0,
                }
            )
            basic_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "total_mv": float(np.exp(symbol_index / 8)),
                }
            )
    daily = pd.DataFrame(daily_rows)
    basics = pd.DataFrame(basic_rows)
    keep = symbols[30:]
    variants = {
        0.0: pd.DataFrame({"trade_date": formation, "symbol": symbols}),
        0.3: pd.DataFrame({"trade_date": formation, "symbol": keep}),
    }

    controls = build_variant_liquidity_controls(
        daily,
        basics,
        pd.DatetimeIndex([formation]),
        variants,
    )
    full = controls[0.0]
    filtered = controls[0.3]

    assert set(filtered["symbol"]) == set(keep)
    assert abs(filtered["size_score"].mean()) < 1e-10
    inherited = full.loc[full["symbol"].isin(keep)].set_index("symbol")["size_score"]
    direct = filtered.set_index("symbol")["size_score"]
    assert not inherited.equals(direct)
