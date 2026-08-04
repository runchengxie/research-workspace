from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes

from src.style_factors import FACTOR_LABELS
from src.style_factors.attribution import run_strategy_attribution, run_yearly_strategy_attribution
from src.style_factors.charts import (
    _yearly_return_matrix,
    plot_cumulative_comparison,
    plot_yearly_barchart,
)
from src.style_factors.data import _group_partition_dates_by_month
from src.style_factors.factor_backtest import (
    _buy_and_hold_leg_returns,
    available_factor_names,
    build_factor_returns,
    compute_summary,
    compute_yearly_breakdown,
    get_rebalance_dates,
)
from src.style_factors.factor_calc import (
    EARNINGS_STABILITY_COL,
    _prepare_fundamentals,
    _winsorize,
    compute_factors,
)
from src.style_factors.helpers._aux import _merge_aux
from src.style_factors.report import (
    _append_attribution_section,
    _append_yearly_section,
    _factor_definition_lines,
    _summary_for_report,
)
from src.style_factors.yearly_chart import render_yearly_chart


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
    # Quality depends on fundamentals; without fina it is skipped.
    assert "factor_quality_z" not in factors.columns
    # Earnings yield (value group) is always available from valuation.
    assert "earnings_yield" in available_factor_names(factors)
    assert {"size", "value", "momentum", "earnings_yield", "lowvol"} <= set(
        available_factor_names(factors)
    )


def test_quality_is_composite_and_earnings_yield_is_value() -> None:
    definitions = "\n".join(_factor_definition_lines())

    # Quality is now a composite operating-quality score, not earnings yield.
    assert FACTOR_LABELS["quality"] == "质量因子"
    assert "盈利稳定性" in definitions
    assert "估值代理，非盈利质量" not in definitions
    # Earnings yield lives in the value group.
    assert FACTOR_LABELS["earnings_yield"] == "盈利收益率因子"
    assert "市盈率倒数" in definitions
    assert "LimitUp" not in definitions


def test_report_summary_uses_chinese_factor_names_and_headings() -> None:
    summary = pd.DataFrame(
        [
            {
                "factor": "value",
                "days": 252,
                "years": 1.0,
                "cumulative_ret": 10.0,
                "geometric_annual_ret": 10.0,
                "annual_vol": 8.0,
                "sharpe": 1.2,
                "max_drawdown": -5.0,
                "hit_rate": 51.0,
            }
        ]
    )

    display = _summary_for_report(summary)

    assert display.loc[0, "因子"] == "价值因子"
    assert "几何年化收益（%）" in display.columns
    assert "factor" not in display.columns


def test_compute_factors_uses_factor_specific_valuation_eligibility() -> None:
    daily, basics = _sample_market_frames(days=50)
    basics.loc[basics["symbol"] == "000001.SZ", "pb"] = -1.0
    basics.loc[basics["symbol"] == "000002.SZ", "pe_ttm"] = -5.0

    factors = compute_factors(daily, basics)

    pb_row = factors[factors["symbol"] == "000001.SZ"]
    pe_row = factors[factors["symbol"] == "000002.SZ"]
    assert not pb_row.empty and not pe_row.empty
    assert pb_row["factor_value_z"].isna().all()
    assert pe_row["factor_earnings_yield_z"].isna().all()
    assert pb_row["factor_size_z"].notna().any()
    assert pe_row["factor_momentum_z"].notna().any()


def test_prepare_fundamentals_computes_stability_on_report_rows() -> None:
    rows = []
    quarter_ends = pd.date_range("2022-03-31", periods=8, freq="QE")
    for quarter, end_date in enumerate(quarter_ends):
        rows.append(
            {
                "symbol": "000001",
                "end_date": end_date,
                "ann_date": end_date + pd.Timedelta(days=30),
                "roe": 10.0,
                "netprofit_yoy": float(quarter),
            }
        )

    prepared = _prepare_fundamentals(pd.DataFrame(rows))

    assert prepared[EARNINGS_STABILITY_COL].iloc[:3].isna().all()
    assert prepared[EARNINGS_STABILITY_COL].iloc[3:].notna().all()


def test_winsorize_is_cross_sectional_by_trade_date() -> None:
    dates = pd.Series([pd.Timestamp("2024-01-02")] * 3 + [pd.Timestamp("2024-01-03")] * 3)
    values = pd.Series([1.0, 2.0, 1000.0, 10.0, 20.0, 30.0])

    winsorized = _winsorize(values, dates)

    assert winsorized.iloc[2] > winsorized.iloc[5]
    assert winsorized.iloc[2] < 1000.0


def test_missing_industry_is_neutralized_as_residual_group() -> None:
    daily, basics = _sample_market_frames(days=50)
    membership = pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "in_date": [pd.Timestamp("2020-01-01")],
            "out_date": [pd.NaT],
            "industry_l1": ["银行"],
        }
    )

    factors = compute_factors(daily, basics, sw_membership=membership)

    residual = factors[factors["symbol"] == "000002.SZ"]
    assert residual["industry_l1"].isna().all()
    assert residual["factor_size_z"].notna().all()


def test_daily_auxiliary_values_are_not_forward_filled() -> None:
    panel = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ"],
            "trade_date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        }
    )
    auxiliary = pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "trade_date": pd.to_datetime(["2024-01-02"]),
            "event": [1.0],
        }
    )

    merged = _merge_aux(panel, auxiliary, ["event"])

    assert merged.loc[0, "event"] == 1.0
    assert pd.isna(merged.loc[1, "event"])


def test_partition_month_grouping_selects_latest_trade_date() -> None:
    dated_parts = [
        (pd.Timestamp("2024-01-30"), Path("trade_date=20240130")),
        (pd.Timestamp("2024-01-31"), Path("trade_date=20240131")),
        (pd.Timestamp("2024-02-29"), Path("trade_date=20240229")),
    ]

    grouped = _group_partition_dates_by_month(dated_parts)

    assert {max(group) for group in grouped.values()} == {
        pd.Timestamp("2024-01-31"),
        pd.Timestamp("2024-02-29"),
    }


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
    assert "geometric_annual_ret" in summary.columns


def test_buy_and_hold_leg_does_not_restore_equal_weights_daily() -> None:
    returns = pd.DataFrame(
        {"A": [1.0, 0.0], "B": [0.0, 1.0]},
        index=pd.bdate_range("2024-01-01", periods=2),
    )

    result = _buy_and_hold_leg_returns(returns, ["A", "B"])

    assert result.iloc[0] == 0.5
    assert abs(result.iloc[1] - (1 / 3)) < 1e-12


def test_yearly_breakdown_marks_partial_years() -> None:
    dates = pd.bdate_range("2024-03-01", periods=100)
    returns = pd.Series(0.001, index=dates, name="size")

    yearly = compute_yearly_breakdown({"size": {"long_short": returns}})

    assert bool(yearly.loc[0, "is_partial_year"])
    assert yearly.loc[0, "period_start"] == "2024-03-01"


def test_yearly_report_formats_missing_returns_as_dash() -> None:
    yearly = pd.DataFrame(
        {
            "year": [2024, 2024],
            "factor": ["size", "value"],
            "period_return": [1.25, np.nan],
        }
    )
    lines: list[str] = []

    _append_yearly_section(lines, yearly)

    report = "\n".join(lines)
    assert "+1.2" in report
    assert "—" in report
    assert "nan" not in report.lower()
    assert "| 年份 | 市值因子 | 价值因子 |" in report
    assert "| year | size | value |" not in report


def test_attribution_report_uses_chinese_yearly_headings() -> None:
    summary = pd.DataFrame([{"factor": "value", "annual_ret": 10.0}])
    attribution = {
        "strategy": "示例策略",
        "days": 252,
        "years": 1.0,
        "geometric_annual_return": 8.0,
        "r_squared": 0.4,
        "annual_alpha": 3.0,
        "betas": {"value": 0.5},
    }
    yearly = pd.DataFrame(
        [
            {
                "year": 2024,
                "days": 252,
                "period_return": 8.0,
                "geometric_annual_return": 8.0,
                "r_squared": 0.4,
                "annual_alpha": 3.0,
            }
        ]
    )
    lines: list[str] = []

    _append_attribution_section(lines, summary, attribution, yearly)

    report = "\n".join(lines)
    assert "| 年份 | 观察日 | 期间收益（%） |" in report
    assert "| year | days | period_return |" not in report


def test_yearly_return_matrix_uses_stable_factor_order_and_keeps_missing_values() -> None:
    yearly = pd.DataFrame(
        {
            "year": [2024, 2024, 2025],
            "factor": ["value", "size", "value"],
            "period_return": [2.5, -1.0, 3.0],
        }
    )

    matrix = _yearly_return_matrix(yearly)

    assert list(matrix.index) == ["size", "value"]
    assert list(matrix.columns) == [2024, 2025]
    assert matrix.loc["size", 2024] == -1.0
    assert pd.isna(matrix.loc["size", 2025])


def test_comparison_uses_log_nav_scale(monkeypatch, tmp_path: Path) -> None:
    dates = pd.bdate_range("2024-01-01", periods=40)
    returns = pd.Series(0.001, index=dates, name="value")
    observed_scales: list[str] = []
    original = Axes.set_yscale

    def record_scale(axis, value, *args, **kwargs):
        observed_scales.append(value)
        return original(axis, value, *args, **kwargs)

    monkeypatch.setattr("matplotlib.axes.Axes.set_yscale", record_scale)
    plot_cumulative_comparison({"value": {"long_short": returns}}, tmp_path)

    assert "log" in observed_scales
    assert (tmp_path / "style_factor_comparison.png").is_file()


def test_yearly_heatmap_chart_is_generated(tmp_path: Path) -> None:
    yearly = pd.DataFrame(
        {
            "year": [2024, 2024, 2025],
            "factor": ["size", "value", "value"],
            "period_return": [-5.0, 8.0, 3.0],
            "is_partial_year": [False, False, True],
        }
    )

    artifacts = plot_yearly_barchart(yearly, tmp_path)

    assert artifacts is not None
    assert (tmp_path / "style_factor_yearly.png").is_file()
    assert (tmp_path / "style_factor_yearly.svg").is_file()
    matrix = pd.read_csv(tmp_path / "style_factor_yearly_matrix.csv")
    assert list(matrix["factor"]) == ["size", "value"]
    metadata = json.loads((tmp_path / "style_factor_yearly.meta.json").read_text())
    assert metadata["schema_version"] == "research.style-factor-yearly-chart.v1"
    assert metadata["partial_years"] == [2025]
    assert metadata["missing_cells"] == 1


def test_yearly_chart_can_be_rendered_from_sealed_csv(tmp_path: Path) -> None:
    input_path = tmp_path / "factor_yearly.csv"
    pd.DataFrame(
        {
            "year": [2025, 2026],
            "factor": ["value", "value"],
            "annual_ret": [4.0, 2.0],
        }
    ).to_csv(input_path, index=False)

    artifacts = render_yearly_chart(input_path, tmp_path / "rendered")

    assert artifacts.png.is_file()
    assert artifacts.svg.is_file()


def test_yearly_chart_rejects_duplicate_factor_years(tmp_path: Path) -> None:
    yearly = pd.DataFrame(
        {
            "year": [2026, 2026],
            "factor": ["value", "value"],
            "period_return": [1.0, 2.0],
        }
    )

    with pytest.raises(ValueError, match="重复"):
        plot_yearly_barchart(yearly, tmp_path)


def test_strategy_attribution_reports_yearly_betas_and_json_safe_summary() -> None:
    dates = pd.bdate_range("2024-01-01", "2025-12-31")
    size = pd.Series(np.sin(np.arange(len(dates)) / 17) / 100, index=dates, name="size")
    value = pd.Series(np.cos(np.arange(len(dates)) / 23) / 100, index=dates, name="value")
    strategy = 0.5 * size + 0.2 * value + 0.0001
    factor_results = {
        "size": {"long_short": size},
        "value": {"long_short": value},
    }

    attribution = run_strategy_attribution(factor_results, strategy, "demo")
    yearly = run_yearly_strategy_attribution(factor_results, strategy, "demo")

    json.dumps(attribution)
    assert attribution["strategy"] == "demo"
    assert abs(attribution["betas"]["size"] - 0.5) < 1e-6
    assert "geometric_annual_return" in attribution
    assert attribution["annual_alpha"] > 0
    assert list(yearly["year"]) == [2024, 2025]
    assert abs(yearly.loc[0, "beta_size"] - 0.5) < 1e-6
    assert "contribution_value" in yearly.columns
