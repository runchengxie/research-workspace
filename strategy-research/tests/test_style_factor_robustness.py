from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from style_factors.robustness_backtest import (
    RobustnessConfig,
    build_constrained_robustness,
)
from style_factors.robustness_constraints import (
    apply_explicit_suspensions,
    load_reported_borrow_activity_eligibility,
    load_st_event_evidence,
)
from style_factors.robustness_data import (
    _normalize_trade_dates,
    _require_unique,
)
from style_factors.robustness_execution import (
    attempt_pending_orders,
    simulate_leg,
    terminal_event_positions,
)
from style_factors.robustness_gate import CORE_FACTORS, evaluate_promotion_gate
from style_factors.robustness_report import _interpretation_guardrail_lines
from style_factors.robustness_sources import (
    expand_st_intervals,
    sha256_file,
)


def test_normalize_trade_dates_accepts_compact_and_iso_values() -> None:
    frame = pd.DataFrame({"trade_date": ["20240102", "2024-01-03"]})

    result = _normalize_trade_dates(frame)

    assert result["trade_date"].tolist() == [
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]


def test_report_guardrails_distinguish_robustness_from_investability() -> None:
    guardrails = "\n".join(_interpretation_guardrail_lines())

    assert "收益方向可以稳定为负" in guardrails
    assert "不等于因子可投资" in guardrails
    assert "真实可借库存" in guardrails


def test_robustness_loader_rejects_duplicate_market_grain() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")] * 2,
            "symbol": ["000001.SZ"] * 2,
        }
    )

    with pytest.raises(ValueError, match="duplicate"):
        _require_unique(frame, ["trade_date", "symbol"], label="daily_clean")


def test_reconstructed_st_intervals_expand_only_on_formation_dates(
    tmp_path: Path,
) -> None:
    interval_path = tmp_path / "st_intervals_reconstructed.parquet"
    pd.DataFrame(
        {
            "ts_code": ["000001.SZ"],
            "interval_start": ["20240102"],
            "interval_end": ["20240215"],
            "pit_class": ["reconstructed_pit"],
        }
    ).to_parquet(interval_path, index=False)
    receipt = {
        "intervals_sha256": sha256_file(interval_path),
        "pit_class": "reconstructed_pit",
        "revision_safe": False,
        "cross_validation": {"precision": 1.0, "recall": 1.0},
    }
    (tmp_path / "st_history_reconstructed.receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )

    history, metadata = expand_st_intervals(
        tmp_path,
        pd.DatetimeIndex(["2024-01-31", "2024-02-29"]),
    )

    assert history.to_dict(orient="records") == [
        {"trade_date": pd.Timestamp("2024-01-31"), "symbol": "000001.SZ"}
    ]
    assert metadata["st_revision_safe"] is False


def _write_constraint_source(
    root: Path,
    dataset: str,
    frame: pd.DataFrame,
    semantics: str,
) -> None:
    path = root / f"{dataset}.parquet"
    frame.to_parquet(path, index=False)
    (root / f"{dataset}.receipt.json").write_text(
        json.dumps(
            {
                "dataset": dataset,
                "quality_status": "complete",
                "sha256": sha256_file(path),
                "semantics": semantics,
            }
        ),
        encoding="utf-8",
    )


def test_reported_borrow_activity_requires_qualification_and_positive_activity(
    tmp_path: Path,
) -> None:
    _write_constraint_source(
        tmp_path,
        "margin_detail",
        pd.DataFrame(
            [
                {"trade_date": "20240131", "ts_code": "A", "rqyl": 10, "rqmcl": 0},
                {"trade_date": "20240131", "ts_code": "B", "rqyl": 0, "rqmcl": 0},
                {"trade_date": "20240131", "ts_code": "C", "rqyl": 5, "rqmcl": 0},
            ]
        ),
        "reported activity",
    )
    _write_constraint_source(
        tmp_path,
        "slb_sec_detail",
        pd.DataFrame(
            [
                {"trade_date": "20240131", "ts_code": "B", "lent_qnt": 20},
                {"trade_date": "20240131", "ts_code": "D", "lent_qnt": 20},
            ]
        ),
        "reported lending",
    )
    qualification = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-31")] * 3,
            "symbol": ["A", "B", "D"],
        }
    )

    result, metadata = load_reported_borrow_activity_eligibility(
        tmp_path,
        pd.DatetimeIndex(["2024-01-31"]),
        qualification,
    )

    assert result["symbol"].tolist() == ["A", "B", "D"]
    assert metadata["margin_detail_activity_rows"] == 2
    assert metadata["slb_sec_detail_activity_rows"] == 2


def test_explicit_suspensions_overlay_existing_price_rows_and_st_events_are_verified(
    tmp_path: Path,
) -> None:
    _write_constraint_source(
        tmp_path,
        "suspend_d",
        pd.DataFrame(
            [
                {"trade_date": "20240131", "ts_code": "A"},
                {"trade_date": "20240131", "ts_code": "MISSING"},
            ]
        ),
        "explicit suspension",
    )
    _write_constraint_source(
        tmp_path,
        "st",
        pd.DataFrame(
            [
                {"ts_code": "A", "imp_date": "20240131", "st_type": "ST"},
                {"ts_code": "B", "imp_date": "20240201", "st_type": "撤销ST"},
            ]
        ),
        "event evidence",
    )
    daily = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-31"), pd.Timestamp("2024-01-31")],
            "symbol": ["A", "B"],
            "is_suspended": [False, False],
        }
    )

    result, metadata = apply_explicit_suspensions(daily, tmp_path)
    st_metadata = load_st_event_evidence(tmp_path)

    assert result.set_index("symbol")["is_suspended"].to_dict() == {"A": True, "B": False}
    assert metadata["suspend_events_on_price_rows"] == 1
    assert metadata["suspend_events_without_price_rows"] == 1
    assert st_metadata["provider_st_event_rows"] == 2
    assert st_metadata["provider_st_event_types"] == ["ST", "撤销ST"]


def test_constraint_source_rejects_incomplete_or_mutated_receipts(tmp_path: Path) -> None:
    _write_constraint_source(
        tmp_path,
        "suspend_d",
        pd.DataFrame([{"trade_date": "20240131", "ts_code": "A"}]),
        "explicit suspension",
    )
    receipt_path = tmp_path / "suspend_d.receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["quality_status"] = "partial"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="quality_status=complete"):
        apply_explicit_suspensions(
            pd.DataFrame(
                {
                    "trade_date": [pd.Timestamp("2024-01-31")],
                    "symbol": ["A"],
                    "is_suspended": [False],
                }
            ),
            tmp_path,
        )


def test_pending_orders_retry_price_limit_blocked_entry_and_exit() -> None:
    weights = np.array([0.0, 1.0])
    target = np.array([1.0, 0.0])
    pending = np.array([True, True])
    tradable = np.array([True, True])

    weights, pending, traded, blocked_entry, blocked_exit = attempt_pending_orders(
        weights,
        target,
        pending,
        tradable=tradable,
        limit_up=np.array([True, False]),
        limit_down=np.array([False, True]),
        side="long",
    )

    assert traded == 0.0
    assert blocked_entry and blocked_exit
    assert pending.all()

    weights, pending, traded, blocked_entry, blocked_exit = attempt_pending_orders(
        weights,
        target,
        pending,
        tradable=tradable,
        limit_up=np.array([False, False]),
        limit_down=np.array([False, False]),
        side="long",
    )

    assert np.allclose(weights, target)
    assert not pending.any()
    assert traded == 2.0
    assert not blocked_entry and not blocked_exit


def test_delisting_event_maps_to_first_market_date_on_or_after_delist() -> None:
    instruments = pd.DataFrame({"symbol": ["A"], "delist_date": [pd.Timestamp("2024-01-06")]})
    trading_dates = pd.DatetimeIndex(["2024-01-05", "2024-01-08"])

    events = terminal_event_positions(instruments, trading_dates, {"A": 0})

    assert list(events) == [pd.Timestamp("2024-01-08")]
    assert events[pd.Timestamp("2024-01-08")].tolist() == [0]  # ty: ignore[invalid-argument-type]


def test_close_execution_starts_exposure_on_following_return_interval() -> None:
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    returns = pd.DataFrame({"A": [0.10, 0.20]}, index=dates)
    matrices = (
        np.ones((2, 1), dtype=bool),
        np.zeros((2, 1), dtype=bool),
        np.zeros((2, 1), dtype=bool),
    )

    result = simulate_leg(
        returns,
        matrices,
        {dates[0]: {"A": 1.0}},
        {},
        side="long",
        terminal_return=-0.5,
    )

    assert result.returns.tolist() == [0.0, 0.20]
    assert result.traded_notional.tolist() == [1.0, 0.0]


def test_terminal_mark_liquidates_position_after_applying_stress_return() -> None:
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    returns = pd.DataFrame({"A": [0.0, np.nan, 0.50]}, index=dates)
    matrices = (
        np.ones((3, 1), dtype=bool),
        np.zeros((3, 1), dtype=bool),
        np.zeros((3, 1), dtype=bool),
    )

    result = simulate_leg(
        returns,
        matrices,
        {dates[0]: {"A": 1.0}},
        {dates[1]: np.asarray([0], dtype=int)},
        side="long",
        terminal_return=-0.5,
    )

    assert result.returns.tolist() == [0.0, -0.5, 0.0]
    assert result.terminal_events == 1


def _small_robustness_frames() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, dict[str, pd.Series]],
]:
    dates = pd.bdate_range("2024-01-02", periods=70)
    formation_dates = pd.DatetimeIndex([dates[20], dates[40], dates[60]])
    symbols = [f"{index:06d}.SZ" for index in range(60)]
    market_rows = []
    factor_rows = []
    for symbol_number, symbol in enumerate(symbols):
        for day_number, date in enumerate(dates):
            market_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "pct_chg": (symbol_number - 30) / 1000 + day_number / 10000,
                    "amount": 1000.0,
                    "is_limit_up": False,
                    "is_limit_down": False,
                    "listed_days": 500,
                }
            )
        for date in formation_dates:
            factor_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "factor_size_z": float(symbol_number),
                }
            )
    daily_clean = pd.DataFrame(market_rows)
    factors = pd.DataFrame(factor_rows)
    universe = pd.DataFrame(
        [{"trade_date": date, "symbol": symbol} for date in formation_dates for symbol in symbols]
    )
    baseline_series = pd.Series(0.0001, index=dates[21:], name="size")
    baseline = {"size": {"long_short": baseline_series}}
    return factors, daily_clean, universe, baseline


def test_constrained_profile_charges_actual_turnover_costs() -> None:
    factors, daily_clean, universe, baseline = _small_robustness_frames()
    artifacts = build_constrained_robustness(
        factors,
        daily_clean,
        universe,
        pd.DataFrame(columns=pd.Index(["trade_date", "symbol"])),
        pd.DataFrame(columns=pd.Index(["symbol", "delist_date"])),
        baseline,
        margin_eligibility=universe,
        config=RobustnessConfig(
            transaction_cost_bps=10.0,
            cost_scenarios_bps=(0.0, 10.0),
            delist_scenarios=(-0.5,),
        ),
    )

    gross = artifacts.gross_results["size"]["long_short"]
    net = artifacts.net_results["size"]["long_short"]
    costs = artifacts.net_results["size"]["transaction_cost"]
    assert np.allclose(net, gross - costs)
    assert costs.sum() > 0
    assert set(artifacts.comparison["profile"]) == {
        "raw_gross_matched_window",
        "constrained_gross",
        "constrained_net",
    }
    assert "size" in artifacts.margin_net_results
    assert set(artifacts.margin_comparison["profile"]) == {
        "constrained_net_matched_reported_activity_window",
        "reported_borrow_activity_proxy_net",
    }


def test_promotion_gate_holds_when_one_core_factor_changes_direction() -> None:
    comparison_rows = []
    for factor in CORE_FACTORS:
        for profile, annual, drawdown in (
            ("raw_gross_matched_window", 5.0, -20.0),
            ("constrained_gross", 4.0, -22.0),
            ("constrained_net", -1.0 if factor == "momentum" else 3.0, -25.0),
        ):
            comparison_rows.append(
                {
                    "factor": factor,
                    "profile": profile,
                    "days": 100,
                    "geometric_annual_ret": annual,
                    "max_drawdown": drawdown,
                }
            )
    scenarios = pd.DataFrame(
        [
            {
                "factor": factor,
                "terminal_return": -0.5,
                "cost_bps": 30.0,
                "geometric_annual_ret": -2.0 if factor == "momentum" else 2.0,
            }
            for factor in CORE_FACTORS
        ]
    )

    gate, decision = evaluate_promotion_gate(
        pd.DataFrame(comparison_rows),
        scenarios,
        config=RobustnessConfig(),
    )

    assert decision["decision"] == "hold"
    assert decision["core_factors_passed"] == len(CORE_FACTORS) - 1
    assert gate.loc[gate["factor"].eq("momentum"), "direction_pass"].item() is False
