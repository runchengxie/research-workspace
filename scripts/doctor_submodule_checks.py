"""Submodule initialization and cleanliness checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from doctor_common import EXPECTED_SUBMODULES, _git_status_short
from workspace_governance import Check


def _git_rev_list_behind(path: Path, base: str) -> int | None:
    """返回 path 的 HEAD 落后 base 的提交数；base 不存在时返回 None。"""
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-list", "--count", f"HEAD..{base}"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return None


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


def check_submodule_freshness(root: Path) -> list[Check]:
    """检查子模块 gitlink 是否落后于各自 origin/main，提前发现指针漂移。"""
    checks: list[Check] = []
    for path in EXPECTED_SUBMODULES:
        repo = root / path
        if not (repo / ".git").exists():
            continue
        behind = _git_rev_list_behind(repo, "origin/main")
        if behind is None:
            checks.append(
                Check(
                    "WARN",
                    "submodule-freshness",
                    f"{path}: 本地无 origin/main 引用，先 git fetch 再判断指针是否漂移。",
                )
            )
        elif behind > 0:
            checks.append(
                Check(
                    "WARN",
                    "submodule-freshness",
                    f"{path}: 指针落后 origin/main 共 {behind} 个提交，提交前先更新 gitlink。",
                )
            )
        else:
            checks.append(Check("OK", "submodule-freshness", f"{path} 指针与 origin/main 同步。"))
    return checks
