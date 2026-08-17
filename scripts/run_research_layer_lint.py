#!/usr/bin/env python3
"""Run the strategy-research presentation-layer quality gate.

The ``strategy-research`` directory is a directly-tracked ordinary directory
(not a submodule). Its ``pyproject.toml`` carries its own ruff profile that
intentionally permits Chinese full-width punctuation (RUF001/002/003), its own
``uv.lock``, and local path sources for alpha-research, portfolio-backtester
and research-contracts. All checks run inside the project environment, so the
project stays independently runnable without PYTHONPATH injection.

The gate covers ruff lint, ruff format, the ty typed surface, and a CLI
import/help smoke for ``python -m style_factors``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_LAYER = ROOT / "strategy-research"


def _run(command: list[str], cwd: Path) -> int:
    return subprocess.run(command, cwd=cwd).returncode


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    target = RESEARCH_LAYER
    project = ["uv", "run", "--project", str(target), "--extra", "dev"]
    checks = [
        [*project, "ruff", "check", "style_factors", "tests", *argv],
        [*project, "ruff", "format", "--check", "style_factors", "tests"],
        [*project, "ty", "check", "--error-on-warning"],
        [*project, "python", "-m", "style_factors", "--help"],
    ]
    for check in checks:
        if _run(check, cwd=target) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
