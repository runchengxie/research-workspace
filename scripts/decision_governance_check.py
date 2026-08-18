#!/usr/bin/env python3
"""Validate research-decision-governance manifests (判断账本与决策记录).

DG1 判断账本使用 ``claim.v1``，每个 claim 是机器可检查的判断对象。DG2 研究案例在
``strategy-research/cases/<案例id>/`` 下使用 ``research_case.v1`` 的 ``case.json``
做导航，配 ``decision.md`` 与 ``reviews/logic.json``、``reviews/evidence.json``。

校验内容：

- 判断账本目录下每个 ``*.json`` 文件符合 ``claim.v1`` 字段与取值约束。
- 每个案例目录的 ``case.json`` 符合 ``research_case.v1``，且引用的 claims、
  research_specs、reviews 文件真实存在。
- 禁止证据缺失时用综合来看等叙事填补结论，DG4 语义保留为对决策记录 review 的提示，
  不强制所有 case 的 decision.status 非 no_view。

Exit codes:
- 0: 所有找到的 manifest 均有效
- 1: 任何 manifest 无效或引用了缺失文件
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = ROOT / "strategy-research" / "cases"
CLAIM_ROOT = ROOT / "strategy-research" / "judgment-ledger"
CLAIM_SCHEMA_VERSION = "claim.v1"
CASE_SCHEMA_VERSION = "research_case.v1"
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
CLAIM_TYPES = {"hypothesis", "fact", "estimate", "inference"}
CLAIM_STATUSES = {"active", "proposed", "superseded", "rejected"}
DECISION_STATUSES = {"no_view", "provisional", "accepted", "rejected"}
REVIEW_KINDS = {"logic", "evidence"}
REVIEW_STATUSES = {"completed", "in_progress", "pending"}


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
            if field_name in item and not isinstance(item[field_name], str):
                issues.append(f"{name}[{index}].{field_name} 必须是字符串")


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
    _string_list(payload, "evidence_bundles", issues)
    _string_list(payload, "known_gaps", issues)
    _objects_list(payload, "abstentions", ("dimension", "reason"), issues)
    reviews = payload.get("reviews")
    if reviews is not None:
        if not isinstance(reviews, list):
            issues.append("reviews 必须是列表")
        else:
            for index, item in enumerate(reviews):
                if not isinstance(item, dict):
                    issues.append(f"reviews[{index}] 必须是对象")
                    continue
                if item.get("kind") not in REVIEW_KINDS:
                    issues.append(f"reviews[{index}].kind 必须属于 {sorted(REVIEW_KINDS)}")
                if item.get("status") not in REVIEW_STATUSES:
                    issues.append(f"reviews[{index}].status 必须属于 {sorted(REVIEW_STATUSES)}")
    _resolve_case_refs(payload, relative, root, issues)
    return issues


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
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    root = args.root.resolve()
    checks: list[GovernanceCheck] = []
    if args.claim:
        checks.append(check_claim(args.claim.resolve()))
    elif args.case:
        checks.append(check_case(args.case.resolve(), root=root))
    else:
        checks.extend(check_claim(path, root=root) for path in _claim_files(root))
        checks.extend(check_case(path, root=root) for path in _case_files(root))
    print(_render(checks, as_json=args.as_json))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
