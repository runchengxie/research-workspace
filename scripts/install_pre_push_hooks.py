#!/usr/bin/env python3
"""Install or inspect the shared pre-push hook in all managed repositories."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from run_submodule_checks import DEFAULT_MANIFEST, ManifestError, SubmoduleConfig, load_manifest

ROOT = Path(__file__).resolve().parents[1]
HOOKS_RELATIVE_PATH = Path(".githooks")
REQUIRED_SHARED_HOOKS = ("pre-commit", "pre-push")


@dataclass(frozen=True)
class HookTarget:
    name: str
    repository: Path


def hook_targets(
    root: Path,
    configs: dict[str, SubmoduleConfig],
    *,
    workspace_root: Path | None = None,
) -> tuple[HookTarget, ...]:
    root = root.resolve()
    # Default to the superproject root so `install_pre_push_hooks` behaves
    # identically to before when invoked directly (e.g. from the main work
    # tree or from tests). The pre-push gate passes the actual linked-worktree
    # root explicitly via `workspace_root` so hooksPath resolves correctly there.
    if workspace_root is None:
        workspace_root = root
    workspace_root = workspace_root.resolve()
    targets = [HookTarget("research-workspace", workspace_root)]
    targets.extend(
        HookTarget(name, (workspace_root / configs[name].path).resolve())
        for name in sorted(configs)
    )
    return tuple(targets)


def _git(
    repository: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(repository), *args),
        check=False,
        capture_output=True,
        text=True,
    )


def _repository_issue(target: HookTarget) -> str | None:
    if not target.repository.is_dir():
        return f"repository is missing: {target.repository}"
    completed = _git(target.repository, "rev-parse", "--show-toplevel")
    if completed.returncode != 0 or not completed.stdout.strip():
        return f"not a Git repository: {target.repository}"
    actual = Path(completed.stdout.strip()).resolve()
    if actual != target.repository.resolve():
        return f"repository resolves to {actual}, expected {target.repository.resolve()}"
    return None


def _absolute_git_dir(target: HookTarget) -> Path | None:
    completed = _git(target.repository, "rev-parse", "--absolute-git-dir")
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return Path(completed.stdout.strip()).resolve()


def _configured_hooks_path(target: HookTarget) -> Path | None:
    completed = _git(target.repository, "config", "--local", "--get", "core.hooksPath")
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    configured = Path(completed.stdout.strip()).expanduser()
    if not configured.is_absolute():
        configured = target.repository / configured
    return configured.resolve()


def _shared_hook_issues(root: Path) -> list[str]:
    hooks = root / HOOKS_RELATIVE_PATH
    issues = []
    for name in REQUIRED_SHARED_HOOKS:
        hook = hooks / name
        if not hook.is_file():
            issues.append(f"tracked hook is missing: {hook}")
        elif not os.access(hook, os.X_OK):
            issues.append(f"tracked hook is not executable: {hook}")
    return issues


def _owner_native_hooks(root: Path, target: HookTarget) -> tuple[Path, ...]:
    shared = (root / HOOKS_RELATIVE_PATH).resolve()
    native_root = (target.repository / ".githooks").resolve()
    candidates = []
    if native_root != shared:
        candidates.extend(
            native_root / name for name in REQUIRED_SHARED_HOOKS if (native_root / name).is_file()
        )
    git_dir = _absolute_git_dir(target)
    if git_dir is not None:
        default_hooks = git_dir / "hooks"
        candidates.extend(
            default_hooks / name
            for name in REQUIRED_SHARED_HOOKS
            if (default_hooks / name).is_file() and os.access(default_hooks / name, os.X_OK)
        )
    unique: dict[Path, Path] = {}
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved != shared / candidate.name:
            unique.setdefault(resolved, candidate)
    return tuple(unique.values())


def _target_mode(root: Path, target: HookTarget) -> str:
    return "managed+owner-native-chained" if _owner_native_hooks(root, target) else "managed-shared"


def _configuration_conflict(root: Path, target: HookTarget) -> str | None:
    configured = _configured_hooks_path(target)
    expected = (root / HOOKS_RELATIVE_PATH).resolve()
    if configured is None or configured == expected:
        return None
    return f"core.hooksPath={configured} conflicts with managed path {expected}"


def check_installation(
    root: Path,
    configs: dict[str, SubmoduleConfig],
    *,
    workspace_root: Path | None = None,
) -> list[str]:
    root = root.resolve()
    issues = _shared_hook_issues(root)
    expected = (root / HOOKS_RELATIVE_PATH).resolve()
    for target in hook_targets(root, configs, workspace_root=workspace_root):
        repository_issue = _repository_issue(target)
        if repository_issue:
            issues.append(f"{target.name}: {repository_issue}")
            continue
        configured = _configured_hooks_path(target)
        if configured != expected:
            value = "unset" if configured is None else str(configured)
            issues.append(f"{target.name}: core.hooksPath={value}, expected {expected}")
        for native_hook in _owner_native_hooks(root, target):
            if not os.access(native_hook, os.X_OK):
                issues.append(f"{target.name}: owner-native hook is not executable: {native_hook}")
    return issues


def install_hooks(
    root: Path,
    configs: dict[str, SubmoduleConfig],
    *,
    dry_run: bool,
    workspace_root: Path | None = None,
) -> int:
    root = root.resolve()
    hook_issues = _shared_hook_issues(root)
    if hook_issues:
        for issue in hook_issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    targets = hook_targets(root, configs, workspace_root=workspace_root)
    repository_issues = [
        f"{target.name}: {issue}"
        for target in targets
        if (issue := _repository_issue(target)) is not None
    ]
    if repository_issues:
        for issue in repository_issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1

    configuration_conflicts = [
        f"{target.name}: {conflict}"
        for target in targets
        if (conflict := _configuration_conflict(root, target)) is not None
    ]
    if configuration_conflicts:
        for issue in configuration_conflicts:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1

    for target in targets:
        # 使用相对路径指向顶层共享钩子，使 linked worktree 也能解析正确
        # （绝对路径会把钩子绑定到某个固定工作树，导致 worktree 推送被守卫拦截）
        relative = os.path.relpath(root / HOOKS_RELATIVE_PATH, target.repository)
        command = ("git", "config", "--local", "core.hooksPath", str(relative))
        mode = _target_mode(root, target)
        if dry_run:
            print(f"[DRY-RUN] {target.name} [{mode}]: ({target.repository}) {' '.join(command)}")
            continue
        completed = _git(
            target.repository,
            "config",
            "--local",
            "core.hooksPath",
            str(relative),
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            print(f"[ERROR] {target.name}: {detail or 'git config failed'}", file=sys.stderr)
            return 1
        print(f"[OK] {target.name} [{mode}]: core.hooksPath={relative}")
    return 0


def _render_check(root: Path, configs: dict[str, SubmoduleConfig]) -> int:
    issues = check_installation(root, configs)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1
    for target in hook_targets(root, configs):
        print(f"[OK] {target.name} [{_target_mode(root, target)}]: hooks installed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        configs = load_manifest(Path(args.manifest).expanduser().resolve())
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser().resolve()
    if args.check:
        return _render_check(root, configs)
    return install_hooks(root, configs, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
