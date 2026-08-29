from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from style_factors.microcap_robustness import (
    MICROCAP_ARTIFACTS,
    assign_registration_regime,
    build_candidate_panels_for_variants,
    build_hard_eligible_reference_universe,
    build_microcap_daily_returns,
    build_microcap_factor_matrix,
    build_microcap_long_only_matrix,
    build_microcap_regimes,
    build_microcap_universe_variants,
    build_microcap_weighting_matrix,
    build_microcap_yearly,
    reweight_formation_targets,
    write_microcap_artifacts,
)


def test_reference_universe_applies_hard_filters_before_market_cap() -> None:
    date = pd.Timestamp("2024-01-31")
    daily = pd.DataFrame(
        {
            "trade_date": [date] * 5,
            "symbol": ["A", "B", "C", "D", "E"],
            "listed_days": [200, 200, 100, 200, 200],
            "amount": [100.0, 0.0, 100.0, 100.0, 100.0],
            "total_mv": [1.0, 2.0, 3.0, 4.0, np.nan],
        }
    )
    universe = daily[["trade_date", "symbol"]]
    st_history = pd.DataFrame({"trade_date": [date], "symbol": ["D"]})
    reference, diagnostics = build_hard_eligible_reference_universe(
        daily,
        universe,
        st_history,
        formation_dates=pd.DatetimeIndex([date]),
        minimum_listed_days=180,
    )
    assert reference["symbol"].tolist() == ["A"]
    row = diagnostics.iloc[0]
    assert row["eligible_before_market_cap_filter"] == 2
    assert row["invalid_market_cap_count"] == 1
    assert row["eligible_reference"] == 1


def test_microcap_variants_use_floor_count_and_symbol_tiebreaker() -> None:
    date = pd.Timestamp("2024-01-31")
    reference = pd.DataFrame(
        {
            "trade_date": [date] * 10,
            "symbol": list("JIHGFEDCBA"),
            "total_mv": [1.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
        }
    )
    variants, diagnostics = build_microcap_universe_variants(reference)
    assert [len(variants[p]) for p in (0.0, 0.1, 0.2, 0.3)] == [10, 9, 8, 7]
    assert "I" not in set(variants[0.1]["symbol"])
    row = diagnostics.loc[diagnostics["exclusion_percentile"].eq(0.3)].iloc[0]
    assert row["excluded_count"] == 3
    assert row["eligible_after"] == 7
    assert 0 < row["excluded_market_cap_share"] < 1


def test_microcap_variants_reject_duplicate_keys() -> None:
    date = pd.Timestamp("2024-01-31")
    reference = pd.DataFrame(
        {"trade_date": [date, date], "symbol": ["A", "A"], "total_mv": [1.0, 2.0]}
    )
    with pytest.raises(ValueError, match="duplicate"):
        build_microcap_universe_variants(reference)


def test_reweight_formation_targets_changes_weights_not_symbols() -> None:
    date = pd.Timestamp("2024-01-31")
    targets = {date: {"A": 0.5, "B": 0.5}}
    caps = pd.DataFrame(
        {"trade_date": [date, date], "symbol": ["A", "B"], "total_mv": [1.0, 3.0]}
    )
    equal = reweight_formation_targets(targets, caps, weighting="equal")
    value = reweight_formation_targets(targets, caps, weighting="value")
    assert set(equal[date]) == set(value[date]) == {"A", "B"}
    assert equal[date] == pytest.approx({"A": 0.5, "B": 0.5})
    assert value[date] == pytest.approx({"A": 0.25, "B": 0.75})


def test_reweight_formation_targets_rejects_invalid_selected_cap() -> None:
    date = pd.Timestamp("2024-01-31")
    targets = {date: {"A": 0.5, "B": 0.5}}
    caps = pd.DataFrame(
        {"trade_date": [date, date], "symbol": ["A", "B"], "total_mv": [1.0, 0.0]}
    )
    with pytest.raises(ValueError, match="finite positive"):
        reweight_formation_targets(targets, caps, weighting="value")


def test_factor_matrix_distinguishes_equal_and_value_weighting() -> None:
    formation = pd.Timestamp("2024-01-31")
    next_formation = pd.Timestamp("2024-02-29")
    symbols = [f"S{i:02d}" for i in range(60)]
    factors = pd.DataFrame(
        {"trade_date": formation, "symbol": symbols, "factor_size_z": np.arange(60, dtype=float)}
    )
    caps = factors[["trade_date", "symbol"]].copy()
    caps["total_mv"] = np.arange(1, 61, dtype=float)
    daily = pd.DataFrame(
        [
            {"trade_date": date, "symbol": symbol, "pct_chg": (index - 29.5) * 0.01}
            for date in pd.bdate_range("2024-02-01", "2024-02-29")
            for index, symbol in enumerate(symbols)
        ]
    )
    matrix, _ = build_microcap_factor_matrix(
        {0.0: factors},
        {0.0: caps},
        daily=daily,
        rebalance_dates=pd.DatetimeIndex([formation, next_formation]),
    )
    rows = matrix.loc[matrix["factor"].eq("size")]
    assert set(rows["weighting"]) == {"equal", "value"}
    assert rows["annual_return"].nunique() == 2


def _candidate_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[float, pd.DataFrame], pd.DataFrame, pd.DatetimeIndex]:
    formation_dates = pd.DatetimeIndex(["2024-01-31", "2024-02-29", "2024-03-29"])
    symbols = [f"S{i:02d}" for i in range(40)]
    controls_rows: list[dict[str, object]] = []
    turnover_rows: list[dict[str, object]] = []
    cap_rows: list[dict[str, object]] = []
    for date in formation_dates:
        for index, symbol in enumerate(symbols):
            controls_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "industry_l1": "A" if index < 20 else "B",
                    "size_score": float(index),
                    "lowvol_score": np.sin(index / 4),
                }
            )
            turnover_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "turnover_lagged_mean_60d": float(40 - index),
                }
            )
            cap_rows.append(
                {"trade_date": date, "symbol": symbol, "total_mv": float(index + 1)}
            )
    variants = {0.0: pd.DataFrame(cap_rows)}
    return pd.DataFrame(controls_rows), pd.DataFrame(turnover_rows), variants, pd.DataFrame(cap_rows), formation_dates


def _candidate_daily(formation_dates: pd.DatetimeIndex) -> pd.DataFrame:
    symbols = [f"S{i:02d}" for i in range(40)]
    dates = pd.bdate_range(formation_dates.min(), formation_dates.max())
    return pd.DataFrame(
        [
            {
                "trade_date": date,
                "symbol": symbol,
                "pct_chg": (index - 20) * 0.01,
                "amount": 1000.0,
                "is_limit_up": False,
                "is_limit_down": False,
            }
            for date in dates
            for index, symbol in enumerate(symbols)
        ]
    )


def test_candidate_panel_is_restandardized_after_variant_filter() -> None:
    controls, turnover, variants, _caps, _dates = _candidate_inputs()
    full = build_candidate_panels_for_variants(controls, turnover, variants)[0.0]
    smaller_keys = variants[0.0].loc[variants[0.0]["symbol"].ge("S10")]
    smaller = build_candidate_panels_for_variants(controls, turnover, {0.3: smaller_keys})[0.3]
    common = sorted(set(full["symbol"]) & set(smaller["symbol"]))
    full_scores = full.loc[full["symbol"].isin(common)].set_index(["trade_date", "symbol"])["signal_small_cap"]
    smaller_scores = smaller.set_index(["trade_date", "symbol"])["signal_small_cap"]
    assert not full_scores.equals(smaller_scores)


def test_long_only_matrix_keeps_selected_names_across_weighting_modes() -> None:
    controls, turnover, variants, caps, formation_dates = _candidate_inputs()
    panels = build_candidate_panels_for_variants(controls, turnover, variants)
    daily = _candidate_daily(formation_dates)
    instruments = pd.DataFrame({"symbol": [f"S{i:02d}" for i in range(40)], "delist_date": pd.NaT})
    matrix, simulations, target_plans = build_microcap_long_only_matrix(
        panels,
        {0.0: caps},
        formation_dates=formation_dates,
        daily_clean=daily,
        instruments=instruments,
        candidates={"small_cap": "signal_small_cap"},
        target_count=10,
        buffered_count=15,
        transaction_cost_bps=10.0,
        initial_capital=10_000_000.0,
    )
    assert not matrix.empty
    assert simulations
    equal = target_plans[("small_cap", 0.0, "equal", "buffered")]
    value = target_plans[("small_cap", 0.0, "value", "buffered")]
    for date in equal:
        assert set(equal[date]) == set(value[date])
        if value[date]:
            assert sum(value[date].values()) == pytest.approx(1.0)


def test_daily_returns_and_summary_tables_share_one_normalized_source() -> None:
    controls, turnover, variants, caps, formation_dates = _candidate_inputs()
    panels = build_candidate_panels_for_variants(controls, turnover, variants)
    daily = _candidate_daily(formation_dates)
    instruments = pd.DataFrame({"symbol": [f"S{i:02d}" for i in range(40)], "delist_date": pd.NaT})
    _matrix, simulations, _plans = build_microcap_long_only_matrix(
        panels,
        {0.0: caps},
        formation_dates=formation_dates,
        daily_clean=daily,
        instruments=instruments,
        candidates={"small_cap": "signal_small_cap"},
        target_count=10,
        buffered_count=15,
        transaction_cost_bps=10.0,
        initial_capital=10_000_000.0,
    )
    normalized = build_microcap_daily_returns({}, simulations, transaction_cost_bps=10.0)
    yearly = build_microcap_yearly(normalized)
    regimes = build_microcap_regimes(normalized)
    assert {"gross", "net"} <= set(normalized["return_type"])
    assert not yearly.empty
    assert not regimes.empty


def test_build_microcap_weighting_matrix_reports_value_minus_equal() -> None:
    factor_matrix = pd.DataFrame(
        {
            "factor": ["size", "size"],
            "exclusion_percentile": [0.3, 0.3],
            "weighting": ["equal", "value"],
            "annual_return": [10.0, 4.0],
            "sharpe": [1.0, 0.5],
            "max_drawdown": [-20.0, -10.0],
            "observations": [100, 100],
        }
    )
    result = build_microcap_weighting_matrix(factor_matrix)
    assert result.loc[0, "value_minus_equal_annual_return"] == pytest.approx(-6.0)


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        ("2019-07-19", "pre_registration_pilot"),
        ("2019-07-22", "registration_pilot"),
        ("2023-02-16", "registration_pilot"),
        ("2023-02-17", "full_registration"),
    ],
)
def test_registration_regime_boundaries(date: str, expected: str) -> None:
    assert assign_registration_regime(pd.Timestamp(date)) == expected


def test_write_microcap_artifacts_uses_stable_filenames(tmp_path: Path) -> None:
    universe = pd.DataFrame(
        {
            "formation_date": [pd.Timestamp("2024-01-31")],
            "exclusion_percentile": [0.0],
            "eligible_reference": [100],
            "excluded_count": [0],
            "eligible_after": [100],
            "market_cap_cutoff": [np.nan],
            "excluded_market_cap_share": [0.0],
        }
    )
    factors = pd.DataFrame(
        {
            "factor": ["size"],
            "exclusion_percentile": [0.0],
            "weighting": ["equal"],
            "annual_return": [1.0],
            "sharpe": [0.1],
            "max_drawdown": [-2.0],
            "observations": [21],
        }
    )
    weighting = pd.DataFrame(
        {"factor": ["size"], "exclusion_percentile": [0.0], "equal_annual_return": [1.0], "value_annual_return": [0.5], "value_minus_equal_annual_return": [-0.5]}
    )
    buffer = pd.DataFrame({"candidate": ["small_cap"], "exclusion_percentile": [0.0], "weighting": ["equal"], "buffer_setting": ["buffered"]})
    capacity = pd.DataFrame({"candidate": ["small_cap"], "exclusion_percentile": [0.0], "weighting": ["equal"], "capital": [10_000_000.0]})
    yearly = pd.DataFrame({"year": [2024], "name": ["size"]})
    regimes = pd.DataFrame({"regime": ["full_registration"], "name": ["size"]})
    write_microcap_artifacts(
        tmp_path,
        universe_diagnostics=universe,
        factor_matrix=factors,
        weighting_matrix=weighting,
        buffer_matrix=buffer,
        capacity_matrix=capacity,
        yearly=yearly,
        regimes=regimes,
        summary={"schema_version": 1},
    )
    assert {path.name for path in tmp_path.iterdir()} == set(MICROCAP_ARTIFACTS.values())
    payload = json.loads((tmp_path / MICROCAP_ARTIFACTS["summary"]).read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
