from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from style_factors.microcap_inference import (
    REGRESSORS,
    build_microcap_decomposition_panel,
    run_microcap_cross_sectional_regressions,
    summarize_cross_sectional_coefficients,
)


def test_decomposition_panel_reports_complete_case_counts() -> None:
    date = pd.Timestamp("2024-01-31")
    characteristics = pd.DataFrame(
        {
            "trade_date": [date, date],
            "symbol": ["A", "B"],
            "log_market_cap": [1.0, 2.0],
            "illiquidity_60d": [0.1, np.nan],
            "max_return_21d": [0.2, 0.3],
            "ivol_60d": [0.1, 0.2],
        }
    )
    turnover = pd.DataFrame(
        {
            "trade_date": [date, date],
            "symbol": ["A", "B"],
            "turnover_lagged_mean_60d": [1.0, 2.0],
        }
    )
    quality = pd.DataFrame(
        {
            "trade_date": [date, date],
            "symbol": ["A", "B"],
            "factor_quality": [0.5, 0.6],
        }
    )
    panel, diagnostics = build_microcap_decomposition_panel(
        characteristics,
        turnover,
        quality,
    )
    assert len(panel) == 2
    assert diagnostics.loc[0, "complete_case_rows"] == 1
    assert diagnostics.loc[0, "missing_illiquidity_60d"] == 1


def _synthetic_regression_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    rng = np.random.default_rng(21)
    formation_dates = pd.date_range("2018-01-31", periods=36, freq="ME")
    symbols = [f"S{i:03d}" for i in range(100)]
    panel_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []
    for date_index, formation in enumerate(formation_dates):
        size = rng.normal(0, 1, len(symbols))
        illiq = -0.8 * size + rng.normal(0, 0.4, len(symbols))
        controls = {
            "max_return_21d": rng.normal(0, 1, len(symbols)),
            "ivol_60d": rng.normal(0, 1, len(symbols)),
            "turnover_lagged_mean_60d": rng.normal(0, 1, len(symbols)),
            "factor_quality": rng.normal(0, 1, len(symbols)),
        }
        future = 0.04 * illiq + rng.normal(0, 0.02, len(symbols))
        for index, symbol in enumerate(symbols):
            panel_rows.append(
                {
                    "trade_date": formation,
                    "symbol": symbol,
                    "log_market_cap": size[index],
                    "illiquidity_60d": illiq[index],
                    **{name: values[index] for name, values in controls.items()},
                }
            )
        if date_index + 1 < len(formation_dates):
            next_date = formation_dates[date_index + 1]
            for index, symbol in enumerate(symbols):
                return_rows.append(
                    {
                        "trade_date": next_date,
                        "symbol": symbol,
                        "return": future[index],
                    }
                )
    returns = pd.DataFrame(return_rows).pivot(
        index="trade_date",
        columns="symbol",
        values="return",
    )
    return pd.DataFrame(panel_rows), returns, pd.DatetimeIndex(formation_dates)


def test_controls_reduce_spurious_size_coefficient() -> None:
    panel, returns, formation_dates = _synthetic_regression_inputs()
    size_only, _ = run_microcap_cross_sectional_regressions(
        panel,
        returns,
        formation_dates=formation_dates,
        regressors=("log_market_cap",),
    )
    full, _ = run_microcap_cross_sectional_regressions(
        panel,
        returns,
        formation_dates=formation_dates,
        regressors=REGRESSORS,
    )
    size_only_mean = size_only.loc[size_only["coefficient"].eq("z_log_market_cap"), "value"].mean()
    full_mean = full.loc[full["coefficient"].eq("z_log_market_cap"), "value"].mean()
    assert abs(full_mean) < abs(size_only_mean)


def test_hac_summary_matches_direct_statsmodels_calculation() -> None:
    dates = pd.date_range("2020-01-31", periods=20, freq="ME")
    values = np.linspace(-0.02, 0.03, len(dates))
    coefficients = pd.DataFrame(
        {
            "formation_date": dates,
            "coefficient": "z_log_market_cap",
            "value": values,
            "r_squared": np.linspace(0.1, 0.3, len(dates)),
        }
    )
    summary = summarize_cross_sectional_coefficients(coefficients, hac_maxlags=3)
    fit = sm.OLS(values, np.ones((len(values), 1))).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": 3},
    )
    row = summary.iloc[0]
    assert row["coefficient_mean"] == pytest.approx(values.mean())
    assert row["hac_standard_error"] == pytest.approx(float(fit.bse[0]))
    assert row["formation_count"] == len(values)
