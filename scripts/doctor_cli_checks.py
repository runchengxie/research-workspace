"""Public CLI contract checks for workspace-level submodules."""

from __future__ import annotations

import os
from pathlib import Path

from doctor_common import (
    EXPECTED_SUBMODULES,
    _has_valid_shebang,
    _public_command_candidates,
    resolve_public_command,
)
from workspace_governance import Check


def check_public_clis(root: Path) -> list[Check]:
    checks: list[Check] = []
    for path, command in EXPECTED_SUBMODULES.items():
        if command is None:
            checks.append(Check("OK", "cli", f"{path} has no workspace-level CLI contract."))
            continue
        resolved = resolve_public_command(root, path, command)
        if resolved:
            checks.append(Check("OK", "cli", f"{command} resolves to {resolved}."))
        else:
            existing = [
                candidate
                for candidate in _public_command_candidates(root, path, command)
                if candidate.is_file()
            ]
            broken = [
                candidate
                for candidate in existing
                if not os.access(candidate, os.X_OK) or not _has_valid_shebang(candidate)
            ]
            if broken:
                checks.append(
                    Check(
                        "WARN",
                        "cli",
                        f"{command} entrypoint exists but is not runnable: {broken[0]}",
                    )
                )
                continue
            checks.append(
                Check(
                    "WARN",
                    "cli",
                    f"{command} is not on PATH and no {path}/.venv command was found.",
                )
            )
    return checks
