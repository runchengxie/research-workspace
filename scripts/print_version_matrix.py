#!/usr/bin/env python3
"""Print the current workspace/submodule version matrix as Markdown."""

from __future__ import annotations

import subprocess
from pathlib import Path

from workspace_doctor import EXPECTED_SUBMODULES


ROOT = Path(__file__).resolve().parents[1]


def _git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _short_commit(path: Path) -> str:
    return _git(["rev-parse", "--short", "HEAD"], path)


def _dirty_suffix(path: Path) -> str:
    status = _git(["status", "--short"], path)
    return " + local changes" if status else ""


def main() -> int:
    workspace = _short_commit(ROOT)
    rows = []
    for submodule in EXPECTED_SUBMODULES:
        repo = ROOT / submodule
        if not repo.exists():
            rows.append((submodule, "missing"))
            continue
        rows.append((submodule, f"`{_short_commit(repo)}`{_dirty_suffix(repo)}"))

    print("| component | commit |")
    print("| --- | --- |")
    print(f"| workspace | `{workspace}`{_dirty_suffix(ROOT)} |")
    for component, commit in rows:
        print(f"| {component} | {commit} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
