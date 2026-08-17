from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from portfolio_backtester.style_factors_backtest import build_quantile_portfolio_returns
from style_factors.liquidity_backtest import (
    compare_baseline_returns,
    summarize_liquidity_portfolios,
)
from style_factors.liquidity_report import (
    generate_liquidity_report,
    plot_liquidity_long_only,
    plot_liquidity_quintiles,
    plot_liquidity_signal_nav,
)
from style_factors.liquidity_signals import (
    BASE_SIGNAL_LABELS,
    _aggregate_turnover_window,
    build_liquidity_control_panel,
    build_liquidity_signal_panel,
    liquidity_signal_labels,
    load_turnover_lookbacks,
)


def test_aggregate_turnover_window_applies_observation_threshold() -> None:
    frames = []
    for day in range(20):
        rows = [{"symbol": "A", "turnover_rate": float(day + 1)}]
        if day < 10:
            rows.append({"symbol": "B", "turnover_rate": 2.0})
        frames.append(pd.DataFrame(rows))

    summary = _aggregate_turnover_window(
        frames,
        window=20,
        minimum_observations=15,
    ).set_index("symbol")

    assert summary.loc["A", "mean"] == 10.5
    assert summary.loc["A", "median"] == 10.5
    assert summary.loc["A", "observations"] == 20
    assert pd.isna(summary.loc["B", "mean"])
    assert pd.isna(summary.loc["B", "median"])


def test_load_turnover_lookbacks_reads_daily_partitions_once(tmp_path: Path) -> None:
    directory = tmp_path / "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"
    dates = pd.bdate_range("2024-01-02", periods=60)
    for index, trade_date in enumerate(dates, start=1):
        partition = directory / f"trade_date={trade_date:%Y%m%d}"
        partition.mkdir(parents=True)
        pd.DataFrame(
            {
                "symbol": ["A", "B"],
                "turnover_rate": [float(index), float(index * 2)],
            }
        ).to_parquet(partition / "part.parquet", index=False)

    result, metadata = load_turnover_lookbacks(
        tmp_path,
        pd.DatetimeIndex([dates[-1]]),
    )
    row = result.set_index("symbol").loc["A"]

    assert row["turnover_1d"] == 60.0
    assert row["turnover_mean_20d"] == 50.5
    assert row["turnover_median_60d"] == 30.5
    assert row["turnover_observations_60d"] == 60
    assert metadata["formation_dates_produced"] == 1


def test_control_panel_recreates_size_and_lowvol_controls() -> None:
    dates = pd.bdate_range("2024-01-02", periods=50)
    symbols = [f"S{index:03d}" for index in range(60)]
    daily_rows = []
    for symbol_index, symbol in enumerate(symbols):
        for day_index, trade_date in enumerate(dates):
            daily_rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": symbol,
                    "close": 10 + symbol_index / 10 + np.sin(day_index / 4),
                    "amount": 1000.0,
                }
            )
    formation_date = dates[-1]
    basics = pd.DataFrame(
        {
            "trade_date": [formation_date] * len(symbols),
            "symbol": symbols,
            "total_mv": np.arange(1, len(symbols) + 1) * 1000.0,
        }
    )

    controls = build_liquidity_control_panel(
        pd.DataFrame(daily_rows),
        basics,
        pd.DatetimeIndex([formation_date]),
    )

    assert len(controls) == len(symbols)
    assert controls["size_score"].notna().all()
    assert controls["lowvol_score"].notna().all()


def test_joint_neutralization_removes_linear_size_and_lowvol_exposure() -> None:
    rng = np.random.default_rng(7)
    dates = pd.to_datetime(["2024-01-31", "2024-02-29"])
    rows = []
    turnover_rows = []
    for trade_date in dates:
        for index in range(100):
            size = (index - 50) / 20
            lowvol = np.sin(index / 9)
            noise = rng.normal(scale=0.2)
            rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": f"S{index:03d}",
                    "industry_l1": "综合",
                    "size_score": size,
                    "lowvol_score": lowvol,
                }
            )
            turnover = 5 + size + 0.8 * lowvol + noise
            turnover_rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": f"S{index:03d}",
                    **dict.fromkeys(BASE_SIGNAL_LABELS, turnover),
                }
            )

    panel, diagnostics = build_liquidity_signal_panel(
        pd.DataFrame(turnover_rows),
        pd.DataFrame(rows),
    )
    neutral = diagnostics[diagnostics["variant"] == "turnover_mean_60d_neutral"].iloc[0]

    assert "signal_turnover_mean_60d_neutral" in panel.columns
    assert abs(neutral["mean_size_correlation"]) < 1e-10
    assert abs(neutral["mean_lowvol_correlation"]) < 1e-10


def _synthetic_portfolio_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    dates = pd.bdate_range("2024-01-02", periods=90)
    formation_dates = pd.DatetimeIndex(
        pd.Series(dates).groupby(pd.Series(dates).dt.to_period("M")).max().tolist()
    )
    symbols = [f"S{index:03d}" for index in range(100)]
    daily_rows = []
    for index, symbol in enumerate(symbols):
        daily_return = -0.1 + index / 500
        for trade_date in dates:
            daily_rows.append({"trade_date": trade_date, "symbol": symbol, "pct_chg": daily_return})
    signal_rows = [
        {"trade_date": trade_date, "symbol": symbol, "signal": float(index)}
        for trade_date in formation_dates
        for index, symbol in enumerate(symbols)
    ]
    return pd.DataFrame(signal_rows), pd.DataFrame(daily_rows), formation_dates


def test_quantile_backtest_and_summary_separate_long_and_spread_returns() -> None:
    signals, daily, formation_dates = _synthetic_portfolio_inputs()
    portfolios = build_quantile_portfolio_returns(
        signals,
        daily,
        formation_dates,
        {"turnover_1d": "signal"},
    )
    signal_diagnostics = pd.DataFrame(
        [
            {
                "variant": "turnover_1d",
                "neutralized": False,
                "formation_observations": len(signals),
                "formation_coverage": 1.0,
                "mean_size_correlation": 0.2,
                "mean_lowvol_correlation": 0.3,
            }
        ]
    )

    summary, quintiles = summarize_liquidity_portfolios(portfolios, signal_diagnostics)
    row = summary.iloc[0]

    assert portfolios["turnover_1d"]["long"].mean() > portfolios["turnover_1d"]["short"].mean()
    assert abs(row["monotonicity_spearman"] - 1.0) < 1e-12
    assert row["improving_quintile_steps"] == 4
    assert row["long_annual_return"] > row["high_turnover_annual_return"]
    assert row["long_short_annual_return"] > 0
    assert len(quintiles) == 5


def test_baseline_tieout_detects_exact_and_drifted_returns(tmp_path: Path) -> None:
    dates = pd.bdate_range("2024-01-02", periods=5)
    observed = pd.Series([0.01, -0.01, 0.02, 0.0, 0.01], index=dates)
    observed.to_csv(tmp_path / "factor_liquidity_daily.csv", header=["liquidity"])

    exact = compare_baseline_returns(observed, tmp_path)
    drifted = compare_baseline_returns(observed + 0.001, tmp_path)

    assert exact["passed"]
    assert exact["maximum_absolute_difference"] == 0
    assert not drifted["passed"]


def test_liquidity_report_and_charts_are_generated(tmp_path: Path) -> None:
    labels = liquidity_signal_labels()
    dates = pd.bdate_range("2024-01-02", periods=40)
    summary_rows = []
    portfolios = {}
    for index, variant in enumerate(labels):
        annual_returns = [float(value + index) for value in range(1, 6)]
        summary_rows.append(
            {
                "variant": variant,
                "neutralized": variant.endswith("_neutral"),
                "long_short_annual_return": 4.0 + index,
                "long_short_sharpe": 1.0 + index / 10,
                "long_short_max_drawdown": -5.0 - index,
                "long_short_positive_year_ratio": 0.8,
                "long_annual_return": 8.0 + index,
                "long_excess_annual_return": 2.0 + index,
                "monotonicity_spearman": 1.0,
                "improving_quintile_steps": 4,
                "mean_size_correlation": 0.0,
                "mean_lowvol_correlation": 0.0,
                "baseline_return_correlation": 0.9,
                **{
                    f"q{quantile}_annual_return": annual_returns[quantile - 1]
                    for quantile in range(1, 6)
                },
            }
        )
        returns = pd.Series(0.0001 * (index + 1), index=dates)
        portfolios[variant] = {"long_short": returns}
    summary = pd.DataFrame(summary_rows)
    metadata = {
        "data_start": "2024-01-02",
        "data_end": "2024-02-26",
        "formation_dates": 2,
        "generated_at": "2026-08-03T00:00:00+00:00",
        "baseline_tieout": {"performed": False},
    }

    report = generate_liquidity_report(summary, metadata, tmp_path)
    plot_liquidity_signal_nav(portfolios, tmp_path)
    plot_liquidity_quintiles(summary, tmp_path)
    plot_liquidity_long_only(summary, tmp_path)

    assert "五组收益" in report
    assert "低换手多头年化收益" in report
    assert (tmp_path / "liquidity_factor_diagnostics.md").is_file()
    assert (tmp_path / "liquidity_signal_nav.png").is_file()
    assert (tmp_path / "liquidity_quintile_returns.png").is_file()
    assert (tmp_path / "liquidity_long_only.png").is_file()
