"""HK public split coverage checks for workspace governance."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from workspace_governance_common import Check

HK_PUBLIC_SPLIT_REQUIRED_IDS = {
    "market-data-platform-hk-assets-and-depth",
    "market-data-platform-legacy-hk-entrypoints",
    "strategy-research-hk-allocation-compat",
    "strategy-research-hk-configs",
    "execution-longport-runtime",
    "top-level-hk-public-demo-staging",
    "top-level-hk-research-lane-template",
}
HK_SPLIT_SCAN_ROOTS = (
    "docs",
    "scripts",
    "demo",
    "market-data-platform",
    "strategy-pipeline",
    "quant-execution-engine",
)
HK_SPLIT_MARKER_RE = re.compile(
    r"(^|/|_)(hk)(_|-|/|\.|$)"
    r"|longport|rqdata-hk|hkdata|hk_assets|hk_depth|hk_data_platform|alloc_hk|alloc-hk",
    re.IGNORECASE,
)
HK_SPLIT_IGNORE_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "outputs",
}
HK_SPLIT_FOLLOW_UP_BUDGET_FIELDS = {"blocked_or_follow_up_records_max", "policy"}
HK_SPLIT_PENDING_STATUSES = {"blocked_pending_audit", "follow_up_required"}


def _ready_split_gate_issues(manifest: dict[str, Any]) -> list[str]:
    required_fields = manifest.get("deletion_gate_requirements", [])
    if not isinstance(required_fields, list):
        return ["deletion_gate_requirements must be a list"]

    issues: list[str] = []
    blocked_values = {"", "pending", "manual_review_required", "follow_up_required"}
    for record in manifest.get("records", []):
        if not isinstance(record, dict):
            continue
        gate = record.get("deletion_gate", {})
        if not isinstance(gate, dict) or gate.get("status") != "ready":
            continue
        identifier = str(record.get("id", "<unknown>"))
        for field in required_fields:
            value = str(gate.get(str(field), "")).strip().lower()
            if value in blocked_values:
                issues.append(f"{identifier}: {field}")
    return issues


def _valid_budget_limit(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _check_follow_up_budget(manifest: dict[str, Any], follow_up_count: int) -> list[Check]:
    budget = manifest.get("follow_up_budget")
    if not isinstance(budget, dict):
        return [
            Check(
                "ERROR",
                "governance-hk-public-split",
                "HK split follow-up budget is missing or invalid.",
            )
        ]
    if not HK_SPLIT_FOLLOW_UP_BUDGET_FIELDS <= set(budget):
        return [
            Check(
                "ERROR",
                "governance-hk-public-split",
                "HK split follow-up budget is missing fields: "
                + ", ".join(sorted(HK_SPLIT_FOLLOW_UP_BUDGET_FIELDS - set(budget))),
            )
        ]

    limit = budget["blocked_or_follow_up_records_max"]
    policy = budget["policy"]
    issues: list[str] = []
    if not _valid_budget_limit(limit):
        issues.append("blocked_or_follow_up_records_max must be a non-negative integer")
    elif follow_up_count > limit:
        issues.append(f"HK split follow-up count {follow_up_count} exceeds max {limit}")
    if not isinstance(policy, str) or not policy.strip():
        issues.append("policy must be a non-empty string")
    if issues:
        return [
            Check(
                "ERROR",
                "governance-hk-public-split",
                "HK split follow-up budget violation: " + "; ".join(issues),
            )
        ]

    return [
        Check(
            "OK",
            "governance-hk-public-split",
            f"HK split follow-up budget holds: follow_up={follow_up_count}/{limit}.",
        )
    ]


def _hk_split_repo_local_patterns(manifest: dict[str, Any]) -> list[str]:
    patterns: list[str] = []
    for record in manifest.get("records", []):
        if (
            isinstance(record, dict)
            and record.get("path_kind") == "repo_local"
            and isinstance(record.get("paths"), list)
        ):
            patterns.extend(str(pattern) for pattern in record["paths"])
    return patterns


def _hk_split_path_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        root = pattern.removesuffix("/**").rstrip("/")
        return path == root or path.startswith(f"{root}/")
    if "*" in pattern:
        return fnmatch.fnmatch(path, pattern)
    return path == pattern


def _tracked_hk_split_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for scan_root_name in HK_SPLIT_SCAN_ROOTS:
        scan_root = root / scan_root_name
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or any(part in HK_SPLIT_IGNORE_PARTS for part in path.parts):
                continue
            relative = path.relative_to(root).as_posix()
            if HK_SPLIT_MARKER_RE.search(relative):
                paths.append(relative)
    return sorted(paths)


def _uncovered_hk_split_paths(root: Path, manifest: dict[str, Any]) -> list[str]:
    patterns = _hk_split_repo_local_patterns(manifest)
    return [
        path
        for path in _tracked_hk_split_paths(root)
        if not any(_hk_split_path_matches(path, pattern) for pattern in patterns)
    ]


def check_hk_public_split(root: Path, manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    records = {
        str(record.get("id", "")): record
        for record in manifest.get("records", [])
        if isinstance(record, dict)
    }
    missing = sorted(HK_PUBLIC_SPLIT_REQUIRED_IDS - set(records))
    gate_issues = _ready_split_gate_issues(manifest)
    uncovered = _uncovered_hk_split_paths(root, manifest)
    if missing or gate_issues or uncovered:
        detail = []
        if missing:
            detail.append("missing_ids=" + ", ".join(missing))
        if gate_issues:
            detail.append("ready_gate_issues=" + "; ".join(gate_issues))
        if uncovered:
            detail.append("uncovered_paths=" + ", ".join(uncovered))
        checks.append(
            Check(
                "ERROR",
                "governance-hk-public-split",
                "HK public split governance mismatch: " + "; ".join(detail),
            )
        )
    else:
        checks.append(
            Check(
                "OK",
                "governance-hk-public-split",
                "HK public split manifest required surfaces and deletion gates are guarded.",
            )
        )
    follow_up = [
        identifier
        for identifier, record in records.items()
        if isinstance(record.get("deletion_gate"), dict)
        and record["deletion_gate"].get("status") in HK_SPLIT_PENDING_STATUSES
    ]
    if follow_up:
        checks.append(
            Check(
                "WARN",
                "governance-hk-public-split",
                f"HK split records still need follow-up or audit: {len(follow_up)}.",
            )
        )
    checks.extend(_check_follow_up_budget(manifest, len(follow_up)))
    return checks
