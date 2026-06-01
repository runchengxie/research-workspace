#!/usr/bin/env python3
"""Print the current workspace/submodule version matrix as Markdown."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from workspace_doctor import EXPECTED_SUBMODULES

ROOT = Path(__file__).resolve().parents[1]


def _git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _is_git_checkout(path: Path) -> bool:
    code, stdout, _stderr = _git(["rev-parse", "--is-inside-work-tree"], path)
    return code == 0 and stdout == "true"


def _short_commit(path: Path) -> str:
    code, stdout, stderr = _git(["rev-parse", "--short", "HEAD"], path)
    if code != 0:
        detail = stderr or "git rev-parse failed"
        return f"unavailable ({detail})"
    return stdout


def _dirty_suffix(path: Path) -> str:
    code, stdout, _stderr = _git(["status", "--short"], path)
    if code != 0:
        return " + status unavailable"
    status = stdout
    return " + local changes" if status else ""


def _submodule_commit(root: Path, submodule: str) -> str:
    repo = root / submodule
    if not repo.exists():
        return "missing"
    if not (repo / ".git").exists():
        return "not initialized"
    if not _is_git_checkout(repo):
        return "not a git checkout"
    return f"`{_short_commit(repo)}`{_dirty_suffix(repo)}"


def render_matrix(root: Path) -> str:
    workspace = _short_commit(root)
    rows = []
    for submodule in EXPECTED_SUBMODULES:
        rows.append((submodule, _submodule_commit(root, submodule)))

    lines = [
        "| component | commit |",
        "| --- | --- |",
        f"| workspace | `{workspace}`{_dirty_suffix(root)} |",
    ]
    for component, commit in rows:
        lines.append(f"| {component} | {commit} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not _is_git_checkout(root):
        print(
            "Version matrix requires a git checkout with initialized submodules; "
            f"{root} is not a git work tree.",
        )
        return 2

    print(render_matrix(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
