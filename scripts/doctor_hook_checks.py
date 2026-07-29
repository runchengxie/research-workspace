"""Local git hooks installation checks for the superproject and submodules."""

from __future__ import annotations

import os
from pathlib import Path

from doctor_common import (
    EXPECTED_SUBMODULES,
    SHARED_HOOK_NAMES,
    _configured_hooks_path,
    _repository_toplevel,
)
from workspace_governance import Check


def check_local_git_hooks(root: Path) -> list[Check]:
    expected = (root / ".githooks").resolve()
    issues: list[str] = [
        f"{name} is missing or not executable"
        for name in SHARED_HOOK_NAMES
        if not (expected / name).is_file() or not os.access(expected / name, os.X_OK)
    ]
    targets = {"research-workspace": root}
    targets.update({name: root / name for name in EXPECTED_SUBMODULES})
    for name, repository in targets.items():
        actual = _repository_toplevel(repository)
        if actual != repository.resolve():
            value = "not a Git worktree" if actual is None else f"resolves to {actual}"
            issues.append(f"{name} is {value}, expected {repository.resolve()}")
            continue
        configured = _configured_hooks_path(repository)
        if configured != expected:
            value = "unset" if configured is None else str(configured)
            issues.append(f"{name} has core.hooksPath={value}")
    if issues:
        return [
            Check(
                "WARN",
                "local-git-hooks",
                "; ".join(issues)
                + ". Run python scripts/install_pre_push_hooks.py and then --check.",
            )
        ]
    return [
        Check(
            "OK",
            "local-git-hooks",
            "Shared local hooks are installed for the superproject and all submodules.",
        )
    ]
