#!/usr/bin/env python3
"""Run high-confidence dead-code discovery without blocking normal quality gates."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = ("src", "scripts", "tests")


def _vulture_command(paths: tuple[str, ...], min_confidence: int) -> tuple[str, ...]:
    args = (*paths, "--min-confidence", str(min_confidence))
    if resolved := shutil.which("vulture"):
        return (resolved, *args)
    return ("uvx", "vulture", *args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=DEFAULT_PATHS)
    parser.add_argument("--min-confidence", type=int, default=90)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return vulture's non-zero finding status instead of advisory success.",
    )
    args = parser.parse_args(argv)

    command = _vulture_command(tuple(args.paths), args.min_confidence)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode == 0:
        return 0
    if completed.returncode == 3 and not args.strict:
        print("[WARN] dead-code advisory findings reported; rerun with --strict to fail.")
        return 0
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
