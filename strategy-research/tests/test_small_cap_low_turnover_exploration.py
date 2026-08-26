from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.style_factors.small_cap_low_turnover_exploration_20260826 import (
    _signal_correlations,
)
from style_factors.small_cap_low_turnover import (
    build_buffered_targets,
    build_candidate_signal_panel,
    build_lagged_turnover_panel,
    filter_candidate_eligibility,
    map_targets_to_execution_dates,
)


def _synthetic_signal_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    date = pd.Timestamp("2024-01-31")
    symbols = [f"S{index:02d}" for index in range(40)]
    controls = pd.DataFrame(
        {
            "trade_date": date,
            "symbol": symbols,
            "industry_l1": ["A"] * 20 + ["B"] * 20,
            "size_score": np.linspace(-2.0, 2.0, len(symbols)),
            "lowvol_score": np.sin(np.arange(len(symbols)) / 4),
        }
    )
    turnover = pd.DataFrame(
        {
            "trade_date": date,
            "symbol": symbols,
            "turnover_lagged_mean_60d": np.linspace(4.0, 1.0, len(symbols)),
        }
    )
    return controls, turnover


def test_candidate_signal_panel_has_small_cap_and_turnover_variants() -> None:
    controls, turnover = _synthetic_signal_inputs()

    panel = build_candidate_signal_panel(
        controls,
        turnover,
        minimum_sample=30,
    )

    expected = {
        "signal_small_cap",
        "signal_low_turnover",
        "signal_low_turnover_residual",
        "signal_composite",
        "signal_composite_residual",
    }
    assert expected <= set(panel.columns)
    by_industry = panel.groupby("industry_l1")
    assert (
        by_industry.apply(
            lambda group: group["signal_small_cap"].corr(group["size_score"]),
            include_groups=False,
        )
        .lt(-0.99)
        .all()
    )
    assert (
        by_industry.apply(
            lambda group: group["signal_low_turnover"].corr(group["turnover_lagged_mean_60d"]),
            include_groups=False,
        )
        .lt(-0.99)
        .all()
    )
    assert panel["signal_low_turnover_residual"].notna().all()
    assert panel["signal_composite"].notna().all()


def test_residual_low_turnover_removes_size_and_lowvol_exposure() -> None:
    controls, turnover = _synthetic_signal_inputs()
    turnover["turnover_lagged_mean_60d"] = (
        4.0 + controls["size_score"] + 0.7 * controls["lowvol_score"]
    )

    panel = build_candidate_signal_panel(
        controls,
        turnover,
        minimum_sample=30,
    )

    residual = panel["signal_low_turnover_residual"]
    assert abs(residual.corr(panel["size_score"])) < 1e-10
    assert abs(residual.corr(panel["lowvol_score"])) < 1e-10


def test_buffer_keeps_existing_names_until_exit_rank() -> None:
    dates = pd.DatetimeIndex(["2024-01-31", "2024-02-29"])
    symbols = [f"S{index:02d}" for index in range(6)]
    rows = []
    for trade_date in dates:
        scores = [6, 5, 4, 3, 2, 1] if trade_date == dates[0] else [6, 5, 1, 4, 3, 2]
        rows.extend(
            {
                "trade_date": trade_date,
                "symbol": symbol,
                "signal": score,
            }
            for symbol, score in zip(symbols, scores, strict=True)
        )
    panel = pd.DataFrame(rows)

    targets = build_buffered_targets(
        panel,
        dates,
        signal_column="signal",
        target_count=3,
        buffer_count=4,
    )

    assert set(targets[dates[0]]) == {"S00", "S01", "S02"}
    assert set(targets[dates[1]]) == {"S00", "S01", "S03"}
    assert targets[dates[1]].get("S02", 0.0) == 0.0
    assert sum(targets[dates[1]].values()) == 1.0


def test_lagged_turnover_excludes_the_formation_day() -> None:
    dates = pd.bdate_range("2024-01-02", periods=61)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "turnover_rate": np.arange(1.0, 62.0),
        }
    )

    panel = build_lagged_turnover_panel(
        daily,
        pd.DatetimeIndex([dates[-1]]),
        window=60,
        minimum_observations=60,
    )

    assert panel.loc[0, "turnover_lagged_mean_60d"] == np.mean(np.arange(1.0, 61.0))


def test_signal_correlation_diagnostic_compares_formation_dates() -> None:
    panel = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-31"] * 4),
            "signal_small_cap": [1.0, 2.0, 3.0, 4.0],
            "signal_low_turnover": [4.0, 3.0, 2.0, 1.0],
        }
    )

    result = _signal_correlations(panel)

    row = result.iloc[0]
    assert row["left_signal"] == "small_cap"
    assert row["right_signal"] == "low_turnover"
    assert row["mean_cross_sectional_correlation"] == -1.0
    assert row["formation_dates"] == 1


def test_eligibility_applies_listing_suspension_and_st_filters() -> None:
    date = pd.Timestamp("2024-01-31")
    symbols = ["A", "B", "C", "D"]
    panel = pd.DataFrame({"trade_date": date, "symbol": symbols, "signal": [4.0, 3.0, 2.0, 1.0]})
    universe = pd.DataFrame({"trade_date": date, "symbol": symbols[:3]})
    daily = pd.DataFrame(
        {
            "trade_date": date,
            "symbol": symbols[:3],
            "listed_days": [180, 179, 180],
            "amount": [100.0, 100.0, 0.0],
        }
    )
    st_history = pd.DataFrame({"trade_date": [date], "symbol": ["C"]})

    eligible = filter_candidate_eligibility(panel, universe, daily, st_history)

    assert eligible["symbol"].tolist() == ["A"]


def test_target_mapping_uses_the_following_trading_session() -> None:
    formation_date: pd.Timestamp = pd.Timestamp("2024-01-31")  # ty: ignore[invalid-assignment]
    execution_date: pd.Timestamp = pd.Timestamp("2024-02-01")  # ty: ignore[invalid-assignment]
    formation_targets: dict[pd.Timestamp, dict[str, float]] = {formation_date: {"A": 1.0}}

    mapped = map_targets_to_execution_dates(
        formation_targets,
        pd.DatetimeIndex([formation_date, execution_date]),
    )

    assert mapped == {execution_date: {"A": 1.0}}
