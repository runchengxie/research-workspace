"""Gitmodules structure check for the research-workspace superproject."""

from __future__ import annotations

from pathlib import Path

from doctor_common import EXPECTED_SUBMODULES, parse_gitmodules
from workspace_governance import Check


def check_gitmodules(root: Path) -> list[Check]:
    checks: list[Check] = []
    submodules = parse_gitmodules(root)
    if not submodules:
        return [Check("ERROR", "gitmodules", "Missing or empty .gitmodules.")]

    expected_paths = set(EXPECTED_SUBMODULES)
    actual_paths = set(submodules.values())
    missing = sorted(expected_paths - actual_paths)
    extra = sorted(actual_paths - expected_paths)
    if missing:
        checks.append(
            Check("ERROR", "gitmodules", f"Missing expected submodule paths: {', '.join(missing)}")
        )
    if extra:
        checks.append(
            Check("WARN", "gitmodules", f"Unexpected submodule paths: {', '.join(extra)}")
        )
    if not missing:
        checks.append(Check("OK", "gitmodules", "Expected submodule paths are present."))
    return checks
