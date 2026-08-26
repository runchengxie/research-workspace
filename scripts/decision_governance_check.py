#!/usr/bin/env python3
"""Validate decision-governance claims, cases, sources and counterexamples.

DG1 validates ``claim.v1`` judgments, DG2 validates ``research_case.v1`` decision
navigation, DG3 validates optional ``source.v1`` records, and DG8 validates
``counterexample.v1`` stress evidence. DG4/DG5/DG6 case rules remain enforced.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
CLAIM_SCHEMA_VERSION = "claim.v1"
CASE_SCHEMA_VERSION = "research_case.v1"
SOURCE_SCHEMA_VERSION = "source.v1"
COUNTEREXAMPLE_SCHEMA_VERSION = "counterexample.v1"
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
CLAIM_TYPES = {"hypothesis", "fact", "estimate", "inference"}
CLAIM_STATUSES = {"active", "proposed", "superseded", "rejected"}
DECISION_STATUSES = {"no_view", "provisional", "accepted", "rejected"}
SOURCE_CLAIM_TYPES = {"fact", "estimate", "guidance", "opinion", "inference", "forecast"}
SOURCE_DIRECTNESS = {"primary", "secondary", "tertiary"}
SOURCE_VERIFIABILITY = {"independently_verified", "single_source", "unverifiable"}
REVIEW_KINDS = {"logic", "evidence"}
REVIEW_STATUSES = {"completed", "in_progress", "pending"}
COUNTEREXAMPLE_TYPES = {
    "time_window",
    "market_regime",
    "cost",
    "liquidity",
    "capacity",
    "exposure",
    "signal_perturbation",
    "correlation",
    "custom",
}
COUNTEREXAMPLE_STATUSES = {"open", "confirmed", "resolved", "superseded"}
COUNTEREXAMPLE_SEVERITIES = {"minor", "material", "critical"}


@dataclass(frozen=True)
class GovernanceCheck:
    path: str
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _required_text(payload: dict[str, Any], name: str, issues: list[str]) -> None:
    value = payload.get(name)
    if value is None:
        issues.append(f"{name} 缺失")
    elif not isinstance(value, str) or not value.strip():
        issues.append(f"{name} 必须是非空字符串")


def _string_list(payload: dict[str, Any], name: str, issues: list[str]) -> None:
    value = payload.get(name)
    if value is None:
        return
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        issues.append(f"{name} 必须是字符串列表")


def _objects_list(
    payload: dict[str, Any],
    name: str,
    required_fields: tuple[str, ...],
    issues: list[str],
) -> None:
    value = payload.get(name)
    if value is None:
        return
    if not isinstance(value, list):
        issues.append(f"{name} 必须是列表")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            issues.append(f"{name}[{index}] 必须是对象")
            continue
        missing = [field_name for field_name in required_fields if field_name not in item]
        if missing:
            issues.append(f"{name}[{index}] 缺少字段：{','.join(missing)}")
        for field_name in required_fields:
            if field_name in item and not isinstance(item[field_name], str):
                issues.append(f"{name}[{index}].{field_name} 必须是字符串")


def _check_source(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != SOURCE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {SOURCE_SCHEMA_VERSION}")
    for name in ("source_id", "source_type", "publisher"):
        _required_text(payload, name, issues)
    published_at = payload.get("published_at")
    if isinstance(published_at, str) and DATE_RE.fullmatch(published_at) is None:
        issues.append("published_at 必须是 YYYY-MM-DD")
    for name in ("effective_at", "observed_at", "ingested_at"):
        value = payload.get(name)
        if value is not None and isinstance(value, str) and DATE_RE.fullmatch(value) is None:
            issues.append(f"{name} 必须是 YYYY-MM-DD 或 null")
    source_id = payload.get("source_id")
    if isinstance(source_id, str) and ID_RE.fullmatch(source_id) is None:
        issues.append("source_id 必须是 [a-z0-9][a-z0-9._-]*")
    if payload.get("claim_type") not in SOURCE_CLAIM_TYPES:
        issues.append(f"claim_type 必须属于 {'、'.join(sorted(SOURCE_CLAIM_TYPES))} 之一")
    if payload.get("directness") not in SOURCE_DIRECTNESS:
        issues.append(f"directness 必须属于 {'、'.join(sorted(SOURCE_DIRECTNESS))} 之一")
    if payload.get("verifiability") not in SOURCE_VERIFIABILITY:
        issues.append(f"verifiability 必须属于 {'、'.join(sorted(SOURCE_VERIFIABILITY))} 之一")
    _string_list(payload, "supports", issues)
    _string_list(payload, "contradicts", issues)
    return issues


def _check_claim(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != CLAIM_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {CLAIM_SCHEMA_VERSION}")
    for name in ("claim_id", "statement", "last_reviewed"):
        _required_text(payload, name, issues)
    if payload.get("claim_type") not in CLAIM_TYPES:
        issues.append(f"claim_type 必须属于 {'、'.join(sorted(CLAIM_TYPES))} 之一")
    if payload.get("status") not in CLAIM_STATUSES:
        issues.append(f"status 必须属于 {'、'.join(sorted(CLAIM_STATUSES))} 之一")
    last_reviewed = payload.get("last_reviewed")
    if isinstance(last_reviewed, str) and DATE_RE.fullmatch(last_reviewed) is None:
        issues.append("last_reviewed 必须是 YYYY-MM-DD")
    _string_list(payload, "supports", issues)
    _string_list(payload, "contradicts", issues)
    _objects_list(payload, "critical_assumptions", ("assumption_id", "statement"), issues)
    _objects_list(
        payload,
        "invalidation_conditions",
        ("observable", "threshold", "horizon"),
        issues,
    )
    _objects_list(payload, "abstain_conditions", ("dimension", "reason"), issues)
    claim_id = payload.get("claim_id")
    if isinstance(claim_id, str) and ID_RE.fullmatch(claim_id) is None:
        issues.append("claim_id 必须是 [a-z0-9][a-z0-9._-]*")
    return issues


def _metric_names(payload: dict[str, Any], name: str, issues: list[str]) -> set[str]:
    metrics = payload.get(name)
    if not isinstance(metrics, list) or not metrics:
        issues.append(f"{name} 必须是非空 metric 列表")
        return set()
    seen: set[str] = set()
    for index, item in enumerate(metrics):
        if not isinstance(item, dict):
            issues.append(f"{name}[{index}] 必须是对象")
            continue
        metric_name = item.get("name")
        metric_value = item.get("value")
        if not isinstance(metric_name, str) or not metric_name.strip():
            issues.append(f"{name}[{index}].name 必须是非空字符串")
        elif metric_name in seen:
            issues.append(f"{name} metric 名称重复：{metric_name}")
        else:
            seen.add(metric_name)
        if (
            isinstance(metric_value, bool)
            or not isinstance(metric_value, (int, float))
            or not math.isfinite(float(metric_value))
        ):
            issues.append(f"{name}[{index}].value 必须是有限数值")
    return seen


def _check_counterexample(
    relative: str,
    payload: dict[str, Any],
    root: Path,
) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != COUNTEREXAMPLE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {COUNTEREXAMPLE_SCHEMA_VERSION}")
    for name in ("counterexample_id", "claim_id", "summary", "as_of"):
        _required_text(payload, name, issues)
    counterexample_id = payload.get("counterexample_id")
    if isinstance(counterexample_id, str):
        if ID_RE.fullmatch(counterexample_id) is None:
            issues.append("counterexample_id 必须是 [a-z0-9][a-z0-9._-]*")
        expected = root / "strategy-research" / "counterexamples" / f"{counterexample_id}.json"
        if root / relative != expected:
            issues.append(f"counterexample 文件名必须与 counterexample_id 一致：{expected}")
    claim_id = payload.get("claim_id")
    if isinstance(claim_id, str):
        if ID_RE.fullmatch(claim_id) is None:
            issues.append("claim_id 必须是 [a-z0-9][a-z0-9._-]*")
        claim_path = root / "strategy-research" / "judgment-ledger" / f"{claim_id}.json"
        if not claim_path.is_file():
            issues.append(f"claim_id 引用缺失：{claim_id}")
    as_of = payload.get("as_of")
    if isinstance(as_of, str) and DATE_RE.fullmatch(as_of) is None:
        issues.append("as_of 必须是 YYYY-MM-DD")
    if payload.get("scenario_type") not in COUNTEREXAMPLE_TYPES:
        issues.append(f"scenario_type 必须属于 {'、'.join(sorted(COUNTEREXAMPLE_TYPES))} 之一")
    if payload.get("status") not in COUNTEREXAMPLE_STATUSES:
        issues.append(f"status 必须属于 {'、'.join(sorted(COUNTEREXAMPLE_STATUSES))} 之一")
    if payload.get("severity") not in COUNTEREXAMPLE_SEVERITIES:
        issues.append(f"severity 必须属于 {'、'.join(sorted(COUNTEREXAMPLE_SEVERITIES))} 之一")
    dimensions = payload.get("stress_dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        issues.append("stress_dimensions 必须是非空列表")
    else:
        for index, item in enumerate(dimensions):
            if not isinstance(item, dict):
                issues.append(f"stress_dimensions[{index}] 必须是对象")
                continue
            if not isinstance(item.get("name"), str) or not item["name"].strip():
                issues.append(f"stress_dimensions[{index}].name 必须是非空字符串")
            for name in ("baseline", "stressed"):
                if name not in item:
                    issues.append(f"stress_dimensions[{index}].{name} 缺失")
                elif isinstance(item[name], (dict, list)):
                    issues.append(f"stress_dimensions[{index}].{name} 必须是 JSON 标量")
    baseline_names = _metric_names(payload, "baseline_metrics", issues)
    stressed_names = _metric_names(payload, "stressed_metrics", issues)
    if baseline_names and stressed_names and baseline_names != stressed_names:
        issues.append("baseline_metrics 与 stressed_metrics 的 metric 名称必须一致")
    for name in ("failure_conditions", "evidence_refs"):
        _string_list(payload, name, issues)
        if not payload.get(name):
            issues.append(f"{name} 必须非空")
    return issues


def _check_decision(payload: dict[str, Any], issues: list[str]) -> None:
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        issues.append("decision 必须是对象")
        return
    if decision.get("status") not in DECISION_STATUSES:
        issues.append(f"decision.status 必须属于 {'、'.join(sorted(DECISION_STATUSES))} 之一")
    _required_text(decision, "thesis", issues)


def _check_dg4(payload: dict[str, Any], issues: list[str]) -> None:
    raw_decision = payload.get("decision")
    decision = cast("dict[str, Any]", raw_decision) if isinstance(raw_decision, dict) else {}
    status = decision.get("status")
    if status == "no_view" and not payload.get("abstentions"):
        issues.append("DG4：decision.status 为 no_view 时必须填写 abstentions（维度与原因）")
    if payload.get("known_gaps") and status == "accepted":
        issues.append("DG4：known_gaps 非空时 decision.status 不得为 accepted")


def _check_dg5(payload: dict[str, Any], issues: list[str]) -> None:
    reviews = payload.get("reviews")
    if reviews is None:
        return
    if not isinstance(reviews, list):
        issues.append("reviews 必须是列表")
        return
    seen: set[str] = set()
    for index, item in enumerate(reviews):
        if not isinstance(item, dict):
            issues.append(f"reviews[{index}] 必须是对象")
            continue
        kind = item.get("kind")
        if kind not in REVIEW_KINDS:
            issues.append(f"reviews[{index}].kind 必须属于 {sorted(REVIEW_KINDS)}")
        if item.get("status") not in REVIEW_STATUSES:
            issues.append(f"reviews[{index}].status 必须属于 {sorted(REVIEW_STATUSES)}")
        if isinstance(kind, str) and kind in REVIEW_KINDS:
            seen.add(kind)
    missing = sorted(REVIEW_KINDS - seen)
    if missing:
        issues.append(f"DG5：reviews 必须同时包含 kind={missing} 的评审")


def _resolve_case_refs(
    payload: dict[str, Any],
    relative: str,
    root: Path,
    issues: list[str],
) -> None:
    case_dir = (root / relative).parent
    case_id = payload.get("case_id")
    if isinstance(case_id, str):
        expected = root / "strategy-research" / "cases" / case_id
        if case_dir != expected:
            issues.append(f"case 目录必须与 case_id 一致：{expected}")
    for claim_ref in payload.get("claims", []):
        if isinstance(claim_ref, str):
            claim_path = root / "strategy-research" / "judgment-ledger" / f"{claim_ref}.json"
            if not claim_path.is_file():
                issues.append(f"claims 引用缺失：{claim_ref}")
    for counterexample_ref in payload.get("counterexamples", []):
        if isinstance(counterexample_ref, str):
            path = root / "strategy-research" / "counterexamples" / f"{counterexample_ref}.json"
            if not path.is_file():
                issues.append(f"counterexamples 引用缺失：{counterexample_ref}")
    for review in payload.get("reviews", []):
        if isinstance(review, dict) and isinstance(review.get("file"), str):
            if not (case_dir / review["file"]).is_file():
                issues.append(f"reviews 引用缺失：{review['file']}")


def _check_case(relative: str, payload: dict[str, Any], root: Path) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != CASE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {CASE_SCHEMA_VERSION}")
    for name in ("case_id", "question", "as_of"):
        _required_text(payload, name, issues)
    as_of = payload.get("as_of")
    if isinstance(as_of, str) and DATE_RE.fullmatch(as_of) is None:
        issues.append("as_of 必须是 YYYY-MM-DD")
    case_id = payload.get("case_id")
    if isinstance(case_id, str) and ID_RE.fullmatch(case_id) is None:
        issues.append("case_id 必须是 [a-z0-9][a-z0-9._-]*")
    _check_decision(payload, issues)
    for name in (
        "research_specs",
        "claims",
        "counterexamples",
        "evidence_bundles",
        "known_gaps",
    ):
        _string_list(payload, name, issues)
    _objects_list(payload, "abstentions", ("dimension", "reason"), issues)
    _check_dg4(payload, issues)
    _check_dg5(payload, issues)
    _resolve_case_refs(payload, relative, root, issues)
    return issues


def _files(root: Path, directory: str, pattern: str) -> list[Path]:
    path = root / "strategy-research" / directory
    return sorted(path.rglob(pattern)) if path.is_dir() else []


def check_claim(path: Path, *, root: Path = ROOT) -> GovernanceCheck:
    payload = _load_json(path)
    if payload is None:
        return GovernanceCheck(str(path), ["claim.json 必须是合法 JSON 对象"])
    return GovernanceCheck(path.relative_to(root).as_posix(), _check_claim(payload))


def check_case(path: Path, *, root: Path) -> GovernanceCheck:
    payload = _load_json(path)
    if payload is None:
        return GovernanceCheck(str(path), ["case.json 必须是合法 JSON 对象"])
    relative = path.relative_to(root).as_posix()
    return GovernanceCheck(relative, _check_case(relative, payload, root))


def check_counterexample(path: Path, *, root: Path = ROOT) -> GovernanceCheck:
    payload = _load_json(path)
    if payload is None:
        return GovernanceCheck(str(path), ["counterexample.json 必须是合法 JSON 对象"])
    relative = path.relative_to(root).as_posix()
    return GovernanceCheck(relative, _check_counterexample(relative, payload, root))


def check_source(path: Path, *, root: Path = ROOT) -> GovernanceCheck:
    payload = _load_json(path)
    if payload is None:
        return GovernanceCheck(str(path), ["source.json 必须是合法 JSON 对象"])
    return GovernanceCheck(path.relative_to(root).as_posix(), _check_source(payload))


def _render(checks: list[GovernanceCheck], *, as_json: bool) -> str:
    if as_json:
        payload = {
            "schema_version": "decision_governance_check.v1",
            "manifests": [
                {"path": check.path, "ok": check.ok, "issues": check.issues} for check in checks
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines = [f"[{'OK' if check.ok else 'ERROR'}] {check.path}" for check in checks]
    lines.extend(f"  - {issue}" for check in checks for issue in check.issues)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--counterexample", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    root = args.root.resolve()
    checks: list[GovernanceCheck] = []
    if args.claim:
        checks.append(check_claim(args.claim.resolve(), root=root))
    elif args.case:
        checks.append(check_case(args.case.resolve(), root=root))
    elif args.counterexample:
        checks.append(check_counterexample(args.counterexample.resolve(), root=root))
    elif args.source:
        checks.append(check_source(args.source.resolve(), root=root))
    else:
        claim_files = _files(root, "judgment-ledger", "*.json")
        checks.extend(check_claim(path, root=root) for path in claim_files)
        checks.extend(check_case(path, root=root) for path in _files(root, "cases", "case.json"))
        checks.extend(
            check_counterexample(path, root=root)
            for path in _files(root, "counterexamples", "*.json")
        )
        checks.extend(check_source(path, root=root) for path in _files(root, "sources", "*.json"))
    print(_render(checks, as_json=args.as_json))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
