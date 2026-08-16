from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pandas as pd
from strategy_app.research.dividend_growth_momentum import (
    dividend_growth_momentum_audit as audit,
)


def _load_script():
    path = (
        Path(__file__).resolve().parents[1]
        / "strategy-research"
        / "pre_production"
        / "dividend_growth_momentum"
        / "dividend_growth_momentum.py"
    )
    spec = importlib.util.spec_from_file_location("dividend_growth_momentum", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _price_frame(module) -> pd.DataFrame:
    rows = []
    for index, date in enumerate(pd.bdate_range("2026-01-02", periods=30)):
        for symbol, slope in (
            (module.LOW_VOL, 0.001),
            (module.DIVIDEND, 0.002),
            (module.GROWTH, 0.004),
            (module.research_config.CSI300, 0.0015),
            (module.GENERIC_DIVIDEND, 0.0018),
            (module.GENERIC_GROWTH, 0.0035),
        ):
            raw = 1.0 + index * slope
            rows.append(
                {
                    "ts_code": symbol,
                    "trade_date": date.strftime("%Y%m%d"),
                    "open": raw,
                    "close": raw,
                    "adj_factor": 2.0,
                }
            )
    return pd.DataFrame(rows)


def test_signal_uses_trailing_close_and_next_open_period() -> None:
    module = _load_script()
    prices = module.prepare_prices(_price_frame(module))
    close, _ = module.common_price_panel(prices)
    momentum = module.momentum_frame(close, 20)
    definition = next(item for item in module.STRATEGIES if item.name == "momentum20_daily")
    analysis_dates = close.loc[momentum.index[0] :].index
    signals = module.scheduled_signal_dates(analysis_dates, frequency="daily")
    positions = module.target_weights(definition, signal_dates=signals, momentum=momentum)
    periods = module.build_periods(signals, common_dates=analysis_dates)

    first_signal = momentum.index[0]
    assert (
        positions.loc[positions["rebalance_date"].eq(first_signal), "symbol"].item()
        == module.GROWTH
    )
    assert periods.iloc[0]["rebalance_date"] == first_signal
    assert periods.iloc[0]["entry_date"] == analysis_dates[1]
    assert periods.iloc[0]["exit_date"] == analysis_dates[2]


def test_core_strategy_keeps_sixty_percent_low_vol() -> None:
    module = _load_script()
    prices = module.prepare_prices(_price_frame(module))
    close, _ = module.common_price_panel(prices)
    momentum = module.momentum_frame(close, 20)
    definition = next(item for item in module.STRATEGIES if item.name == "core60_momentum20_weekly")
    dates = close.loc[momentum.index[0] :].index
    signals = module.scheduled_signal_dates(dates, frequency="weekly")
    positions = module.target_weights(definition, signal_dates=signals, momentum=momentum)
    weights = positions.pivot(index="rebalance_date", columns="symbol", values="weight").fillna(0)

    assert weights[module.LOW_VOL].eq(0.6).all()
    assert weights.sum(axis=1).eq(1.0).all()
    assert weights[module.GROWTH].eq(0.4).all()


def test_adjustment_factor_is_applied_to_open_and_close() -> None:
    module = _load_script()
    prices = module.prepare_prices(_price_frame(module))
    first = prices.iloc[0]
    assert first["adj_open"] == first["open"] * 2.0
    assert first["adj_close"] == first["close"] * 2.0


def test_generic_pair_uses_generic_symbols_without_changing_primary_signal() -> None:
    module = _load_script()
    prices = module.prepare_prices(_price_frame(module))
    close, _ = module.common_price_panel(prices)
    primary = module.momentum_frame(close, 20)
    generic = module.momentum_frame(
        close,
        20,
        pair_symbols=(module.GENERIC_DIVIDEND, module.GENERIC_GROWTH),
    )

    assert primary.iloc[0]["stronger_symbol"] == module.GROWTH
    assert generic.iloc[0]["stronger_symbol"] == module.GENERIC_GROWTH


def test_rule_provenance_marks_unimplemented_bias_and_batch_trading() -> None:
    provenance = audit.rule_provenance_frame().set_index("element")

    assert "没有实现" in provenance.loc["BIAS/加速减仓", "research_completion"]
    assert "一次性切换" in provenance.loc["换仓方式", "research_completion"]


def test_benchmark_relative_metrics_identical_stream_has_unit_beta() -> None:
    dates = pd.bdate_range("2025-01-02", periods=300)
    returns = pd.Series([0.001, -0.0005, 0.0008] * 100)
    daily = pd.concat(
        [
            pd.DataFrame({"period_end": dates, "strategy": name, "net_return": returns})
            for name in ("strategy", "benchmark")
        ],
        ignore_index=True,
    )
    relative = audit.benchmark_relative_metrics(
        daily,
        (("strategy", "benchmark", "matched_static"),),
    ).iloc[0]

    assert math.isclose(relative["beta"], 1.0, abs_tol=1e-12)
    assert math.isclose(relative["annualized_alpha_rf0"], 0.0, abs_tol=1e-12)
    assert math.isclose(relative["tracking_error"], 0.0, abs_tol=1e-12)


def test_archived_sources_include_separate_report_builder(tmp_path: Path) -> None:
    module = _load_script()

    module._archive_research_sources(tmp_path)

    assert (
        (tmp_path / "research_report.py").read_text().startswith('"""Markdown report construction')
    )
    assert (tmp_path / "research_reporting.py").is_file()


def test_cost_stress_scales_framework_fee_linearly() -> None:
    module = _load_script()
    periods = pd.DataFrame(
        {
            "rebalance_date": ["20260102"],
            "entry_date": ["20260105"],
            "exit_date": ["20260106"],
            "gross_return": [0.02],
            "net_return": [0.019],
            "fee_cost": [0.001],
            "turnover": [1.0],
        }
    )
    positions = pd.DataFrame(
        {
            "rebalance_date": [pd.Timestamp("2026-01-02")],
            "symbol": [module.DIVIDEND],
            "weight": [1.0],
            "selected_leg": [module.DIVIDEND],
        }
    )
    open_prices = pd.DataFrame(
        {module.DIVIDEND: [1.0, 1.02]},
        index=pd.to_datetime(["2026-01-05", "2026-01-06"]),
    )
    definition = next(item for item in module.STRATEGIES if item.name == "momentum20_daily")
    summary, error = module.stress_existing_result(
        definition=definition,
        base_result_periods=periods,
        base_cost_bps=10.0,
        stress_cost_bps=25.0,
        positions=positions,
        open_prices=open_prices,
    )

    assert math.isclose(summary["total_return"], 0.0175, abs_tol=1e-12)
    assert error < 1e-12
