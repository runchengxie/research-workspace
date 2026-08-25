"""Field-level semantics for canonical promotion checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .promotion_evidence_common import date_token, finite_number, mapping

_BENCHMARK_AXES = ("universe", "horizon", "regime", "cost_bps")
CheckValidator = Callable[[Mapping[str, Any]], bool]


def _pit(entry: Mapping[str, Any]) -> bool:
    return all(
        entry.get(key) is True
        for key in ("pit_universe", "pit_fundamentals", "pit_industry_membership")
    )


def _walk_forward(entry: Mapping[str, Any]) -> bool:
    count = entry.get("window_count")
    return (
        isinstance(count, int)
        and not isinstance(count, bool)
        and count >= 2
        and bool(str(entry.get("metric") or "").strip())
    )


def _benchmark_matrix(entry: Mapping[str, Any]) -> bool:
    cells = entry.get("cells")
    if not isinstance(cells, list) or len(cells) < 2:
        return False
    span = sum(
        1
        for axis in _BENCHMARK_AXES
        if len({mapping(cell).get(axis) for cell in cells if isinstance(cell, Mapping)}) > 1
    )
    return span >= 2


def _cost(entry: Mapping[str, Any]) -> bool:
    scenarios = entry.get("scenarios")
    if not finite_number(entry.get("turnover"), nonnegative=True):
        return False
    if not isinstance(scenarios, list) or len(scenarios) < 2:
        return False
    costs: set[float] = set()
    for item in scenarios:
        row = mapping(item)
        if not finite_number(row.get("cost_bps"), nonnegative=True):
            return False
        if not str(row.get("metric") or "").strip() or not finite_number(row.get("value")):
            return False
        costs.add(float(row["cost_bps"]))
    return len(costs) >= 2


def _final_oos(entry: Mapping[str, Any]) -> bool:
    return (
        date_token(entry.get("oos_start")) is not None
        and bool(str(entry.get("metric") or "").strip())
        and entry.get("frozen_before_evaluation") is True
        and entry.get("retuned_after_freeze") is False
    )


def _cpcv(entry: Mapping[str, Any]) -> bool:
    groups = entry.get("n_groups")
    test_groups = entry.get("test_groups")
    return (
        isinstance(groups, int)
        and not isinstance(groups, bool)
        and isinstance(test_groups, int)
        and not isinstance(test_groups, bool)
        and 0 < test_groups < groups
        and bool(str(entry.get("metric") or "").strip())
    )


def _regime(entry: Mapping[str, Any]) -> bool:
    regimes = entry.get("regimes")
    if not str(entry.get("metric") or "").strip() or not isinstance(regimes, list):
        return False
    by_id = {mapping(item).get("id"): mapping(item) for item in regimes}
    return all(
        regime_id in by_id and finite_number(by_id[regime_id].get("value"))
        for regime_id in ("bull", "bear", "sideways")
    )


def _capacity(entry: Mapping[str, Any]) -> bool:
    portfolio_values = entry.get("portfolio_values")
    rates = entry.get("participation_rates")
    return (
        isinstance(portfolio_values, list)
        and len(portfolio_values) >= 2
        and all(finite_number(value, positive=True) for value in portfolio_values)
        and isinstance(rates, list)
        and len(rates) >= 2
        and all(finite_number(value, positive=True) for value in rates)
        and finite_number(entry.get("primary_participation_rate"), positive=True)
        and finite_number(entry.get("recommended_capacity"), positive=True)
    )


_VALIDATORS: dict[str, CheckValidator] = {
    "pit": _pit,
    "walk_forward": _walk_forward,
    "benchmark_matrix": _benchmark_matrix,
    "cost": _cost,
    "final_oos": _final_oos,
    "cpcv": _cpcv,
    "regime": _regime,
    "capacity": _capacity,
}


def check_errors(receipt: Mapping[str, Any], check_id: str) -> list[str]:
    entry = mapping(mapping(receipt.get("checks")).get(check_id))
    if entry.get("status") != "passed":
        return ["check_not_passed"]
    validator = _VALIDATORS.get(check_id)
    if validator is not None and not validator(entry):
        return ["check_fields_invalid"]
    return []
