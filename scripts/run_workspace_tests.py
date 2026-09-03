#!/usr/bin/env python3
"""Run superproject integration tests against the checked-out workspace sources."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SOURCE_ROOTS = (
    Path("src"),
    Path("market-data-platform/src"),
    Path("alpha-research/src"),
    Path("portfolio-backtester/src"),
    Path("strategy-app/src"),
    Path("strategy-pipeline/src"),
)


class WorkspaceSourceError(RuntimeError):
    """Raised when a source tree required by workspace integration tests is missing."""


def workspace_pythonpath(root: Path, *, existing: str | None = None) -> str:
    root = root.resolve()
    paths = [(root / relative).resolve() for relative in WORKSPACE_SOURCE_ROOTS]
    missing = [
        relative.as_posix()
        for relative, path in zip(WORKSPACE_SOURCE_ROOTS, paths, strict=True)
        if not path.is_dir()
    ]
    if missing:
        raise WorkspaceSourceError(
            "workspace integration tests require initialized source trees: " + ", ".join(missing)
        )

    values = [str(path) for path in paths]
    if existing:
        values.append(existing)
    return os.pathsep.join(values)


def pytest_command(root: Path) -> tuple[str, ...]:
    root = root.resolve()
    return (
        "uv",
        "run",
        "--project",
        str(root),
        "--group",
        "dev",
        "python",
        "-m",
        "pytest",
        str(root / "tests"),
        "--ignore",
        str(root / "tests/test_next_open_to_high_research.py"),
        "--ignore",
        str(root / "tests/test_next_open_to_high_research_part2.py"),
        "--ignore",
        str(root / "tests/test_private_research_config_boundary.py"),
        "-q",
    )


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = workspace_pythonpath(ROOT, existing=env.get("PYTHONPATH"))
    completed = subprocess.run(pytest_command(ROOT), cwd=ROOT, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
