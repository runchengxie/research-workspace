#!/usr/bin/env python3
"""Read-only maintainability governance checks for the workspace."""

from __future__ import annotations

import ast
import json
from pathlib import Path, PurePosixPath
from typing import Any, TypeGuard

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
    "docs/compatibility-facades.yml": "compatibility_facades.v2",
    "docs/quality-coverage-governance.yml": "quality_coverage_governance.v1",
    "docs/maintainability-refactor-roadmap.yml": "maintainability_refactor_roadmap.v1",
    "docs/evidence/maintainability/baseline-20260719-ty.json": "maintainability_baseline.v1",
}
SCRIPT_LIFECYCLE_ROOTS = (
    "scripts",
    "alpha-research/scripts",
    "strategy-pipeline/scripts/internal",
    "market-data-platform/scripts/internal",
    "portfolio-backtester/scripts",
    "quant-execution-engine/project_tools",
)
SCRIPT_LIFECYCLE_SUFFIXES = {".py", ".sh"}
SCRIPT_LIFECYCLE_EXTRA_PATHS = {
    "src/research_contracts/a_share_readiness.py",
    "src/research_contracts/a_share_readiness_common.py",
    "src/research_contracts/a_share_readiness_contract.py",
    "src/research_contracts/a_share_readiness_evidence.py",
    "src/research_contracts/smoke_contracts.py",
    "src/style_factors/style_factor_attribution.py",
}
DEPRECATION_BUDGET_FIELDS = {"pending_follow_up_max", "policy"}
DEPRECATION_PENDING_STATUSES = {"blocked_pending_audit", "follow_up_required"}
COMPATIBILITY_FACADE_COMMON_FIELDS = {
    "owner_repo",
    "kind",
    "replacement",
    "current_consumers",
    "removal_condition",
    "rollback_path",
    "focused_tests",
    "consumer_audit",
    "status",
}
COMPATIBILITY_FACADE_ROOTS = (
    "alpha-research/src",
    "portfolio-backtester/src",
    "strategy-pipeline/src",
    "market-data-platform/src",
    "quant-execution-engine/src",
)
COMPATIBILITY_FACADE_MARKERS = (
    "facade",
    "Compatibility wrapper",
    "Backward-compatible",
    "backward-compatible",
)
COMPATIBILITY_FACADE_GLOB_MARKERS = frozenset("*?[]{}")
HOTSPOT_COUNT_FIELDS = {
    "large_files",
    "long_functions",
    "complexity_hotspots",
    "large_classes",
}
HOTSPOT_BUDGET_FIELDS = {f"max_{field}" for field in HOTSPOT_COUNT_FIELDS}


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
    for relative_path in SCRIPT_LIFECYCLE_EXTRA_PATHS:
        if (root / relative_path).is_file():
            paths.add(relative_path)
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


def _valid_budget_limit(value: Any) -> TypeGuard[int]:
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
            paths.add(_workspace_relative_path(repo_name, relative))
    return paths


def _workspace_relative_path(repo_name: str, relative: str) -> str:
    return relative if repo_name == "research-workspace" else f"{repo_name}/{relative}"


def _baseline_large_class_paths(baseline: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for repo in baseline.get("repos", []):
        if not isinstance(repo, dict):
            continue
        repo_name = str(repo.get("repo", ""))
        for class_record in repo.get("large_classes", []):
            if not isinstance(class_record, dict):
                continue
            relative = str(class_record.get("path", "")).strip()
            if relative:
                paths.add(_workspace_relative_path(repo_name, relative))
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


def _has_star_import(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    return any(
        isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
        for node in ast.walk(tree)
    )


def _tracked_compatibility_facade_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for relative_root in COMPATIBILITY_FACADE_ROOTS:
        source_root = root / relative_root
        if not source_root.is_dir():
            continue
        for path in source_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                head = path.read_text(encoding="utf-8", errors="ignore")[:500]
            except OSError:
                continue
            if any(marker in head for marker in COMPATIBILITY_FACADE_MARKERS) or _has_star_import(
                path
            ):
                paths.add(path.relative_to(root).as_posix())
    return paths


def _is_concrete_facade_path(value: Any) -> TypeGuard[str]:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and path.as_posix() == value
        and ".." not in path.parts
        and not COMPATIBILITY_FACADE_GLOB_MARKERS.intersection(value)
    )


def _compatibility_facade_record_paths(
    record: dict[str, Any], label: str
) -> tuple[list[str], list[str]]:
    has_path = "path" in record
    has_paths = "paths" in record
    if has_path == has_paths:
        return [], [f"{label}: exactly one of path or paths is required"]

    raw_paths = record["paths"] if has_paths else [record["path"]]
    if not isinstance(raw_paths, list) or not raw_paths:
        return [], [f"{label}: paths must be a non-empty list"]

    issues: list[str] = []
    paths: list[str] = []
    for index, value in enumerate(raw_paths):
        if not _is_concrete_facade_path(value):
            issues.append(f"{label}: path[{index}] must be a concrete workspace-relative file")
            continue
        paths.append(value)
    if len(paths) != len(set(paths)):
        issues.append(f"{label}: paths must be unique")
    return paths, issues


def _compatibility_facade_common_issues(record: dict[str, Any], label: str) -> list[str]:
    issues: list[str] = []
    missing_fields = sorted(COMPATIBILITY_FACADE_COMMON_FIELDS - set(record))
    if missing_fields:
        issues.append(f"{label}: missing fields {', '.join(missing_fields)}")
    focused_tests = record.get("focused_tests")
    if not isinstance(focused_tests, list) or not focused_tests:
        issues.append(f"{label}: focused_tests must be non-empty")
    for field in COMPATIBILITY_FACADE_COMMON_FIELDS - {"focused_tests"}:
        if not str(record.get(field, "")).strip():
            issues.append(f"{label}: {field} must be non-empty")
    return issues


def _check_compatibility_facades(root: Path, manifest: dict[str, Any]) -> list[Check]:
    raw_records = manifest.get("records", [])
    issues: list[str] = []
    if not isinstance(raw_records, list):
        raw_records = []
        issues.append("records must be a list")
    records = [record for record in raw_records if isinstance(record, dict)]
    invalid_record_indexes = [
        str(index) for index, record in enumerate(raw_records) if not isinstance(record, dict)
    ]
    if invalid_record_indexes:
        issues.append(
            "records must contain objects at indexes " + ", ".join(invalid_record_indexes)
        )
    record_paths: set[str] = set()
    path_records: dict[str, list[str]] = {}
    tracked_paths = _tracked_compatibility_facade_paths(root)

    for index, record in enumerate(records):
        label = str(record.get("id", f"record[{index}]"))
        paths, path_issues = _compatibility_facade_record_paths(record, label)
        issues.extend(path_issues)
        issues.extend(_compatibility_facade_common_issues(record, label))
        for path in paths:
            record_paths.add(path)
            path_records.setdefault(path, []).append(label)
            if not (root / path).is_file():
                issues.append(f"{label}: {path}: file missing")

    duplicate_paths = sorted(path for path, labels in path_records.items() if len(labels) > 1)
    if duplicate_paths:
        issues.append("multiply-registered=" + ", ".join(duplicate_paths))
    missing = sorted(tracked_paths - record_paths)
    stale = sorted(record_paths - tracked_paths)
    if missing:
        issues.append("unregistered=" + ", ".join(missing))
    if stale:
        issues.append("stale=" + ", ".join(stale))

    if issues:
        return [
            Check(
                "ERROR",
                "governance-compatibility-facades",
                "Compatibility facade governance drift: " + "; ".join(issues),
            )
        ]
    return [
        Check(
            "OK",
            "governance-compatibility-facades",
            f"Compatibility facade register covers {len(tracked_paths)} detected facades.",
        )
    ]


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
    uncovered = sorted(
        (_baseline_large_file_paths(baseline) | _baseline_large_class_paths(baseline))
        - planned
        - accepted
    )
    budget_records = {
        str(record.get("repo", "")): record
        for record in roadmap.get("hotspot_budgets", [])
        if isinstance(record, dict)
    }
    budget_issues: list[str] = []
    for repo in baseline.get("repos", []):
        if not isinstance(repo, dict):
            continue
        repo_name = str(repo.get("repo", ""))
        budget = budget_records.get(repo_name)
        if not isinstance(budget, dict):
            budget_issues.append(f"{repo_name}: missing hotspot budget")
            continue
        missing_fields = sorted(HOTSPOT_BUDGET_FIELDS - set(budget))
        if missing_fields:
            budget_issues.append(f"{repo_name}: missing budget fields {', '.join(missing_fields)}")
            continue
        counts = repo.get("hotspot_counts", {})
        if not isinstance(counts, dict):
            budget_issues.append(f"{repo_name}: missing hotspot counts")
            continue
        for field in sorted(HOTSPOT_COUNT_FIELDS):
            count = counts.get(field)
            limit = budget.get(f"max_{field}")
            if not _valid_budget_limit(count):
                budget_issues.append(f"{repo_name}: invalid {field} count")
            elif not _valid_budget_limit(limit):
                budget_issues.append(f"{repo_name}: invalid max_{field} budget")
            elif count > limit:
                budget_issues.append(f"{repo_name}: {field} count {count} exceeds budget {limit}")
            elif count < limit:
                budget_issues.append(
                    f"{repo_name}: {field} budget {limit} is loose; lower it to {count}"
                )
    baseline_repos = {
        str(repo.get("repo", "")) for repo in baseline.get("repos", []) if isinstance(repo, dict)
    }
    stale_budget_repos = sorted(set(budget_records) - baseline_repos)
    for repo_name in stale_budget_repos:
        budget_issues.append(f"{repo_name}: stale hotspot budget")

    checks: list[Check] = []
    if uncovered:
        checks.append(
            Check(
                "ERROR",
                "governance-refactor-roadmap",
                "Baseline large files/classes missing roadmap decision: " + ", ".join(uncovered),
            )
        )
    if budget_issues:
        checks.append(
            Check(
                "ERROR",
                "governance-refactor-roadmap",
                "Hotspot budget drift: " + "; ".join(budget_issues),
            )
        )
    if checks:
        return checks
    return [
        Check(
            "OK",
            "governance-refactor-roadmap",
            "Baseline large files/classes have decisions and hotspot budgets are tight.",
        )
    ]


def check_maintainability_governance(root: Path) -> list[Check]:
    checks, docs = _load_governance_docs(root)

    if deprecations := docs.get("docs/deprecations.yml"):
        checks.extend(_check_deprecations(deprecations))
    if lifecycle := docs.get("docs/script-lifecycle.yml"):
        checks.extend(_check_script_lifecycle(root, lifecycle))
    if facades := docs.get("docs/compatibility-facades.yml"):
        checks.extend(_check_compatibility_facades(root, facades))
    checks.extend(check_submodule_governance_gates(root))
    if quality := docs.get("docs/quality-coverage-governance.yml"):
        checks.extend(check_quality_coverage(root, quality))

    roadmap = docs.get("docs/maintainability-refactor-roadmap.yml")
    baseline = docs.get("docs/evidence/maintainability/baseline-20260719-ty.json")
    if roadmap and baseline:
        checks.extend(_check_refactor_roadmap(roadmap, baseline))

    return checks
