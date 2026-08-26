from __future__ import annotations

import numpy as np
import pandas as pd
from pytest import approx, raises

from experiments.style_factors.small_cap_low_turnover_exploration_20260826 import (
    _build_share_ledger_positions,
    _period_return_metrics,
    _run_capacity_ladder,
    _run_joint_matrix,
    _run_rebalance_matrix,
    _run_reconciliation_matrix,
    _run_share_ledger_matrix,
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
    build_rebalance_formation_dates,
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
        "signal_low_turnover_residual_industry",
        "signal_composite",
        "signal_composite_residual",
        "signal_composite_residual_industry",
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
    assert panel["signal_low_turnover_residual_industry"].notna().all()
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


def test_industry_residual_removes_industry_dummy_exposure() -> None:
    controls, turnover = _synthetic_signal_inputs()
    industry_offset = np.where(controls["industry_l1"] == "A", 2.0, -2.0)
    turnover["turnover_lagged_mean_60d"] = (
        4.0 + controls["size_score"] + 0.7 * controls["lowvol_score"] + industry_offset
    )

    panel = build_candidate_signal_panel(
        controls,
        turnover,
        minimum_sample=30,
    )

    plain = panel["signal_low_turnover_residual"]
    industry = panel["signal_low_turnover_residual_industry"]
    assert abs(industry.corr(panel["size_score"])) < 1e-10
    assert abs(industry.corr(panel["lowvol_score"])) < 1e-10
    industry_dummy = (panel["industry_l1"] == "A").astype(float)
    assert abs(industry.corr(industry_dummy)) < 1e-10
    assert abs(industry.corr(industry_dummy)) < abs(plain.corr(industry_dummy))


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


def test_lagged_turnover_counts_market_sessions_not_observed_rows() -> None:
    dates = pd.bdate_range("2024-01-02", periods=62)
    missing_date = dates[-3]
    daily = pd.DataFrame(
        [
            {"trade_date": date, "symbol": "A", "turnover_rate": 1.0}
            for date in dates
            if date != missing_date
        ]
        + [{"trade_date": date, "symbol": "B", "turnover_rate": 1.0} for date in dates]
    )

    panel = build_lagged_turnover_panel(
        daily,
        pd.DatetimeIndex([dates[-1]]),
        window=60,
        minimum_observations=60,
    )

    assert np.isnan(panel.loc[0, "turnover_lagged_mean_60d"])


def test_rebalance_formation_dates_monthly_selects_month_end_sessions() -> None:
    dates = pd.bdate_range("2024-01-02", "2024-06-28")
    result = build_rebalance_formation_dates(dates, frequency="monthly")
    expected = pd.DatetimeIndex(
        ["2024-01-31", "2024-02-29", "2024-03-29", "2024-04-30", "2024-05-31", "2024-06-28"]
    )
    assert list(result) == list(expected)


def test_rebalance_formation_dates_quarterly_selects_quarter_end_sessions() -> None:
    dates = pd.bdate_range("2024-01-02", "2024-12-31")
    result = build_rebalance_formation_dates(dates, frequency="quarterly")
    expected = pd.DatetimeIndex(["2024-03-29", "2024-06-28", "2024-09-30", "2024-12-31"])
    assert list(result) == list(expected)


def test_rebalance_formation_dates_weekly_has_more_dates_than_monthly() -> None:
    dates = pd.bdate_range("2024-01-02", "2024-12-31")
    weekly = build_rebalance_formation_dates(dates, frequency="weekly")
    monthly = build_rebalance_formation_dates(dates, frequency="monthly")
    biweekly = build_rebalance_formation_dates(dates, frequency="biweekly")
    assert len(weekly) > len(biweekly) > len(monthly)
    assert len(monthly) == 12


def test_rebalance_formation_dates_rejects_unknown_frequency() -> None:
    dates = pd.bdate_range("2024-01-02", "2024-01-31")
    invalid_frequency: str = "daily"
    with raises(ValueError, match="frequency"):
        build_rebalance_formation_dates(dates, frequency=invalid_frequency)  # ty: ignore[invalid-argument-type]


def test_rebalance_formation_dates_rejects_empty_calendar() -> None:
    with raises(ValueError, match="empty"):
        build_rebalance_formation_dates(pd.DatetimeIndex([]), frequency="monthly")


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


def test_trade_capacity_matrix_rejects_nonfinite_capital() -> None:
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

    for capital in (np.nan, np.inf):
        with raises(ValueError, match="positive"):
            build_trade_capacity_matrix(
                daily,
                returns,
                initial_capital=capital,
                participation_rate=0.10,
            )


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


def _synthetic_rebalance_daily() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", "2024-09-30")
    symbols = [f"S{index:02d}" for index in range(8)]
    rows = []
    for date in dates:
        for index, symbol in enumerate(symbols):
            rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "turnover_rate": 1.0 + index * 0.1,
                    "pct_chg": 0.0,
                    "amount": 1000.0 + index,
                    "close": 10.0 + index,
                    "tr_close": 10.0 + index,
                    "total_mv": 1e9 + index * 1e8,
                    "listed_days": 300,
                    "is_limit_up": False,
                    "is_limit_down": False,
                }
            )
    return pd.DataFrame(rows)


def test_rebalance_matrix_returns_all_frequencies_with_increasing_dates() -> None:
    daily = _synthetic_rebalance_daily()
    symbols = daily["symbol"].unique().tolist()
    universe = daily[["trade_date", "symbol"]].copy()
    st_history = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    instruments = pd.DataFrame({"symbol": symbols, "delist_date": pd.NaT})
    returns = daily_return_matrix(daily)
    matrices = execution_matrices(daily, returns)

    matrix = _run_rebalance_matrix(
        daily_clean=daily,
        sw_membership=None,
        universe=universe,
        st_history=st_history,
        instruments=instruments,
        transaction_cost_bps=10.0,
        target_count=4,
        buffer_count=6,
        minimum_listed_days=0,
        initial_capital=1_000_000.0,
        returns=returns,
        matrices=matrices,
    )

    expected_frequencies = {"weekly", "biweekly", "monthly", "quarterly"}
    assert set(matrix["rebalance_frequency"]) == expected_frequencies
    counts = {
        row["rebalance_frequency"]: row["formation_dates"]
        for row in matrix.to_dict(orient="records")
    }
    assert counts["weekly"] > counts["biweekly"] > counts["monthly"] > counts["quarterly"]
    assert all(row["holdout_days"] >= 0 for row in matrix.to_dict(orient="records"))


def test_share_ledger_positions_pair_rebalance_and_entry_dates() -> None:
    trading_dates = pd.bdate_range("2024-01-02", "2024-01-10")
    formation_targets: dict[pd.Timestamp, dict[str, float]] = {  # ty: ignore[invalid-assignment]
        pd.Timestamp("2024-01-02"): {"A": 0.5, "B": 0.5},
        pd.Timestamp("2024-01-09"): {"A": 1.0},
    }
    positions = _build_share_ledger_positions(formation_targets, trading_dates)
    assert list(positions.columns) == ["rebalance_date", "entry_date", "symbol", "weight", "side"]
    assert positions.loc[0, "rebalance_date"] == pd.Timestamp("2024-01-02")
    assert positions.loc[0, "entry_date"] == pd.Timestamp("2024-01-03")
    assert positions.loc[2, "entry_date"] == pd.Timestamp("2024-01-10")
    assert positions.loc[0, "side"] == "long"


def test_share_ledger_matrix_runs_with_cash_ledger_execution() -> None:
    daily = _synthetic_rebalance_daily()
    symbols = daily["symbol"].unique().tolist()
    universe = daily[["trade_date", "symbol"]].copy()
    st_history = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    instruments = pd.DataFrame({"symbol": symbols, "delist_date": pd.NaT})

    matrix = _run_share_ledger_matrix(
        daily_clean=daily,
        sw_membership=None,
        universe=universe,
        st_history=st_history,
        instruments=instruments,
        transaction_cost_bps=10.0,
        target_count=4,
        buffer_count=6,
        minimum_listed_days=0,
        initial_capital=1_000_000.0,
        frequencies=("monthly",),
    )

    assert not matrix.empty
    row = matrix.iloc[0]
    assert row["rebalance_frequency"] == "monthly"
    assert row["status"] == "ok"
    assert row["weight_level_targets"] > 0
    assert row["share_ledger_fill_ratio"] is not None


def test_reconciliation_matrix_decomposes_engine_gap() -> None:
    daily = _synthetic_rebalance_daily()
    symbols = daily["symbol"].unique().tolist()
    universe = daily[["trade_date", "symbol"]].copy()
    st_history = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    instruments = pd.DataFrame({"symbol": symbols, "delist_date": pd.NaT})
    returns = daily_return_matrix(daily)
    matrices = execution_matrices(daily, returns)

    matrix = _run_reconciliation_matrix(
        daily_clean=daily,
        sw_membership=None,
        universe=universe,
        st_history=st_history,
        instruments=instruments,
        transaction_cost_bps=10.0,
        target_count=4,
        buffer_count=6,
        minimum_listed_days=0,
        initial_capital=1_000_000.0,
        returns=returns,
        matrices=matrices,
        frequencies=("monthly",),
    )

    assert not matrix.empty
    composite_arms = set(matrix.loc[matrix["candidate"] == "composite", "engine_arm"])
    assert composite_arms == {
        "weight_level",
        "ideal_nav",
        "ledger_full",
        "ledger_no_participation",
        "ledger_no_t1",
        "ledger_no_lot",
        "ledger_zero_cost",
    }
    control_arms = set(matrix.loc[matrix["candidate"] == "large_cap_control", "engine_arm"])
    assert control_arms == {"weight_level", "ideal_nav", "ledger_full"}
    weight_rows = matrix.loc[matrix["engine_arm"] == "weight_level"]
    assert weight_rows["fill_ratio"].isna().all()
    ledger_rows = matrix.loc[matrix["engine_arm"] != "weight_level"]
    assert ledger_rows["fill_ratio"].notna().all()
    assert matrix["net_annual_return"].notna().all()


def test_capacity_ladder_reports_requested_capitals() -> None:
    daily = _synthetic_rebalance_daily()
    symbols = daily["symbol"].unique().tolist()
    universe = daily[["trade_date", "symbol"]].copy()
    st_history = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    instruments = pd.DataFrame({"symbol": symbols, "delist_date": pd.NaT})

    ladder = _run_capacity_ladder(
        daily_clean=daily,
        sw_membership=None,
        universe=universe,
        st_history=st_history,
        instruments=instruments,
        transaction_cost_bps=10.0,
        target_count=4,
        buffer_count=6,
        minimum_listed_days=0,
        capitals=(1_000_000.0, 10_000_000.0),
    )

    assert not ladder.empty
    assert ladder["capital"].tolist() == [1_000_000.0, 10_000_000.0]
    assert (ladder["status"] == "ok").all()
    assert ladder["fill_ratio"].notna().all()
    assert ladder["net_annual_return"].notna().all()


def test_joint_matrix_covers_definition_and_frequency_grid() -> None:
    daily = _synthetic_rebalance_daily()
    symbols = daily["symbol"].unique().tolist()
    universe = daily[["trade_date", "symbol"]].copy()
    st_history = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    instruments = pd.DataFrame({"symbol": symbols, "delist_date": pd.NaT})
    returns = daily_return_matrix(daily)
    matrices = execution_matrices(daily, returns)

    matrix = _run_joint_matrix(
        daily_clean=daily,
        sw_membership=None,
        universe=universe,
        st_history=st_history,
        instruments=instruments,
        transaction_cost_bps=10.0,
        target_count=4,
        buffer_count=6,
        minimum_listed_days=0,
        initial_capital=1_000_000.0,
        returns=returns,
        matrices=matrices,
        definitions=(("mean_20", 20, "mean"), ("mean_60", 60, "mean")),
        frequencies=("monthly",),
    )

    assert not matrix.empty
    assert set(matrix["turnover_definition"]) == {"mean_20", "mean_60"}
    assert set(matrix["rebalance_frequency"]) == {"monthly"}
    assert matrix["net_annual_return"].notna().all()
    # 合成数据落在 2024 年，开发窗为空属预期，保留期必须有值。
    assert matrix["development_annualized_return"].isna().all()
    assert matrix["holdout_annualized_return"].notna().all()
