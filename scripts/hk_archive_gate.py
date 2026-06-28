#!/usr/bin/env python3
"""Validate the private HK legacy archive boundary without moving source files."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "hk-private-archive-manifest.yml"
REQUIRED_REPOSITORIES = {
    "research-workspace",
    "market-data-platform",
    "strategy-pipeline",
    "quant-execution-engine",
}
REQUIRED_RECORD_FIELDS = {
    "archive_action",
    "archive_checksum",
    "consumer_audit",
    "deletion_gate",
    "focused_tests",
    "id",
    "lifecycle",
    "owner_repo",
    "paths",
    "replacement_docs",
    "restore_dependency",
    "rollback_notes",
}
REQUIRED_GATE_FIELDS = {
    "consumer_audit",
    "focused_tests",
    "private_archive_reference",
    "private_archive_export_evidence",
    "replacement_docs",
    "restore_evidence",
    "rollback_notes",
    "source_tag",
    "status",
    "zero_usage_release_window",
}
BLOCKING_VALUES = {
    "",
    "not_started",
    "pending",
    "pending_downstream_attestation",
    "pending_follow_up_execution",
    "pending_operator_stage",
    "pending_operator_tag",
    "pending_operator_publication",
}
READY_GATE_STATUSES = {"ready", "removed"}
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
Issue = dict[str, str]


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _repo_path(root: Path, manifest: dict[str, Any], owner: str) -> Path:
    repository_paths = manifest.get("repository_paths", {})
    return (root / str(repository_paths.get(owner, ""))).resolve()


def _git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed in {repo}")
    return result.stdout.strip()


def tracked_paths(repo: Path, revision: str) -> list[str]:
    return _git_output(repo, "ls-tree", "-r", "--name-only", revision).splitlines()


def matching_tracked_paths(repo: Path, revision: str, patterns: list[str]) -> list[str]:
    tracked = tracked_paths(repo, revision)
    return sorted(
        {path for path in tracked for pattern in patterns if fnmatch.fnmatch(path, pattern)}
    )


def _is_blocking(value: object) -> bool:
    return str(value or "").strip().lower() in BLOCKING_VALUES


def _issue(path: str, check: str) -> Issue:
    return {"path": path, "check": check}


def _archive_repository_issues(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if manifest.get("schema_version") != "hk_private_archive_manifest.v1":
        issues.append(_issue("schema_version", "unexpected_schema_version"))
    if manifest.get("checksum_policy") != "sha256":
        issues.append(_issue("checksum_policy", "sha256_required"))

    archive_repo = manifest.get("archive_repository", {})
    required_archive_values = {
        "visibility": "private",
        "maintenance": "paused",
        "purpose": "restore_only",
        "workspace_integration": "external_not_submodule",
    }
    for key, value in required_archive_values.items():
        if archive_repo.get(key) != value:
            issues.append(_issue(f"archive_repository.{key}", f"expected_{value}"))
    if not archive_repo.get("access_control_owners"):
        issues.append(_issue("archive_repository", "missing_access_control_owners"))
    return issues


def _revision_issues(manifest: dict[str, Any], *, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    repository_paths = manifest.get("repository_paths", {})
    source_revisions = manifest.get("source_revisions", {})
    if set(repository_paths) != REQUIRED_REPOSITORIES:
        issues.append(_issue("repository_paths", "unexpected_repository_set"))
    if set(source_revisions) != REQUIRED_REPOSITORIES:
        issues.append(_issue("source_revisions", "unexpected_revision_set"))
    for owner in sorted(REQUIRED_REPOSITORIES):
        revision = str(source_revisions.get(owner, ""))
        repo = _repo_path(root, manifest, owner)
        if not REVISION_RE.fullmatch(revision):
            issues.append(_issue(f"source_revisions.{owner}", "revision_not_pinned"))
            continue
        try:
            _git_output(repo, "cat-file", "-e", f"{revision}^{{commit}}")
        except RuntimeError:
            issues.append(_issue(f"source_revisions.{owner}", "revision_not_found"))
    return issues


def _record_path_issues(
    record_id: str,
    paths: list[Any],
    *,
    owner: str,
    manifest: dict[str, Any],
    root: Path,
) -> list[Issue]:
    source_revisions = manifest.get("source_revisions", {})
    revision = str(source_revisions.get(owner, ""))
    if not REVISION_RE.fullmatch(revision):
        return []

    repo = _repo_path(root, manifest, owner)
    return [
        _issue(f"{record_id}:{pattern}", "unresolved_path")
        for pattern in paths
        if not matching_tracked_paths(repo, revision, [str(pattern)])
    ]


def _single_record_issues(
    record: dict[str, Any],
    record_ids: set[str],
    *,
    manifest: dict[str, Any],
    root: Path,
) -> list[Issue]:
    issues: list[Issue] = []
    record_id = str(record.get("id", "missing-id"))
    if record_id in record_ids:
        issues.append(_issue(record_id, "duplicate_id"))
    record_ids.add(record_id)
    for field in sorted(REQUIRED_RECORD_FIELDS - set(record)):
        issues.append(_issue(record_id, f"missing_{field}"))
    owner = str(record.get("owner_repo", ""))
    if owner not in REQUIRED_REPOSITORIES:
        issues.append(_issue(record_id, "unknown_owner_repo"))
        return issues
    if record.get("archive_action") not in {"include", "retain_active"}:
        issues.append(_issue(record_id, "invalid_archive_action"))
    paths = record.get("paths", [])
    if not isinstance(paths, list) or not paths:
        issues.append(_issue(record_id, "empty_paths"))
        return issues
    issues.extend(_record_path_issues(record_id, paths, owner=owner, manifest=manifest, root=root))
    gate = record.get("deletion_gate", {})
    if not isinstance(gate, dict):
        issues.append(_issue(record_id, "invalid_deletion_gate"))
        return issues
    for field in sorted(REQUIRED_GATE_FIELDS - set(gate)):
        issues.append(_issue(record_id, f"missing_gate_{field}"))
    return issues


def _records_issues(
    manifest: dict[str, Any],
    *,
    root: Path,
) -> tuple[list[Issue], set[str], list[dict[str, Any]]]:
    issues: list[Issue] = []
    records = manifest.get("records", [])
    if not isinstance(records, list) or not records:
        issues.append(_issue("records", "empty_records"))
        records = []
    record_ids: set[str] = set()
    valid_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            issues.append(_issue("records", "invalid_record"))
            continue
        valid_records.append(record)
        issues.extend(_single_record_issues(record, record_ids, manifest=manifest, root=root))
    return issues, record_ids, valid_records


def _retained_boundary_issues(records: list[dict[str, Any]]) -> list[Issue]:
    issues: list[Issue] = []
    if not any(
        record.get("archive_action") == "retain_active"
        and record.get("owner_repo") == "quant-execution-engine"
        and any("longport" in path for path in record.get("paths", []))
        for record in records
    ):
        issues.append(_issue("records", "missing_retained_longport_boundary"))
    if not any(
        record.get("archive_action") == "retain_active"
        and record.get("owner_repo") == "market-data-platform"
        and any("cold_storage.py" in path for path in record.get("paths", []))
        for record in records
    ):
        issues.append(_issue("records", "missing_retained_restore_control_plane"))
    return issues


def _active_dependency_issues(manifest: dict[str, Any], *, root: Path) -> list[Issue]:
    archive_repo = manifest.get("archive_repository", {})
    archive_name = str(archive_repo.get("name", ""))
    integration_text = "\n".join(
        [
            (root / ".gitmodules").read_text(encoding="utf-8"),
            (root / "scripts" / "submodule_checks.json").read_text(encoding="utf-8"),
        ]
    )
    if archive_name and archive_name in integration_text:
        return [_issue(archive_name, "archive_repo_must_not_be_active_dependency")]
    return []


def validate_manifest(manifest: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    issues: list[Issue] = []
    issues.extend(_archive_repository_issues(manifest))
    issues.extend(_revision_issues(manifest, root=root))
    record_issues, record_ids, records = _records_issues(manifest, root=root)
    issues.extend(record_issues)
    issues.extend(_retained_boundary_issues(records))
    issues.extend(_active_dependency_issues(manifest, root=root))
    return {
        "status": "passed" if not issues else "failed",
        "schema_version": manifest.get("schema_version"),
        "record_ids": sorted(record_ids),
        "issues": issues,
    }


def _record_blockers(record: dict[str, Any]) -> list[str]:
    gate = record.get("deletion_gate", {})
    if gate.get("status") == "not_applicable":
        return []
    blockers = [
        field
        for field in sorted(REQUIRED_GATE_FIELDS - {"status"})
        if _is_blocking(gate.get(field))
    ]
    if gate.get("status") not in READY_GATE_STATUSES:
        blockers.append("status")
    return blockers


def build_report(
    manifest: dict[str, Any],
    *,
    root: Path = ROOT,
    export_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_manifest(manifest, root=root)
    records = []
    for record in manifest.get("records", []):
        blockers = _record_blockers(record)
        eligible_for_removal_review = record["archive_action"] == "include" and not blockers
        records.append(
            {
                "id": record["id"],
                "owner_repo": record["owner_repo"],
                "archive_action": record["archive_action"],
                "deletion_gate_status": record["deletion_gate"]["status"],
                "blockers": blockers,
                "eligible_for_removal_review": eligible_for_removal_review,
            }
        )
    export_validation = {"status": "not_provided", "issues": []}
    if export_manifest is not None:
        export_issues = []
        if export_manifest.get("schema_version") != "hk_private_archive_export_manifest.v1":
            export_issues.append("unexpected_schema_version")
        if export_manifest.get("source_revisions") != manifest.get("source_revisions"):
            export_issues.append("source_revision_mismatch")
        if export_manifest.get("scan", {}).get("status") != "passed":
            export_issues.append("archive_scan_failed")
        if not export_manifest.get("archive_sha256"):
            export_issues.append("missing_archive_sha256")
        export_validation = {
            "status": "passed" if not export_issues else "failed",
            "issues": export_issues,
        }
    removal_blocked = any(record["blockers"] for record in records)
    return {
        "schema_version": "hk_private_archive_gate_report.v1",
        "status": (
            "passed"
            if validation["status"] == "passed" and export_validation["status"] != "failed"
            else "failed"
        ),
        "manifest_validation": validation,
        "export_validation": export_validation,
        "removal_review_status": (
            "blocked_pending_audit" if removal_blocked else "eligible_for_removal_review"
        ),
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Run the read-only archive gate.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--export-manifest", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("--check is required; this script never mutates archive state")
    manifest = load_manifest(args.manifest.resolve())
    export_manifest = (
        json.loads(args.export_manifest.resolve().read_text(encoding="utf-8"))
        if args.export_manifest
        else None
    )
    report = build_report(manifest, export_manifest=export_manifest)
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.format == "json"
        else (
            f"status={report['status']} "
            f"removal_review_status={report['removal_review_status']} "
            f"records={len(report['records'])}"
        )
    )
    if args.out:
        args.out.resolve().write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
