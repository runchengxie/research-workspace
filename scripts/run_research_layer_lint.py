#!/usr/bin/env python3
"""Lint the migrated style-factor presentation layer.

The ``strategy-research`` directory is a directly-tracked ordinary directory
(not a submodule). Its ``pyproject.toml`` carries its own ruff profile that
intentionally permits Chinese full-width punctuation (RUF001/002/003), which
the superproject ruff profile would otherwise flag across the Chinese docs
and user-facing strings.

We run ruff from inside ``strategy-research`` so its ``pyproject.toml`` is the
effective config (ruff stops at the first ``pyproject.toml`` walking up). Only
the owned ``style_factors/`` package and ``tests/`` are linted; the
``experiments/`` adhoc scripts remain out of the quality gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_LAYER = ROOT / "strategy-research"


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    target = RESEARCH_LAYER
    # Use --no-project so uv does not try to resolve strategy-research's own
    # dependencies (alpha-research / portfolio-backtester are local packages
    # not on the registry). The ruff profile lives in strategy-research's
    # pyproject.toml, passed explicitly via --config so Chinese full-width
    # punctuation (RUF001/002/003) is intentionally allowed there.
    command = [
        "uv",
        "run",
        "--no-project",
        "--with",
        "ruff",
        "ruff",
        "check",
        "--config",
        str(target / "pyproject.toml"),
        "style_factors",
        "tests",
        *argv,
    ]
    result = subprocess.run(command, cwd=target)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
