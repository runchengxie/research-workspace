"""Strict, framework-neutral validation for qexec recovery matrix evidence.

This mirrors the persisted ``execution_recovery_matrix.v1`` wire contract without
importing qexec, vn.py, a broker SDK, or any execution runtime.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any, cast

EXECUTION_SCHEMA = "execution_recovery_matrix.v1"
RECOVERY_SCENARIOS = (
    "accepted_but_timeout",
    "duplicate_submission",
    "duplicate_callback",
    "out_of_order_callback",
    "partial_fill_restart",
    "cancel_fill_race",
    "reconnect_replay",
    "position_drift",
)
FORBIDDEN_TYPE_PREFIXES = ("qlib.", "vnpy.", "QuantConnect.")
TOP_LEVEL_KEYS = {"schema", "mode", "deterministic", "live_broker_access", "scenarios"}
SCENARIO_KEYS = {"id", "status", "expected_state", "reconciliation"}
STATE_KEYS = {
    "submission_state",
    "order_status",
    "broker_order_id",
    "filled_quantity",
    "remaining_quantity",
    "submission_attempt_count",
    "order_event_count",
    "fill_count",
    "journal_sequence",
    "transport_submit_calls",
    "idempotent_retry_blocked",
    "state_monotonic",
}
RECONCILIATION_KEYS = {
    "status",
    "result",
    "action",
    "evidence_count",
    "kill_switch",
    "position_drift",
}
SUBMISSION_STATES = {
    "RECORDED",
    "SUBMISSION_UNCERTAIN",
    "ACCEPTED",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
    "FAILED",
}
ORDER_STATUSES = {
    "PENDING",
    "NEW",
    "ACCEPTED",
    "PENDING_NEW",
    "PENDING_REPLACE",
    "WAIT_TO_NEW",
    "WAIT_TO_CANCEL",
    "PENDING_CANCEL",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCELLED",
    "REJECTED",
    "EXPIRED",
    "BLOCKED",
    "FAILED",
    "SUCCESS",
    "UNKNOWN",
}


def _walk_strings(value: Any, path: str = "$") -> list[tuple[str, str]]:
    strings: list[tuple[str, str]] = []
    if isinstance(value, str):
        strings.append((path, value))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            strings.extend(_walk_strings(item, f"{path}.{key}"))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            strings.extend(_walk_strings(item, f"{path}[{index}]"))
    return strings


def _framework_type_issues(payload: Mapping[str, Any]) -> list[str]:
    return [
        f"execution: framework runtime type leaked at {path}: {value}"
        for path, value in _walk_strings(payload)
        if value.startswith(FORBIDDEN_TYPE_PREFIXES)
    ]


def _exact_key_issues(
    payload: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> list[str]:
    actual = set(payload)
    if actual == expected:
        return []
    missing = ", ".join(sorted(expected - actual)) or "none"
    extra = ", ".join(sorted(actual - expected)) or "none"
    return [f"{label}: keys differ; missing={missing}; extra={extra}"]


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_canonical_decimal(value: object, *, signed: bool = False) -> bool:
    if not _is_non_empty_string(value):
        return False
    try:
        parsed = Decimal(cast(str, value))
    except InvalidOperation:
        return False
    if not parsed.is_finite() or (not signed and parsed < 0):
        return False
    canonical = "0" if parsed == 0 else format(parsed.normalize(), "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    return canonical == value


def _quantity_issues(label: str, state: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in ("filled_quantity", "remaining_quantity"):
        if not _is_canonical_decimal(state.get(field)):
            issues.append(f"{label}.{field} must be a canonical non-negative Decimal string")
    return issues


def _count_issues(label: str, state: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in (
        "submission_attempt_count",
        "order_event_count",
        "fill_count",
        "journal_sequence",
        "transport_submit_calls",
    ):
        if not _is_non_negative_integer(state.get(field)):
            issues.append(f"{label}.{field} must be a non-negative integer")
    return issues


def _submission_invariant_issues(label: str, state: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if state.get("submission_attempt_count") != 1:
        issues.append(f"{label}.submission_attempt_count must be 1")
    if state.get("transport_submit_calls") != 1:
        issues.append(f"{label}.transport_submit_calls must be 1")
    if state.get("idempotent_retry_blocked") is not True:
        issues.append(f"{label}.idempotent_retry_blocked must be true")
    if state.get("state_monotonic") is not True:
        issues.append(f"{label}.state_monotonic must be true")
    return issues


def _state_issues(identifier: str, value: object) -> list[str]:
    label = f"execution: {identifier} expected_state"
    if not isinstance(value, Mapping):
        return [f"{label} is missing"]
    state = cast(Mapping[str, Any], value)
    issues = _exact_key_issues(state, STATE_KEYS, label)
    if state.get("submission_state") not in SUBMISSION_STATES:
        issues.append(f"{label}.submission_state is invalid")
    order_status = state.get("order_status")
    if order_status is not None and order_status not in ORDER_STATUSES:
        issues.append(f"{label}.order_status is invalid")
    broker_order_id = state.get("broker_order_id")
    if broker_order_id is not None and not _is_non_empty_string(broker_order_id):
        issues.append(f"{label}.broker_order_id is invalid")
    return [
        *issues,
        *_quantity_issues(label, state),
        *_count_issues(label, state),
        *_submission_invariant_issues(label, state),
    ]


def _reconciliation_issues(identifier: str, value: object) -> list[str]:
    label = f"execution: {identifier} reconciliation"
    if not isinstance(value, Mapping):
        return [f"{label} result is missing"]
    reconciliation = cast(Mapping[str, Any], value)
    issues = _exact_key_issues(reconciliation, RECONCILIATION_KEYS, label)
    if reconciliation.get("status") not in {"resolved", "manual_intervention_required"}:
        issues.append(f"{label}.status is unsupported")
    for field in ("result", "action"):
        if not _is_non_empty_string(reconciliation.get(field)):
            issues.append(f"{label}.{field} must be a non-empty string")
    if not _is_non_negative_integer(reconciliation.get("evidence_count")):
        issues.append(f"{label}.evidence_count must be a non-negative integer")
    if not isinstance(reconciliation.get("kill_switch"), bool):
        issues.append(f"{label}.kill_switch must be a boolean")
    drift = reconciliation.get("position_drift")
    if drift is not None and not _is_canonical_decimal(drift, signed=True):
        issues.append(f"{label}.position_drift must be null or a canonical Decimal string")
    return issues


def _scenario_issues(identifier: str, item: Mapping[str, Any]) -> list[str]:
    issues = _exact_key_issues(item, SCENARIO_KEYS, f"execution: {identifier}")
    if item.get("status") != "passed":
        issues.append(f"execution: {identifier} did not pass")
    issues.extend(_state_issues(identifier, item.get("expected_state")))
    issues.extend(_reconciliation_issues(identifier, item.get("reconciliation")))
    return issues


def _index_scenarios(
    scenarios: list[object],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    issues: list[str] = []
    for item in scenarios:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            issues.append("execution: every item must have a string id")
            continue
        typed_item = cast(Mapping[str, Any], item)
        identifier = str(typed_item["id"])
        if identifier in indexed:
            issues.append(f"execution: duplicate id {identifier}")
        indexed[identifier] = typed_item
    return indexed, issues


def _header_issues(payload: Mapping[str, Any]) -> list[str]:
    issues = _exact_key_issues(payload, TOP_LEVEL_KEYS, "execution")
    if payload.get("schema") != EXECUTION_SCHEMA:
        issues.append(f"execution: schema must be {EXECUTION_SCHEMA}")
    if payload.get("deterministic") is not True:
        issues.append("execution: matrix must declare deterministic=true")
    if payload.get("live_broker_access") is not False:
        issues.append("execution: live_broker_access must be false")
    if payload.get("mode") not in {"paper", "shadow"}:
        issues.append("execution: mode must be paper or shadow")
    return issues


def validate_execution_evidence(payload: Mapping[str, Any]) -> list[str]:
    """Validate the exact qexec v1 matrix shape and recovery invariants."""

    issues = [*_framework_type_issues(payload), *_header_issues(payload)]
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        return [*issues, "execution: scenarios must be a list"]
    indexed, index_issues = _index_scenarios(scenarios)
    issues.extend(index_issues)
    scenario_ids = tuple(item.get("id") for item in scenarios if isinstance(item, Mapping))
    if scenario_ids != RECOVERY_SCENARIOS:
        issues.append("execution: scenarios must be the complete canonical matrix in order")
    for identifier, item in indexed.items():
        issues.extend(_scenario_issues(identifier, item))
    return issues


__all__ = ["RECOVERY_SCENARIOS", "validate_execution_evidence"]
