#!/usr/bin/env python3
"""Read-only checks for the research-workspace superproject.

This module aggregates the per-domain check functions defined in the
``doctor_*_checks.py`` modules and exposes them at the top level so that
existing callers (``tests/test_workspace_doctor.py``, ``print_version_matrix.py``
and the pre-push subprocess) keep working unchanged.
"""

from __future__ import annotations

import argparse
import os  # noqa: F401  (exposed for tests that patch workspace_doctor.os.environ)
from pathlib import Path

import doctor_common
from doctor_boundary_checks import check_script_import_boundaries
from doctor_cli_checks import check_public_clis
from doctor_common import DATA_PLATFORM_ROOT_CANDIDATES
from doctor_data_platform_checks import check_data_platform_root as _check_data_platform_root
from doctor_doc_checks import check_readme
from doctor_env_checks import check_top_level_outputs
from doctor_git_checks import check_gitmodules
from doctor_hk_archive_checks import check_hk_private_archive_governance
from doctor_hook_checks import check_local_git_hooks
from doctor_submodule_checks import check_submodule_freshness, check_submodule_state
from workspace_governance import (
    Check,  # noqa: F401  (used only in type annotations)
    check_maintainability_governance,
)

# Re-exported so existing callers (tests, print_version_matrix) keep working.
EXPECTED_SUBMODULES = doctor_common.EXPECTED_SUBMODULES
SHARED_HOOK_NAMES = doctor_common.SHARED_HOOK_NAMES
parse_gitmodules = doctor_common.parse_gitmodules


def check_data_platform_root(root: Path | None = None) -> list[Check]:
    return _check_data_platform_root(root, candidates=DATA_PLATFORM_ROOT_CANDIDATES)


def run_checks(root: Path) -> list[Check]:
    root = root.resolve()
    checks: list[Check] = []
    checks.extend(check_gitmodules(root))
    checks.extend(check_readme(root))
    checks.extend(check_submodule_state(root))
    checks.extend(check_submodule_freshness(root))
    checks.extend(check_local_git_hooks(root))
    checks.extend(check_public_clis(root))
    checks.extend(check_data_platform_root(root))
    checks.extend(check_top_level_outputs(root))
    checks.extend(check_script_import_boundaries(root))
    checks.extend(check_hk_private_archive_governance(root))
    checks.extend(check_maintainability_governance(root))
    return checks


def render_checks(checks: list[Check]) -> str:
    lines = [f"[{check.severity}] {check.code}: {check.message}" for check in checks]
    errors = sum(1 for check in checks if check.severity == "ERROR")
    warnings = sum(1 for check in checks if check.severity == "WARN")
    lines.append(f"Summary: errors={errors} warnings={warnings}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only workspace health checks.")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures. Useful before bumping submodule pointers.",
    )
    args = parser.parse_args(argv)

    checks = run_checks(Path(args.root))
    print(render_checks(checks))
    has_errors = any(check.severity == "ERROR" for check in checks)
    has_warnings = any(check.severity == "WARN" for check in checks)
    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
