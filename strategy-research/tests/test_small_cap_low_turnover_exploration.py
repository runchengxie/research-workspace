from __future__ import annotations

import numpy as np
import pandas as pd
from pytest import approx, raises

from experiments.style_factors.small_cap_low_turnover_exploration_20260826 import (
    _period_return_metrics,
    _signal_correlations,
)
from style_factors.robustness_execution import (
    daily_return_matrix,
    execution_matrices,
    simulate_leg,
)
from style_factors.small_cap_low_turnover import (
    build_buffered_targets,
    build_candidate_signal_panel,
    build_lagged_turnover_panel,
    build_trade_capacity_matrix,
    filter_candidate_eligibility,
    map_targets_to_execution_dates,
    round_target_weights_to_lots,
    simulate_long_only_candidates,
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


def test_lagged_turnover_supports_median_aggregation() -> None:
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
        statistic="median",
    )

    assert panel.loc[0, "turnover_lagged_median_60d"] == 30.5


def test_trade_capacity_matrix_converts_amount_to_weight_capacity() -> None:
    dates = pd.bdate_range("2024-01-02", periods=3)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": [0.0, 0.0, 0.0],
            "amount": [1000.0, 500.0, 250.0],
        }
    )
    returns = daily_return_matrix(daily)

    capacity = build_trade_capacity_matrix(
        daily,
        returns,
        initial_capital=1_000_000.0,
        participation_rate=0.10,
    )

    assert capacity[:, 0].tolist() == [0.0, 0.1, 0.05]


def test_trade_capacity_matrix_supports_zero_capacity_rows() -> None:
    dates = pd.bdate_range("2024-01-02", periods=2)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": [0.0, 0.0],
            "amount": [100.0, 100.0],
        }
    )
    returns = daily_return_matrix(daily)

    capacity = build_trade_capacity_matrix(
        daily,
        returns,
        initial_capital=1_000_000.0,
        participation_rate=0.0,
    )

    assert capacity.tolist() == [[0.0], [0.0]]


def test_lot_rounding_floors_target_shares() -> None:
    prior_date: pd.Timestamp = pd.Timestamp("2024-01-31")  # ty: ignore[invalid-assignment]
    execution_date: pd.Timestamp = pd.Timestamp("2024-02-01")  # ty: ignore[invalid-assignment]
    daily = pd.DataFrame(
        {
            "trade_date": [prior_date, execution_date],
            "symbol": ["A", "A"],
            "close": [12.34, 99.99],
        }
    )

    rounded = round_target_weights_to_lots(
        {execution_date: {"A": 0.5}},
        daily,
        initial_capital=100_000.0,
        lot_size=100,
    )

    assert rounded[execution_date]["A"] == approx(0.4936)


def test_simulation_respects_trade_capacity_without_changing_default() -> None:
    dates = pd.bdate_range("2024-01-02", periods=2)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": [0.0, 0.0],
            "amount": [1000.0, 1000.0],
            "is_limit_up": False,
            "is_limit_down": False,
        }
    )
    returns = daily_return_matrix(daily)
    matrices = execution_matrices(daily, returns)
    capacity = np.full((len(dates), 1), 0.25)

    simulation = simulate_leg(
        returns,
        matrices,
        {dates[0]: {"A": 1.0}},
        terminal_events={},
        side="long",
        terminal_return=-0.5,
        max_trade_weight=capacity,
    )
    uncapped = simulate_leg(
        returns,
        matrices,
        {dates[0]: {"A": 1.0}},
        terminal_events={},
        side="long",
        terminal_return=-0.5,
    )

    assert simulation.traded_notional.iloc[0] == 0.25
    assert uncapped.traded_notional.iloc[0] == 1.0


def test_simulation_rejects_nonfinite_trade_capacity() -> None:
    dates = pd.bdate_range("2024-01-02", periods=1)
    daily = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": "A",
            "pct_chg": [0.0],
            "amount": [1000.0],
            "is_limit_up": False,
            "is_limit_down": False,
        }
    )
    returns = daily_return_matrix(daily)
    matrices = execution_matrices(daily, returns)

    with raises(ValueError, match="finite"):
        simulate_leg(
            returns,
            matrices,
            {dates[0]: {"A": 1.0}},
            terminal_events={},
            side="long",
            terminal_return=-0.5,
            max_trade_weight=np.array([[np.nan]]),
        )


def test_period_return_metrics_separates_development_and_holdout_windows() -> None:
    dates = pd.to_datetime(["2023-12-29", "2024-01-02", "2024-01-03"])
    returns = pd.Series([0.10, 0.20, -0.10], index=dates)
    holdout_start: pd.Timestamp = pd.Timestamp("2024-01-01")  # ty: ignore[invalid-assignment]
    holdout_end: pd.Timestamp = pd.Timestamp("2024-12-31")  # ty: ignore[invalid-assignment]

    metrics = _period_return_metrics(
        returns,
        start=holdout_start,
        end=holdout_end,
    )

    assert metrics["days"] == 2
    assert metrics["cumulative_return"] == approx(0.08)


def test_candidate_simulation_accepts_precomputed_execution_context() -> None:
    dates = pd.bdate_range("2024-01-02", periods=3)
    symbols = ["A", "B"]
    daily = pd.DataFrame(
        [
            {
                "trade_date": date,
                "symbol": symbol,
                "pct_chg": 0.0,
                "amount": 1000.0,
                "close": 10.0,
                "listed_days": 200,
                "is_limit_up": False,
                "is_limit_down": False,
            }
            for date in dates
            for symbol in symbols
        ]
    )
    signal_panel = pd.DataFrame(
        [
            {"trade_date": dates[0], "symbol": "A", "signal": 1.0},
            {"trade_date": dates[0], "symbol": "B", "signal": 0.0},
            {"trade_date": dates[1], "symbol": "A", "signal": 0.0},
            {"trade_date": dates[1], "symbol": "B", "signal": 1.0},
        ]
    )
    universe = signal_panel[["trade_date", "symbol"]].copy()
    st_history = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    instruments = pd.DataFrame({"symbol": symbols, "delist_date": pd.NaT})
    returns = daily_return_matrix(daily)
    matrices = execution_matrices(daily, returns)

    simulations = simulate_long_only_candidates(
        signal_panel,
        daily,
        universe,
        st_history,
        instruments,
        {"candidate": "signal"},
        target_count=1,
        buffer_count=1,
        minimum_listed_days=0,
        returns=returns,
        matrices=matrices,
    )

    assert set(simulations) == {"candidate"}
