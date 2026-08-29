from __future__ import annotations

import pandas as pd

from experiments.macro_context_shadow.run_m0_portfolio_backtest import (
    _hac_mean_t,
    summarize_portfolio,
)


def test_summarize_portfolio_applies_turnover_cost() -> None:
    daily = pd.DataFrame({"gross_return": [0.01, 0.0], "turnover": [0.5, 0.0]})
    result = summarize_portfolio(daily, turnover_bps=30.0)
    assert result["days"] == 2
    assert result["mean_daily_turnover"] == 0.25
    assert result["net_ann"] < result["gross_ann"]


def test_hac_mean_t_is_negative_for_negative_active_returns() -> None:
    assert _hac_mean_t([-0.01, -0.02, -0.01, -0.03], lags=2) < 0.0
