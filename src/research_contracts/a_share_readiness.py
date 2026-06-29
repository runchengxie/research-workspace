#!/usr/bin/env python3
"""Read-only A-share readiness report for the integrated workspace."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from a_share_readiness_common import (
    BASELINE_ASSETS,
    COMPLETE_PIT_ASSETS,
    HISTORICAL_INDUSTRY_RULES,
    PIT_FUNDAMENTALS_RULES,
    READINESS_LEVELS,
    SIDE_AWARE_RULES,
)
from a_share_readiness_evidence import build_readiness_report

__all__ = [
    "BASELINE_ASSETS",
    "COMPLETE_PIT_ASSETS",
    "HISTORICAL_INDUSTRY_RULES",
    "PIT_FUNDAMENTALS_RULES",
    "READINESS_LEVELS",
    "SIDE_AWARE_RULES",
    "build_readiness_report",
    "main",
]


def _write_report(report: Mapping[str, Any], output: Path | None, *, pretty: bool) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2 if pretty else None)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect no-write A-share workspace readiness.")
    parser.add_argument(
        "--artifacts-root",
        default=os.environ.get("DATA_PLATFORM_ROOT"),
        help="Shared data-platform root. Defaults to DATA_PLATFORM_ROOT.",
    )
    parser.add_argument("--evidence-manifest")
    parser.add_argument("--out")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--require", choices=READINESS_LEVELS)
    args = parser.parse_args(argv)

    if not args.artifacts_root:
        parser.error("--artifacts-root or DATA_PLATFORM_ROOT is required")
    try:
        report = build_readiness_report(
            args.artifacts_root,
            evidence_manifest=args.evidence_manifest,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _write_report(report, Path(args.out) if args.out else None, pretty=args.pretty)
    if args.require and not report["levels"][args.require]["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
