#!/usr/bin/env python3
"""Compatibility facade governance checks for the workspace."""

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath
from typing import Any, TypeGuard

from workspace_governance_common import Check

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


def check_compatibility_facades(root: Path, manifest: dict[str, Any]) -> list[Check]:
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


__all__ = [
    "check_compatibility_facades",
    "_compatibility_facade_common_issues",
    "_compatibility_facade_record_paths",
    "_has_star_import",
    "_is_concrete_facade_path",
    "_tracked_compatibility_facade_paths",
]
