from __future__ import annotations

from importlib import import_module

import numpy as np
import pandas as pd
from pytest import approx


def _turnover_anatomy():
    return import_module("style_factors.turnover_anatomy")


def test_proxy_controls_exclude_formation_day_inputs() -> None:
    module = _turnover_anatomy()
    dates = pd.bdate_range("2023-07-03", periods=130)
    symbols = ["AAA", "BBB"]
    rows: list[dict[str, object]] = []
    for symbol_index, symbol in enumerate(symbols):
        for day_index, trade_date in enumerate(dates):
            rows.append(
                {
                    "trade_date": trade_date,
                    "symbol": symbol,
                    "tr_close": 10.0 + symbol_index + day_index * 0.01,
                    "amount": 1_000.0 + symbol_index * 100.0 + day_index,
                }
            )
    daily = pd.DataFrame(rows)
    shocked = daily.copy()
    mask = shocked["trade_date"].eq(dates[-1])
    shocked.loc[mask, "tr_close"] = 1_000_000.0
    shocked.loc[mask, "amount"] = 1_000_000_000.0

    baseline = (
        module.build_turnover_proxy_controls(
            daily,
            pd.DatetimeIndex([dates[-1]]),
        )
        .sort_values("symbol")
        .reset_index(drop=True)
    )
    formation_shocked = (
        module.build_turnover_proxy_controls(
            shocked,
            pd.DatetimeIndex([dates[-1]]),
        )
        .sort_values("symbol")
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(baseline, formation_shocked)


def test_deconfounding_ladder_orthogonalizes_each_declared_control_stage() -> None:
    module = _turnover_anatomy()
    rng = np.random.default_rng(7)
    date = pd.Timestamp("2023-12-29")
    symbols = [f"S{index:02d}" for index in range(60)]
    signal_panel = pd.DataFrame(
        {
            "trade_date": date,
            "symbol": symbols,
            "industry_l1": "A",
            "size_score": rng.normal(size=len(symbols)),
            "lowvol_score": rng.normal(size=len(symbols)),
            "signal_low_turnover": rng.normal(size=len(symbols)),
        }
    )
    proxy_controls = pd.DataFrame(
        {
            "trade_date": date,
            "symbol": symbols,
            "activity_20d_raw": rng.normal(size=len(symbols)),
            "illiquidity_20d_raw": rng.normal(size=len(symbols)),
            "momentum_126_21d_raw": rng.normal(size=len(symbols)),
            "reversal_21d_raw": rng.normal(size=len(symbols)),
        }
    )

    ladder, diagnostics = module.build_turnover_deconfounding_ladder(
        signal_panel,
        proxy_controls,
        minimum_sample=30,
    )

    final_stage = diagnostics.set_index("stage").loc["size_lowvol_liquidity_returns"]
    assert final_stage["non_null_observations"] == len(symbols)
    assert final_stage["max_abs_control_correlation"] < 1e-10
    final_signal = final_stage["signal_column"]
    for control in module.TURNOVER_DECONFOUNDING_CONTROLS["size_lowvol_liquidity_returns"]:
        assert abs(ladder[final_signal].corr(ladder[control])) < 1e-10


def test_turnover_anatomy_respects_missing_formation_dates_as_forward_boundaries() -> None:
    module = _turnover_anatomy()
    first = pd.Timestamp("2024-01-31")
    missing_middle = pd.Timestamp("2024-02-29")
    last = pd.Timestamp("2024-03-29")
    symbols = [f"S{index:02d}" for index in range(20)]
    panel = pd.DataFrame(
        {
            "trade_date": first,
            "symbol": symbols,
            "signal_low_turnover": np.arange(len(symbols), dtype=float),
        }
    )
    february = pd.bdate_range("2024-02-01", "2024-02-29")
    march = pd.bdate_range("2024-03-01", "2024-03-29")
    returns = pd.DataFrame(
        0.0,
        index=february.append(march),
        columns=pd.Index(symbols),
    )
    returns.loc[february, symbols[-4:]] = 0.01
    returns.loc[march, symbols[-4:]] = -0.05

    anatomy = module.summarize_turnover_anatomy(
        panel,
        returns,
        formation_dates=pd.DatetimeIndex([first]),
        calendar_dates=pd.DatetimeIndex([first, missing_middle, last]),
        stage_columns={"raw": "signal_low_turnover"},
        sample_label="development",
        bucket_count=5,
    )

    assert anatomy.iloc[0]["low_turnover_leg_return"] > 0


def test_turnover_anatomy_separates_low_turnover_leg_from_high_turnover_avoidance() -> None:
    module = _turnover_anatomy()
    formation = pd.Timestamp("2023-12-29")
    symbols = [f"S{index:02d}" for index in range(20)]
    signal = np.arange(len(symbols), dtype=float)
    panel = pd.DataFrame(
        {
            "trade_date": formation,
            "symbol": symbols,
            "signal_low_turnover": signal,
        }
    )
    forward = np.zeros(len(symbols), dtype=float)
    forward[:4] = -0.10
    forward[-4:] = 0.10
    returns = pd.DataFrame(
        [forward],
        index=pd.date_range("2024-01-02", periods=1),
        columns=pd.Index(symbols),
    )

    anatomy = module.summarize_turnover_anatomy(
        panel,
        returns,
        formation_dates=pd.DatetimeIndex([formation]),
        stage_columns={"raw": "signal_low_turnover"},
        sample_label="development",
        bucket_count=5,
    )

    row = anatomy.iloc[0]
    assert row["sample"] == "development"
    assert row["stage"] == "raw"
    assert row["low_turnover_leg_return"] == approx(0.10)
    assert row["high_turnover_leg_return"] == approx(-0.10)
    assert row["low_minus_high_return"] == approx(0.20)
    assert row["mean_rank_ic"] > 0
