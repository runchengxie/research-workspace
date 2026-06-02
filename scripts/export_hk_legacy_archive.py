#!/usr/bin/env python3
"""Stage the private HK legacy source archive from pinned Git revisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from hk_archive_gate import DEFAULT_MANIFEST, ROOT, load_manifest, matching_tracked_paths
from hk_archive_gate import validate_manifest as validate_private_manifest

FORBIDDEN_ROOT_PARTS = {"artifacts", "cache", "data", "outputs", "reports"}
FORBIDDEN_PARTS = {".git", ".pytest_cache", ".venv", "__pycache__"}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".feather",
    ".gz",
    ".parquet",
    ".pickle",
    ".pkl",
    ".tar",
    ".zst",
    ".zip",
}
CREDENTIAL_LITERAL = re.compile(
    r"(?i)(?:token|secret|password|api[_-]?key|access[_-]?key)\s*[:=]\s*[\"'][^\"']{8,}[\"']"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_bytes(repo: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def _safety_issues(relative: Path, data: bytes) -> list[dict[str, str]]:
    issues = []
    if relative.parts and relative.parts[0] in FORBIDDEN_ROOT_PARTS:
        issues.append({"path": relative.as_posix(), "check": "runtime_root"})
    if any(part.startswith(".env") or part in FORBIDDEN_PARTS for part in relative.parts):
        issues.append({"path": relative.as_posix(), "check": "forbidden_path"})
    if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
        issues.append({"path": relative.as_posix(), "check": "runtime_or_archive_suffix"})
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        issues.append({"path": relative.as_posix(), "check": "non_utf8_source"})
    else:
        if CREDENTIAL_LITERAL.search(text):
            issues.append({"path": relative.as_posix(), "check": "credential_literal"})
    return issues


def scan_archive_tree(root: Path) -> dict[str, Any]:
    issues = []
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        files.append(relative.as_posix())
        issues.extend(_safety_issues(relative, path.read_bytes()))
    return {
        "status": "passed" if not issues else "failed",
        "files_scanned": len(files),
        "files": files,
        "issues": issues,
    }


def export_archive(*, manifest_path: Path, out_dir: Path, root: Path = ROOT) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    validation = validate_private_manifest(manifest, root=root)
    if validation["status"] != "passed":
        raise RuntimeError(f"HK private archive manifest failed validation: {validation['issues']}")
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing export directory: {out_dir}")
    out_dir.mkdir(parents=True)
    repository_paths = manifest["repository_paths"]
    source_revisions = manifest["source_revisions"]
    included: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in manifest["records"]:
        if record["archive_action"] != "include":
            continue
        owner = str(record["owner_repo"])
        repo = (root / str(repository_paths[owner])).resolve()
        revision = str(source_revisions[owner])
        for source_path in matching_tracked_paths(repo, revision, record["paths"]):
            staged_relative = Path(owner) / source_path
            staged_key = staged_relative.as_posix()
            if staged_key in seen:
                continue
            seen.add(staged_key)
            data = _git_bytes(repo, revision, source_path)
            issues = _safety_issues(Path(source_path), data)
            if issues:
                raise RuntimeError(f"HK private archive safety scan failed: {issues}")
            destination = out_dir / staged_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            included.append(
                {
                    "record_id": str(record["id"]),
                    "owner_repo": owner,
                    "source_path": source_path,
                    "staged_path": staged_key,
                    "sha256": _sha256(data),
                }
            )
    readme = (
        "# HK quant legacy archive\n\n"
        "Private paused-maintenance restore-only source archive. "
        "This repository is not an active workspace dependency.\n"
    )
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    initial_scan = scan_archive_tree(out_dir)
    if initial_scan["status"] != "passed":
        raise RuntimeError(f"HK private archive safety scan failed: {initial_scan['issues']}")
    combined = "\n".join(f"{row['staged_path']}:{row['sha256']}" for row in included).encode()
    export_manifest = {
        "schema_version": "hk_private_archive_export_manifest.v1",
        "archive_repository": manifest["archive_repository"],
        "source_revisions": source_revisions,
        "included_files": included,
        "archive_sha256": _sha256(combined),
        "scan": initial_scan,
    }
    output = out_dir / "archive-export-manifest.json"
    output.write_text(
        json.dumps(export_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    final_scan = scan_archive_tree(out_dir)
    if final_scan["status"] != "passed":
        raise RuntimeError(f"HK private archive safety scan failed: {final_scan['issues']}")
    export_manifest["scan"] = final_scan
    output.write_text(
        json.dumps(export_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return export_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--scan-only", type=Path)
    args = parser.parse_args(argv)
    if args.scan_only is not None:
        result = scan_archive_tree(args.scan_only.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "passed" else 1
    if args.out is None:
        parser.error("--out is required unless --scan-only is used")
    result = export_archive(
        manifest_path=args.manifest.resolve(),
        out_dir=args.out.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
