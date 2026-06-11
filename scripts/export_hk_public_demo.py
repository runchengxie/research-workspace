#!/usr/bin/env python3
"""Stage and verify the curated HK public demo without copying Git history."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from hk_public_demo_scan import scan_public_tree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "demo" / "hk-public-demo-export-v1.json"
DEFAULT_SPLIT_MANIFEST = ROOT / "docs" / "hk-public-split-manifest.yml"
READY_BLOCKERS = {
    "",
    "manual_review_required",
    "not_recorded",
    "pending",
    "todo",
}
REQUIRED_RECORD_FIELDS = {
    "action",
    "consumer_audit_status",
    "deletion_gate",
    "id",
    "owner_repo",
    "path_kind",
    "paths",
    "public_safety",
    "removal_condition",
    "replacement_path",
    "required_redactions",
    "restore_dependency",
}
REQUIRED_GATE_FIELDS = {
    "consumer_audit",
    "focused_tests",
    "public_split_evidence",
    "replacement_docs",
    "restore_evidence",
    "rollback_notes",
    "status",
}
Issue = dict[str, str]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def load_split_manifest(path: Path = DEFAULT_SPLIT_MANIFEST) -> dict[str, Any]:
    return _load_json(path)


def _path_matches(pattern: str, *, root: Path) -> list[Path]:
    if pattern.endswith("/**"):
        directory = root / pattern.removesuffix("/**")
        if directory.is_dir():
            return sorted(path for path in directory.rglob("*") if path.is_file())
    matches = sorted(path for path in root.glob(pattern) if path.is_file())
    if matches:
        return matches
    literal = root / pattern
    return [literal] if literal.is_file() else []


def _issue(path: str, check: str) -> Issue:
    return {"path": path, "check": check}


def _split_gate_issues(
    record_id: str,
    gate: object,
    cleanup_statuses: set[Any],
    gate_requirements: set[Any],
) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(gate, dict):
        return [_issue(record_id, "invalid_deletion_gate")]

    required_gate_fields = gate_requirements or REQUIRED_GATE_FIELDS
    for field in sorted(required_gate_fields):
        if field not in gate:
            issues.append(_issue(record_id, f"missing_gate_{field}"))
    if gate.get("status") not in cleanup_statuses:
        issues.append(_issue(record_id, "invalid_cleanup_status"))
    if gate.get("status") == "ready":
        for field in sorted(required_gate_fields):
            value = str(gate.get(field, "")).strip().lower()
            if value in READY_BLOCKERS:
                issues.append(_issue(record_id, f"ready_gate_blocked_{field}"))
    return issues


def _split_record_path_issues(
    record_id: str, paths: object, path_kind: object, root: Path
) -> list[Issue]:
    if not isinstance(paths, list) or not paths:
        return [_issue(record_id, "empty_paths")]
    if path_kind != "repo_local":
        return []
    return [
        _issue(f"{record_id}:{pattern}", "unresolved_path")
        for pattern in paths
        if not _path_matches(str(pattern), root=root)
    ]


def _split_record_issues(
    record: object,
    index: int,
    seen_ids: set[str],
    *,
    actions: set[Any],
    public_safety: set[Any],
    cleanup_statuses: set[Any],
    gate_requirements: set[Any],
    root: Path,
) -> tuple[str, list[Issue]]:
    if not isinstance(record, dict):
        record_id = f"record[{index}]"
        return record_id, [_issue(record_id, "invalid_record")]

    issues: list[Issue] = []
    record_id = str(record.get("id") or f"record[{index}]")
    for field in sorted(REQUIRED_RECORD_FIELDS - set(record)):
        issues.append(_issue(record_id, f"missing_{field}"))
    if record_id in seen_ids:
        issues.append(_issue(record_id, "duplicate_id"))
    seen_ids.add(record_id)

    if record.get("action") not in actions:
        issues.append(_issue(record_id, "invalid_action"))
    if record.get("public_safety") not in public_safety:
        issues.append(_issue(record_id, "invalid_public_safety"))
    gate = record.get("deletion_gate", {})
    issues.extend(_split_gate_issues(record_id, gate, cleanup_statuses, gate_requirements))
    paths = record.get("paths", [])
    issues.extend(_split_record_path_issues(record_id, paths, record.get("path_kind"), root))
    return record_id, issues


def validate_split_manifest(manifest: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    issues: list[Issue] = []
    actions = set(manifest.get("actions", []))
    public_safety = set(manifest.get("public_safety", []))
    cleanup_statuses = set(manifest.get("cleanup_statuses", []))
    gate_requirements = set(manifest.get("deletion_gate_requirements", []))
    records = manifest.get("records", [])

    if manifest.get("schema_version") != "hk_public_split_manifest.v1":
        issues.append(_issue("schema_version", "unexpected_schema_version"))
    if not isinstance(records, list) or not records:
        issues.append(_issue("records", "empty_records"))
        records = []

    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        record_id, record_issues = _split_record_issues(
            record,
            index,
            seen_ids,
            actions=actions,
            public_safety=public_safety,
            cleanup_statuses=cleanup_statuses,
            gate_requirements=gate_requirements,
            root=root,
        )
        issues.extend(record_issues)

    return {
        "status": "passed" if not issues else "failed",
        "schema_version": manifest.get("schema_version", "unknown"),
        "record_ids": sorted(seen_ids),
        "issues": issues,
    }


def _repo_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _read_allowlist(path: Path) -> list[Path]:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if text and not text.startswith("#"):
            relative = Path(text)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe allowlist entry: {text}")
            rows.append(relative)
    if not rows:
        raise ValueError("HK public demo allowlist is empty")
    return rows


def _run_quality_checks(root: Path) -> dict[str, Any]:
    commands = [[sys.executable, "scripts/check_quality.py"]]
    results = [_run_checked(command, cwd=root) for command in commands]
    return {
        "status": "passed" if all(result["returncode"] == 0 for result in results) else "failed",
        "results": results,
    }


def _public_split_record_ids(manifest: dict[str, Any]) -> list[str]:
    public_actions = {"archive_in_public_demo", "move_to_public_demo"}
    return sorted(
        str(record["id"])
        for record in manifest.get("records", [])
        if record.get("action") in public_actions
    )


def _run_checked(command: list[str], *, cwd: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    display_command = ["python", *command[1:]] if command[:1] == [sys.executable] else command
    payload = {
        "command": display_command,
        "returncode": result.returncode,
    }
    if result.returncode != 0:
        payload["stdout"] = result.stdout
        payload["stderr"] = result.stderr
    return payload


def export_demo(*, config_path: Path, out_dir: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    template_root = ROOT / str(config["template_root"])
    allowlist_path = ROOT / str(config["allowlist"])
    split_manifest_path = ROOT / str(
        config.get("split_manifest", DEFAULT_SPLIT_MANIFEST.relative_to(ROOT))
    )
    split_manifest = load_split_manifest(split_manifest_path)
    split_manifest_validation = validate_split_manifest(split_manifest)
    if split_manifest_validation["status"] != "passed":
        raise RuntimeError(
            f"HK public split manifest validation failed: {split_manifest_validation['issues']}"
        )

    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing export directory: {out_dir}")
    out_dir.mkdir(parents=True)

    included_files = []
    for relative in _read_allowlist(allowlist_path):
        source = template_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"Allowlisted demo file is missing: {source}")
        destination = out_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        included_files.append(relative.as_posix())

    initial_scan = scan_public_tree(out_dir)
    if initial_scan["status"] != "passed":
        raise RuntimeError(f"Public demo safety scan failed: {initial_scan['issues']}")

    smoke_commands = [
        [sys.executable, "scripts/run_demo.py", "--out-dir", "samples"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    ]
    smoke_results = [_run_checked(command, cwd=out_dir) for command in smoke_commands]
    if any(result["returncode"] != 0 for result in smoke_results):
        raise RuntimeError(f"Public demo offline smoke failed: {smoke_results}")

    quality_checks = _run_quality_checks(out_dir)
    if quality_checks["status"] != "passed":
        raise RuntimeError(f"Public demo quality checks failed: {quality_checks['results']}")

    final_scan = scan_public_tree(out_dir)
    if final_scan["status"] != "passed":
        raise RuntimeError(f"Public demo safety scan failed: {final_scan['issues']}")

    manifest = {
        "schema_version": "hk_public_demo_export_manifest.v1",
        "source_revision": _repo_revision(),
        "public_repository": config["public_repository"],
        "split_manifest": {
            "schema_version": split_manifest_validation["schema_version"],
            "record_ids": _public_split_record_ids(split_manifest),
            "validation": split_manifest_validation,
        },
        "included_files": included_files,
        "generated_files": ["samples/summary.json", "samples/targets.json"],
        "synthetic_fixtures": ["fixtures/synthetic_prices.csv"],
        "scan": final_scan,
        "offline_smoke": {
            "status": "passed",
            "results": smoke_results,
        },
        "quality_checks": quality_checks,
    }
    manifest_path = out_dir / "export-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest_scan = scan_public_tree(out_dir)
    if manifest_scan["status"] != "passed":
        raise RuntimeError(f"Export manifest safety scan failed: {manifest_scan['issues']}")
    manifest["scan"] = manifest_scan
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--scan-only", type=Path)
    args = parser.parse_args()
    if args.scan_only is not None:
        result = scan_public_tree(args.scan_only.resolve())
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "passed" else 1
    if args.out is None:
        parser.error("--out is required unless --scan-only is used")
    result = export_demo(
        config_path=args.config.resolve(),
        out_dir=args.out.resolve(),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
