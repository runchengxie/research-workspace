"""Top-level output, secret and shared-code leakage checks."""

from __future__ import annotations

from pathlib import Path

import workspace_env
from doctor_common import (
    FORBIDDEN_TOP_LEVEL_DIRS,
    FORBIDDEN_TOP_LEVEL_PATTERNS,
    FORBIDDEN_TOP_LEVEL_SHARED_CODE_DIRS,
)
from workspace_governance import Check


def _collect_leaked_env_files(root: Path) -> list[str]:
    leaked: list[str] = []
    for pattern in FORBIDDEN_TOP_LEVEL_PATTERNS:
        for candidate in root.glob(pattern):
            if candidate.name == workspace_env.TOP_LEVEL_ENV_EXAMPLE:
                continue
            if candidate.name == workspace_env.TOP_LEVEL_ENV_FILE:
                issues = workspace_env.env_file_issues(candidate)
                if not issues:
                    continue
                leaked.append(f"{candidate.name} ({'; '.join(issues)})")
                continue
            leaked.append(candidate.name)
    return leaked


def check_top_level_outputs(root: Path) -> list[Check]:
    checks: list[Check] = []
    leaked_files = _collect_leaked_env_files(root)
    if leaked_files:
        checks.append(
            Check(
                "ERROR",
                "top-level-secrets",
                f"Forbidden top-level env files: {', '.join(sorted(leaked_files))}",
            )
        )
    else:
        checks.append(Check("OK", "top-level-secrets", "No forbidden top-level env files found."))

    leaked_dirs = [name for name in FORBIDDEN_TOP_LEVEL_DIRS if (root / name).exists()]
    if leaked_dirs:
        checks.append(
            Check(
                "WARN",
                "top-level-artifacts",
                f"Top-level generated/data dirs found: {', '.join(leaked_dirs)}",
            )
        )
    else:
        checks.append(
            Check("OK", "top-level-artifacts", "No top-level data/cache/output dirs found.")
        )

    shared_code_files: list[str] = []
    for dirname in FORBIDDEN_TOP_LEVEL_SHARED_CODE_DIRS:
        shared_root = root / dirname
        if not shared_root.exists():
            continue
        shared_code_files.extend(
            path.relative_to(root).as_posix()
            for path in sorted(shared_root.rglob("*.py"))
            if path.is_file()
        )
    if shared_code_files:
        checks.append(
            Check(
                "ERROR",
                "top-level-shared-code",
                "Top-level shared Python code must move into an owning submodule/package: "
                + ", ".join(shared_code_files),
            )
        )
    else:
        checks.append(
            Check("OK", "top-level-shared-code", "No top-level shared Python code found.")
        )
    return checks
