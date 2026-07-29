"""Submodule initialization and cleanliness checks."""

from __future__ import annotations

from pathlib import Path

from doctor_common import EXPECTED_SUBMODULES, _git_status_short
from workspace_governance import Check


def check_submodule_state(root: Path) -> list[Check]:
    checks: list[Check] = []
    for path in EXPECTED_SUBMODULES:
        repo = root / path
        if not repo.exists():
            checks.append(Check("ERROR", "submodule-init", f"{path} is missing."))
            continue
        if not (repo / ".git").exists():
            checks.append(Check("ERROR", "submodule-init", f"{path} is not initialized."))
            continue
        code, stdout, stderr = _git_status_short(repo)
        if code != 0:
            detail = stderr or "git status failed"
            checks.append(Check("WARN", "submodule-status", f"{path}: {detail}"))
        elif stdout:
            checks.append(Check("WARN", "submodule-dirty", f"{path} has local changes."))
        else:
            checks.append(Check("OK", "submodule-clean", f"{path} is clean."))
    return checks
