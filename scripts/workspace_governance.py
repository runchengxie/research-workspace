#!/usr/bin/env python3
"""Read-only maintainability governance checks for the workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workspace_governance_common import Check
from workspace_governance_quality import check_quality_coverage
from workspace_governance_submodules import check_submodule_governance_gates

__all__ = [
    "Check",
    "check_maintainability_governance",
    "check_submodule_governance_gates",
]

GOVERNANCE_DOC_SCHEMAS = {
    "docs/deprecations.yml": "deprecation_register.v1",
    "docs/script-lifecycle.yml": "script_lifecycle.v1",
    "docs/quality-coverage-governance.yml": "quality_coverage_governance.v1",
    "docs/maintainability-refactor-roadmap.yml": "maintainability_refactor_roadmap.v1",
    "docs/evidence/maintainability/baseline-20260617.json": "maintainability_baseline.v1",
}
SCRIPT_LIFECYCLE_ROOTS = (
    "scripts",
    "cross-sectional-trees/scripts/internal",
    "market-data-platform/scripts/internal",
    "quant-execution-engine/project_tools",
)
SCRIPT_LIFECYCLE_SUFFIXES = {".py", ".sh"}
DEPRECATION_BUDGET_FIELDS = {"pending_follow_up_max", "policy"}
DEPRECATION_PENDING_STATUSES = {"blocked_pending_audit", "follow_up_required"}


def _load_json_doc(root: Path, relative: str) -> tuple[dict[str, Any] | None, Check | None]:
    path = root / relative
    if not path.is_file():
        return None, Check("ERROR", "governance-docs", f"Missing {relative}.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, Check("ERROR", "governance-docs", f"Invalid JSON subset in {relative}: {exc}")
    if not isinstance(payload, dict):
        return None, Check("ERROR", "governance-docs", f"{relative} must contain an object.")
    return payload, None


def _tracked_script_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for relative_root in SCRIPT_LIFECYCLE_ROOTS:
        script_root = root / relative_root
        if not script_root.is_dir():
            continue
        for path in script_root.rglob("*"):
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
                continue
            if path.is_file() and path.suffix in SCRIPT_LIFECYCLE_SUFFIXES:
                paths.add(path.relative_to(root).as_posix())
    return paths


def _deprecation_removal_issues(manifest: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for record in manifest.get("records", []):
        if not isinstance(record, dict) or record.get("status") != "removal_ready":
            continue
        identifier = str(record.get("id", "<unknown>"))
        consumer_audit = str(record.get("consumer_audit", "")).lower()
        if consumer_audit in {"", "pending", "manual_review_required"}:
            issues.append(f"{identifier}: consumer_audit")
        if not record.get("replacement_docs"):
            issues.append(f"{identifier}: replacement_docs")
        if not record.get("rollback_path"):
            issues.append(f"{identifier}: rollback_path")
        if not record.get("focused_tests"):
            issues.append(f"{identifier}: focused_tests")
        if record.get("restore_evidence_required") and not record.get("restore_evidence"):
            issues.append(f"{identifier}: restore_evidence")
    return issues


def _valid_budget_limit(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _check_deprecation_budget(manifest: dict[str, Any], pending_count: int) -> list[Check]:
    budget = manifest.get("deprecation_budget")
    if not isinstance(budget, dict):
        return [
            Check(
                "ERROR",
                "governance-deprecations",
                "Deprecation budget is missing or invalid.",
            )
        ]
    if not DEPRECATION_BUDGET_FIELDS <= set(budget):
        return [
            Check(
                "ERROR",
                "governance-deprecations",
                "Deprecation budget is missing fields: "
                + ", ".join(sorted(DEPRECATION_BUDGET_FIELDS - set(budget))),
            )
        ]

    limit = budget["pending_follow_up_max"]
    policy = budget["policy"]
    issues: list[str] = []
    if not _valid_budget_limit(limit):
        issues.append("pending_follow_up_max must be a non-negative integer")
    elif pending_count > limit:
        issues.append(f"pending deprecated surface count {pending_count} exceeds max {limit}")
    if not isinstance(policy, str) or not policy.strip():
        issues.append("policy must be a non-empty string")
    if issues:
        return [
            Check(
                "ERROR",
                "governance-deprecations",
                "Deprecation budget violation: " + "; ".join(issues),
            )
        ]

    return [
        Check(
            "OK",
            "governance-deprecations",
            f"Deprecation budget holds: pending_follow_up={pending_count}/{limit}.",
        )
    ]


def _baseline_large_file_paths(baseline: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for repo in baseline.get("repos", []):
        if not isinstance(repo, dict):
            continue
        repo_name = str(repo.get("repo", ""))
        for file_record in repo.get("large_files", []):
            if not isinstance(file_record, dict):
                continue
            relative = str(file_record.get("path", "")).strip()
            if not relative:
                continue
            if repo_name == "research-workspace":
                paths.add(relative)
            else:
                paths.add(f"{repo_name}/{relative}")
    return paths


def _load_governance_docs(root: Path) -> tuple[list[Check], dict[str, dict[str, Any]]]:
    checks: list[Check] = []
    docs: dict[str, dict[str, Any]] = {}
    for relative, expected_schema in GOVERNANCE_DOC_SCHEMAS.items():
        payload, error = _load_json_doc(root, relative)
        if error:
            checks.append(error)
            continue
        assert payload is not None
        actual_schema = payload.get("schema_version")
        if actual_schema != expected_schema:
            checks.append(
                Check(
                    "ERROR",
                    "governance-docs",
                    f"{relative} schema_version={actual_schema!r}; expected {expected_schema}.",
                )
            )
            continue
        docs[relative] = payload

    if len(docs) == len(GOVERNANCE_DOC_SCHEMAS):
        checks.append(Check("OK", "governance-docs", "Maintainability governance docs parse."))
    return checks, docs


def _check_deprecations(manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    issues = _deprecation_removal_issues(manifest)
    if issues:
        checks.append(
            Check(
                "ERROR",
                "governance-deprecations",
                "Deprecation records marked removal_ready without evidence: " + "; ".join(issues),
            )
        )
    else:
        checks.append(
            Check("OK", "governance-deprecations", "Deprecation removal gates are guarded.")
        )
    pending = [
        str(record.get("id", "<unknown>"))
        for record in manifest.get("records", [])
        if isinstance(record, dict) and record.get("status") in DEPRECATION_PENDING_STATUSES
    ]
    if pending:
        checks.append(
            Check(
                "WARN",
                "governance-deprecations",
                f"Registered deprecated surfaces still need follow-up: {len(pending)}.",
            )
        )
    checks.extend(_check_deprecation_budget(manifest, len(pending)))
    return checks


def _check_script_lifecycle(root: Path, manifest: dict[str, Any]) -> list[Check]:
    records = {
        str(record.get("path", ""))
        for record in manifest.get("records", [])
        if isinstance(record, dict)
    }
    actual_paths = _tracked_script_paths(root)
    missing = sorted(actual_paths - records)
    stale = sorted(records - actual_paths)
    if missing or stale:
        detail = []
        if missing:
            detail.append("unclassified=" + ", ".join(missing))
        if stale:
            detail.append("stale=" + ", ".join(stale))
        return [
            Check(
                "ERROR",
                "governance-script-lifecycle",
                "Script lifecycle manifest drift: " + "; ".join(detail),
            )
        ]
    return [
        Check(
            "OK",
            "governance-script-lifecycle",
            f"Script lifecycle classifies {len(actual_paths)} tracked scripts.",
        )
    ]


def _check_refactor_roadmap(roadmap: dict[str, Any], baseline: dict[str, Any]) -> list[Check]:
    planned = {
        str(record.get("path", ""))
        for record in roadmap.get("records", [])
        if isinstance(record, dict)
    }
    accepted = {
        str(record.get("path", ""))
        for record in roadmap.get("accepted_hotspots", [])
        if isinstance(record, dict)
    }
    uncovered = sorted(_baseline_large_file_paths(baseline) - planned - accepted)
    if uncovered:
        return [
            Check(
                "ERROR",
                "governance-refactor-roadmap",
                "Baseline large files missing roadmap decision: " + ", ".join(uncovered),
            )
        ]
    return [
        Check(
            "OK",
            "governance-refactor-roadmap",
            "Baseline large files have planned or accepted roadmap decisions.",
        )
    ]


def check_maintainability_governance(root: Path) -> list[Check]:
    checks, docs = _load_governance_docs(root)

    if deprecations := docs.get("docs/deprecations.yml"):
        checks.extend(_check_deprecations(deprecations))
    if lifecycle := docs.get("docs/script-lifecycle.yml"):
        checks.extend(_check_script_lifecycle(root, lifecycle))
    checks.extend(check_submodule_governance_gates(root))
    if quality := docs.get("docs/quality-coverage-governance.yml"):
        checks.extend(check_quality_coverage(root, quality))

    roadmap = docs.get("docs/maintainability-refactor-roadmap.yml")
    baseline = docs.get("docs/evidence/maintainability/baseline-20260617.json")
    if roadmap and baseline:
        checks.extend(_check_refactor_roadmap(roadmap, baseline))

    return checks
