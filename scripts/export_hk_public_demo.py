#!/usr/bin/env python3
"""Stage and verify the curated HK public demo without copying Git history."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "demo" / "hk-public-demo-export-v1.json"
MAX_PUBLIC_FILE_BYTES = 512 * 1024
FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "cache",
    "outputs",
}
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
FORBIDDEN_TEXT = {
    "absolute_local_path": re.compile(r"(?:/home/|/tmp/|/Users/|[A-Za-z]:\\\\Users\\\\)"),
    "credential_assignment": re.compile(
        r"(?i)(?:token|secret|password|api[_-]?key|access[_-]?key)\s*[:=]\s*[^\s<]+"
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


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


def scan_public_tree(root: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        relative_text = relative.as_posix()
        files.append(relative_text)
        if any(part.startswith(".env") or part in FORBIDDEN_PARTS for part in relative.parts):
            issues.append({"path": relative_text, "check": "forbidden_path"})
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            issues.append({"path": relative_text, "check": "licensed_or_archive_suffix"})
        if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
            issues.append({"path": relative_text, "check": "oversized_file"})
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append({"path": relative_text, "check": "non_utf8_file"})
            continue
        for check, pattern in FORBIDDEN_TEXT.items():
            if pattern.search(text):
                issues.append({"path": relative_text, "check": check})
    return {
        "status": "passed" if not issues else "failed",
        "files_scanned": len(files),
        "files": files,
        "issues": issues,
    }


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

    final_scan = scan_public_tree(out_dir)
    if final_scan["status"] != "passed":
        raise RuntimeError(f"Public demo safety scan failed: {final_scan['issues']}")

    manifest = {
        "schema_version": "hk_public_demo_export_manifest.v1",
        "source_revision": _repo_revision(),
        "public_repository": config["public_repository"],
        "included_files": included_files,
        "generated_files": ["samples/summary.json", "samples/targets.json"],
        "synthetic_fixtures": ["fixtures/synthetic_prices.csv"],
        "scan": final_scan,
        "offline_smoke": {
            "status": "passed",
            "results": smoke_results,
        },
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
