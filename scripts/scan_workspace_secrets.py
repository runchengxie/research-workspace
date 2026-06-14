#!/usr/bin/env python3
"""Scan superproject-owned files for secret leaks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ("README.md", "AGENTS.md", "pyproject.toml")
ROOT_DIRS = ("docs", "scripts", "tests", "demo")
SKIP_PARTS = {".git", ".pytest_cache", "__pycache__"}
TEXT_SUFFIXES = {".csv", ".json", ".md", ".py", ".txt", ".toml", ".yaml", ".yml"}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:access[_-]?token|api[_-]?key|client[_-]?secret|password|private[_-]?key)"
    r"\s*[:=]\s*[\"']?(?!<|\\{|\\$|none\b|example\b|private-value\b)[A-Za-z0-9_/+.-]{12,}"
)


def _root_owned_files(root: Path) -> list[Path]:
    files = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for dirname in ROOT_DIRS:
        directory = root / dirname
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in TEXT_SUFFIXES
                and not any(part in SKIP_PARTS for part in path.relative_to(root).parts)
            ):
                files.append(path)
    return sorted(set(files))


def scan_superproject(root: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    files = _root_owned_files(root)
    for path in files:
        relative = path.relative_to(root).as_posix()
        if any(part.startswith(".env") for part in path.relative_to(root).parts):
            issues.append({"path": relative, "check": "forbidden_env_file"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if SECRET_ASSIGNMENT.search(text):
            issues.append({"path": relative, "check": "credential_assignment"})
    return {
        "scope": "superproject_owned_files",
        "status": "passed" if not issues else "failed",
        "files_scanned": len(files),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result: dict[str, Any] = {"superproject": scan_superproject(args.root.resolve())}
    print(json.dumps(result, indent=2, sort_keys=True))
    failed = any(payload["status"] != "passed" for payload in result.values())
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
