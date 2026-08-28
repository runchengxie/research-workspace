"""Outcome-profile validation helpers for decision governance."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

OUTCOME_PROFILE_SCHEMA_VERSION = "outcome_profile.v1"
OUTCOME_DECISION_TYPES = {"entry", "exit", "portfolio", "allocation", "execution", "custom"}
OUTCOME_STATUSES = {"proposed", "active", "superseded", "retired"}
OUTCOME_DIRECTIONS = {"higher_is_better", "lower_is_better"}
OUTCOME_ROLES = {"objective", "constraint", "diagnostic"}
OUTCOME_OPERATORS = {"lt", "lte", "gt", "gte"}

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _required_text(payload: dict[str, Any], name: str, issues: list[str]) -> None:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{name} 必须是非空字符串")


def _check_metric_name(
    item: dict[str, Any],
    *,
    label: str,
    seen: set[str],
    issues: list[str],
) -> None:
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append(f"{label}.name 必须是非空字符串")
        return
    if name in seen:
        issues.append(f"metrics 名称重复：{name}")
        return
    seen.add(name)


def _check_constraint_fields(
    item: dict[str, Any],
    *,
    label: str,
    role: Any,
    issues: list[str],
) -> None:
    if role != "constraint":
        if "operator" in item or "threshold" in item:
            issues.append(f"{label} 只有 constraint 可以包含 operator 或 threshold")
        return
    if item.get("operator") not in OUTCOME_OPERATORS:
        issues.append(f"{label}.operator 必须属于 {sorted(OUTCOME_OPERATORS)}")
    threshold = item.get("threshold")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(float(threshold))
    ):
        issues.append(f"{label}.threshold 必须是有限数值")


def _check_metric(
    item: Any,
    *,
    index: int,
    seen: set[str],
    issues: list[str],
) -> None:
    label = f"metrics[{index}]"
    if not isinstance(item, dict):
        issues.append(f"{label} 必须是对象")
        return
    _check_metric_name(item, label=label, seen=seen, issues=issues)
    if item.get("direction") not in OUTCOME_DIRECTIONS:
        issues.append(f"{label}.direction 必须属于 {sorted(OUTCOME_DIRECTIONS)}")
    role = item.get("role")
    if role not in OUTCOME_ROLES:
        issues.append(f"{label}.role 必须属于 {sorted(OUTCOME_ROLES)}")
    unit = item.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        issues.append(f"{label}.unit 必须是非空字符串")
    _check_constraint_fields(item, label=label, role=role, issues=issues)


def _check_identity(
    relative: str,
    payload: dict[str, Any],
    root: Path,
    issues: list[str],
) -> None:
    profile_id = payload.get("outcome_profile_id")
    if isinstance(profile_id, str):
        if _ID_RE.fullmatch(profile_id) is None:
            issues.append("outcome_profile_id 必须是 [a-z0-9][a-z0-9._-]*")
        expected = root / "strategy-research" / "outcome-profiles" / f"{profile_id}.json"
        if root / relative != expected:
            issues.append(f"outcome profile 文件名必须与 outcome_profile_id 一致：{expected}")
    strategy_id = payload.get("strategy_id")
    if isinstance(strategy_id, str) and _ID_RE.fullmatch(strategy_id) is None:
        issues.append("strategy_id 必须是 [a-z0-9][a-z0-9._-]*")
    as_of = payload.get("as_of")
    if isinstance(as_of, str) and _DATE_RE.fullmatch(as_of) is None:
        issues.append("as_of 必须是 YYYY-MM-DD")


def check_outcome_profile_payload(
    relative: str,
    payload: dict[str, Any],
    root: Path,
) -> list[str]:
    """Validate one outcome-profile payload against governance semantics."""

    issues: list[str] = []
    if payload.get("schema_version") != OUTCOME_PROFILE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {OUTCOME_PROFILE_SCHEMA_VERSION}")
    for name in ("outcome_profile_id", "strategy_id", "statement", "as_of"):
        _required_text(payload, name, issues)
    _check_identity(relative, payload, root, issues)
    if payload.get("decision_type") not in OUTCOME_DECISION_TYPES:
        issues.append(f"decision_type 必须属于 {sorted(OUTCOME_DECISION_TYPES)}")
    if payload.get("status") not in OUTCOME_STATUSES:
        issues.append(f"status 必须属于 {sorted(OUTCOME_STATUSES)}")
    metrics = payload.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        issues.append("metrics 必须是非空列表")
        return issues
    seen: set[str] = set()
    for index, item in enumerate(metrics):
        _check_metric(item, index=index, seen=seen, issues=issues)
    return issues


__all__ = ["OUTCOME_PROFILE_SCHEMA_VERSION", "check_outcome_profile_payload"]
