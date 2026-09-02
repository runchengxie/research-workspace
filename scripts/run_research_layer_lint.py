#!/usr/bin/env python3
"""Run the strategy-research presentation-layer quality gate.

``strategy-research`` is an independently versioned Git submodule with its own
``pyproject.toml`` and development environment. Its Ruff profile permits the
Chinese punctuation used in documentation strings and comments. Repository
local Git sources support standalone installation, while the superproject
locks the workspace source version through the submodule gitlink.

The gate runs inside the strategy-research project and covers Ruff lint, Ruff
format, the ty typed surface, and the ``python -m style_factors`` CLI smoke.
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
        [*project, "ruff", "check", "src/style_factors", "tests", *argv],
        [*project, "ruff", "format", "--check", "src/style_factors", "tests"],
        [*project, "ty", "check", "--error-on-warning"],
        [*project, "python", "-m", "style_factors", "--help"],
    ]
    for check in checks:
        if _run(check, cwd=target) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
