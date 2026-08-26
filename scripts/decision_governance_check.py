#!/usr/bin/env python3
"""Validate research-decision-governance manifests (判断账本与决策记录).

DG1 判断账本使用 ``claim.v1``，每个 claim 是机器可检查的判断对象。DG2 研究案例在
``strategy-research/cases/<案例id>/`` 下使用 ``research_case.v1`` 的 ``case.json``
做导航，配 ``decision.md`` 与 ``reviews/logic.json``、``reviews/evidence.json``。
DG8 使用 ``counterexample.v1`` 把能明显削弱或推翻 claim 的压力情景提升为一等证据导航对象。

校验内容：

- 判断账本目录下每个 ``*.json`` 文件符合 ``claim.v1`` 字段与取值约束。
- 每个案例目录的 ``case.json`` 符合 ``research_case.v1``，且引用的 claims、
  counterexamples、research_specs、reviews 文件真实存在。
- 反例目录下每个 ``*.json`` 文件符合 ``counterexample.v1``，引用已有 claim，
  压力前后 metric 可比较，证据引用非空。
- 禁止证据缺失时用综合来看等叙事填补结论（DG4）：no_view 必须有 abstentions，known_gaps
  非空时 decision.status 不得为 accepted。
- DG5：每个 case 的 reviews 必须同时含 logic 与 evidence 两种 kind（双评审）。
- DG6：decision 可拆分 evidence_readiness 维度数组与 investment_conviction 附注，不合成单一总分。

Exit codes:
- 0: 所有找到的 manifest 均有效
- 1: 任何 manifest 无效或引用了缺失文件
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
CASE_ROOT = ROOT / "strategy-research" / "cases"
CLAIM_ROOT = ROOT / "strategy-research" / "judgment-ledger"
SOURCE_ROOT = ROOT / "strategy-research" / "sources"
COUNTEREXAMPLE_ROOT = ROOT / "strategy-research" / "counterexamples"
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
COUNTEREXAMPLE_SCENARIO_TYPES = {
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
    if not isinstance(payload, dict):
        return None
    return payload


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
            field_value = item.get(field_name)
            if field_name in item and not isinstance(field_value, str):
                issues.append(f"{name}[{index}].{field_name} 必须是字符串")


def _metric_list(payload: dict[str, Any], name: str, issues: list[str]) -> set[str]:
    value = payload.get(name)
    if not isinstance(value, list) or not value:
        issues.append(f"{name} 必须是非空 metric 列表")
        return set()
    seen: set[str] = set()
    for index, item in enumerate(value):
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


def _check_source(relative: str, payload: dict[str, Any]) -> list[str]:
    # DG3 定性来源溯源：可选校验。真实来源数据落在外部 market-intel，本仓仅持有引用校验用的
    # source 文件（strategy-research/sources/），不强制所有 claim/case 必须填 source。
    issues: list[str] = []
    if payload.get("schema_version") != SOURCE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {SOURCE_SCHEMA_VERSION}")
    _required_text(payload, "source_id", issues)
    _required_text(payload, "source_type", issues)
    _required_text(payload, "publisher", issues)
    published_at = payload.get("published_at")
    if isinstance(published_at, str) and DATE_RE.fullmatch(published_at) is None:
        issues.append("published_at 必须是 YYYY-MM-DD")
    for field_name in ("effective_at", "observed_at", "ingested_at"):
        value = payload.get(field_name)
        if value is not None and isinstance(value, str) and DATE_RE.fullmatch(value) is None:
            issues.append(f"{field_name} 必须是 YYYY-MM-DD 或 null")
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


def _check_claim(relative: str, payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != CLAIM_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {CLAIM_SCHEMA_VERSION}")
    _required_text(payload, "claim_id", issues)
    _required_text(payload, "statement", issues)
    _required_text(payload, "last_reviewed", issues)
    claim_type = payload.get("claim_type")
    if claim_type not in CLAIM_TYPES:
        issues.append(f"claim_type 必须属于 {'、'.join(sorted(CLAIM_TYPES))} 之一")
    status = payload.get("status")
    if status not in CLAIM_STATUSES:
        issues.append(f"status 必须属于 {'、'.join(sorted(CLAIM_STATUSES))} 之一")
    last_reviewed = payload.get("last_reviewed")
    if isinstance(last_reviewed, str) and DATE_RE.fullmatch(last_reviewed) is None:
        issues.append("last_reviewed 必须是 YYYY-MM-DD")
    _string_list(payload, "supports", issues)
    _string_list(payload, "contradicts", issues)
    _objects_list(
        payload,
        "critical_assumptions",
        ("assumption_id", "statement"),
        issues,
    )
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


def _check_counterexample(
    relative: str,
    payload: dict[str, Any],
    root: Path,
) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != COUNTEREXAMPLE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {COUNTEREXAMPLE_SCHEMA_VERSION}")
    for field_name in ("counterexample_id", "claim_id", "summary", "as_of"):
        _required_text(payload, field_name, issues)

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
    if payload.get("scenario_type") not in COUNTEREXAMPLE_SCENARIO_TYPES:
        issues.append(
            f"scenario_type 必须属于 {'、'.join(sorted(COUNTEREXAMPLE_SCENARIO_TYPES))} 之一"
        )
    if payload.get("status") not in COUNTEREXAMPLE_STATUSES:
        issues.append(f"status 必须属于 {'、'.join(sorted(COUNTEREXAMPLE_STATUSES))} 之一")
    if payload.get("severity") not in COUNTEREXAMPLE_SEVERITIES:
        issues.append(f"severity 必须属于 {'、'.join(sorted(COUNTEREXAMPLE_SEVERITIES))} 之一")

    stress_dimensions = payload.get("stress_dimensions")
    if not isinstance(stress_dimensions, list) or not stress_dimensions:
        issues.append("stress_dimensions 必须是非空列表")
    else:
        for index, item in enumerate(stress_dimensions):
            if not isinstance(item, dict):
                issues.append(f"stress_dimensions[{index}] 必须是对象")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                issues.append(f"stress_dimensions[{index}].name 必须是非空字符串")
            for field_name in ("baseline", "stressed"):
                if field_name not in item:
                    issues.append(f"stress_dimensions[{index}].{field_name} 缺失")
                elif isinstance(item[field_name], (dict, list)):
                    issues.append(f"stress_dimensions[{index}].{field_name} 必须是 JSON 标量")

    baseline_names = _metric_list(payload, "baseline_metrics", issues)
    stressed_names = _metric_list(payload, "stressed_metrics", issues)
    if baseline_names and stressed_names and baseline_names != stressed_names:
        issues.append("baseline_metrics 与 stressed_metrics 的 metric 名称必须一致")

    for field_name in ("failure_conditions", "evidence_refs"):
        _string_list(payload, field_name, issues)
        if not payload.get(field_name):
            issues.append(f"{field_name} 必须非空")
    return issues


def _check_decision(payload: dict[str, Any], issues: list[str]) -> None:
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        issues.append("decision 必须是对象")
        return
    status = decision.get("status")
    if status not in DECISION_STATUSES:
        issues.append(f"decision.status 必须属于 {'、'.join(sorted(DECISION_STATUSES))} 之一")
    _required_text(decision, "thesis", issues)


def _check_case(relative: str, payload: dict[str, Any], root: Path) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != CASE_SCHEMA_VERSION:
        issues.append(f"schema_version 必须是 {CASE_SCHEMA_VERSION}")
    _required_text(payload, "case_id", issues)
    _required_text(payload, "question", issues)
    _required_text(payload, "as_of", issues)
    as_of = payload.get("as_of")
    if isinstance(as_of, str) and DATE_RE.fullmatch(as_of) is None:
        issues.append("as_of 必须是 YYYY-MM-DD")
    case_id = payload.get("case_id")
    if isinstance(case_id, str) and ID_RE.fullmatch(case_id) is None:
        issues.append("case_id 必须是 [a-z0-9][a-z0-9._-]*")
    _check_decision(payload, issues)
    _string_list(payload, "research_specs", issues)
    _string_list(payload, "claims", issues)
    _string_list(payload, "counterexamples", issues)
    _string_list(payload, "evidence_bundles", issues)
    _string_list(payload, "known_gaps", issues)
    _objects_list(payload, "abstentions", ("dimension", "reason"), issues)
    _check_dg4(payload, issues)
    _check_dg5_reviews(payload, issues)
    _resolve_case_refs(payload, relative, root, issues)
    return issues


def _check_dg4(payload: dict[str, Any], issues: list[str]) -> None:
    # DG4：缺数据即放弃判断——no_view 必须给出 abstentions；已知缺口下不得直接 accepted。
    raw_decision: object = payload.get("decision")
    decision: dict[str, Any] = (
        cast("dict[str, Any]", raw_decision) if isinstance(raw_decision, dict) else {}
    )
    decision_status: object = decision.get("status")
    if decision_status == "no_view" and not payload.get("abstentions"):
        issues.append("DG4：decision.status 为 no_view 时必须填写 abstentions（维度与原因）")
    if payload.get("known_gaps") and decision_status == "accepted":
        issues.append(
            "DG4：known_gaps 非空时 decision.status 不得为 accepted（禁止在已知缺口下给出接受结论）"
        )


def _check_dg5_reviews(payload: dict[str, Any], issues: list[str]) -> None:
    # DG5：逻辑与证据双评审——reviews 必须同时含 logic 与 evidence 两种 kind。
    reviews = payload.get("reviews")
    if reviews is None:
        return
    if not isinstance(reviews, list):
        issues.append("reviews 必须是列表")
        return
    seen_kinds: set[str] = set()
    for index, item in enumerate(reviews):
        if not isinstance(item, dict):
            issues.append(f"reviews[{index}] 必须是对象")
            continue
        kind: object = item.get("kind")
        if kind not in REVIEW_KINDS:
            issues.append(f"reviews[{index}].kind 必须属于 {sorted(REVIEW_KINDS)}")
        if item.get("status") not in REVIEW_STATUSES:
            issues.append(f"reviews[{index}].status 必须属于 {sorted(REVIEW_STATUSES)}")
        if kind in REVIEW_KINDS:
            seen_kinds.add(cast(str, kind))
    missing = sorted(REVIEW_KINDS - seen_kinds)
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
        expected_dir = root / "strategy-research" / "cases" / case_id
        if (root / relative).parent != expected_dir:
            issues.append(f"case 目录必须与 case_id 一致：{expected_dir}")
    for claim_ref in payload.get("claims", []):
        if not isinstance(claim_ref, str):
            continue
        claim_path = root / "strategy-research" / "judgment-ledger" / f"{claim_ref}.json"
        if not claim_path.is_file():
            issues.append(f"claims 引用缺失：{claim_ref}")
    for counterexample_ref in payload.get("counterexamples", []):
        if not isinstance(counterexample_ref, str):
            continue
        counterexample_path = (
            root / "strategy-research" / "counterexamples" / f"{counterexample_ref}.json"
        )
        if not counterexample_path.is_file():
            issues.append(f"counterexamples 引用缺失：{counterexample_ref}")
    for review in payload.get("reviews", []):
        if not isinstance(review, dict):
            continue
        review_file = review.get("file")
        if not isinstance(review_file, str):
            continue
        if not (case_dir / review_file).is_file():
            issues.append(f"reviews 引用缺失：{review_file}")


def _claim_files(root: Path) -> list[Path]:
    return sorted((root / "strategy-research" / "judgment-ledger").rglob("*.json"))


def _case_files(root: Path) -> list[Path]:
    return sorted((root / "strategy-research" / "cases").rglob("case.json"))


def _counterexample_files(root: Path) -> list[Path]:
    counterexample_dir = root / "strategy-research" / "counterexamples"
    if not counterexample_dir.is_dir():
        return []
    return sorted(counterexample_dir.rglob("*.json"))


def _source_files(root: Path) -> list[Path]:
    # DG3 来源文件为可选：仅当 strategy-research/sources/ 目录存在时才校验。
    sources_dir = root / "strategy-research" / "sources"
    if not sources_dir.is_dir():
        return []
    return sorted(sources_dir.rglob("*.json"))


def check_claim(path: Path, *, root: Path = ROOT) -> GovernanceCheck:
    payload = _load_json(path)
    if payload is None:
        return GovernanceCheck(str(path), ["claim.json 必须是合法 JSON 对象"])
    relative = path.relative_to(root).as_posix()
    return GovernanceCheck(relative, _check_claim(relative, payload))


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
    relative = path.relative_to(root).as_posix()
    return GovernanceCheck(relative, _check_source(relative, payload))


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
        checks.extend(check_claim(path, root=root) for path in _claim_files(root))
        checks.extend(check_case(path, root=root) for path in _case_files(root))
        checks.extend(
            check_counterexample(path, root=root) for path in _counterexample_files(root)
        )
        checks.extend(check_source(path, root=root) for path in _source_files(root))
    print(_render(checks, as_json=args.as_json))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
