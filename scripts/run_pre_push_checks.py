#!/usr/bin/env python3
"""Run the complete quality gate owned by the repository being pushed."""

from __future__ import annotations

import argparse
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from install_pre_push_hooks import check_installation
from run_submodule_checks import (
    DEFAULT_MANIFEST,
    ManifestError,
    SubmoduleConfig,
    load_manifest,
    plan_commands,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 1800


@dataclass(frozen=True)
class GateCommand:
    name: str
    cwd: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class GatePlan:
    repository: str
    repository_root: Path
    check_workspace_consistency: bool
    commands: tuple[GateCommand, ...]


@dataclass(frozen=True)
class PushedRef:
    local_ref: str
    local_oid: str
    remote_ref: str
    remote_oid: str
    line_number: int

    @property
    def is_deletion(self) -> bool:
        return bool(self.local_oid) and set(self.local_oid) == {"0"}


def parse_pushed_refs(payload: str) -> tuple[PushedRef, ...]:
    if not payload:
        return ()
    pushed_refs = []
    remote_refs = set()
    for line_number, line in enumerate(payload.splitlines(), start=1):
        fields = line.split()
        if len(fields) != 4:
            raise ManifestError(f"pre-push input line {line_number} must have four fields")
        local_ref, local_oid, remote_ref, remote_oid = fields
        if remote_ref in remote_refs:
            raise ManifestError(f"pre-push input repeats remote ref {remote_ref}")
        remote_refs.add(remote_ref)
        pushed_refs.append(
            PushedRef(local_ref, local_oid.lower(), remote_ref, remote_oid.lower(), line_number)
        )
    return tuple(pushed_refs)


def _root_gate_commands(root: Path) -> tuple[GateCommand, ...]:
    root_tests = tuple(
        "uv run --project strategy-pipeline --extra dev --with matplotlib>=3.8 "
        "--with tabulate>=0.9 python -m pytest tests -q".split()
    )
    return (
        GateCommand(
            "root-quality",
            root,
            (sys.executable, "scripts/run_quality_checks.py", "--profile", "hard"),
        ),
        GateCommand(
            "workspace-doctor",
            root,
            (sys.executable, "scripts/workspace_doctor.py"),
        ),
        GateCommand(
            "contract-smoke",
            root,
            (sys.executable, "src/research_contracts/smoke_contracts.py", "--strict"),
        ),
        GateCommand("root-tests", root, root_tests),
    )


def _matching_submodule(
    root: Path,
    repository: Path,
    configs: dict[str, SubmoduleConfig],
) -> str | None:
    matches = [
        name for name, config in configs.items() if (root / config.path).resolve() == repository
    ]
    if len(matches) > 1:
        raise ManifestError(f"multiple submodules resolve to {repository}")
    return matches[0] if matches else None


def plan_gate(
    root: Path,
    repository: Path,
    configs: dict[str, SubmoduleConfig],
) -> GatePlan:
    root = root.resolve()
    repository = repository.resolve()
    if repository == root:
        return GatePlan("research-workspace", root, True, _root_gate_commands(root))

    name = _matching_submodule(root, repository, configs)
    if name is None:
        raise ManifestError(f"repository is outside the managed workspace: {repository}")
    delegated = plan_commands(root, configs, profile="full", submodules=[name])
    commands = tuple(
        GateCommand(f"{name}:{index}", item.cwd, item.command)
        for index, item in enumerate(delegated, start=1)
    )
    if not commands:
        raise ManifestError(f"{name}.full expands to no commands")
    return GatePlan(name, repository, False, commands)


def _capture(command: tuple[str, ...], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)


def repository_head(repository: Path) -> str | None:
    completed = _capture(("git", "rev-parse", "--verify", "HEAD^{commit}"), cwd=repository)
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return completed.stdout.strip().lower()


def _valid_object_id(value: str, length: int) -> bool:
    return len(value) == length and all(character in string.hexdigits for character in value)


def _destination_issue(pushed_ref: PushedRef) -> str | None:
    if pushed_ref.remote_ref.startswith("refs/heads/"):
        if pushed_ref.remote_ref != "refs/heads/main":
            return "only remote branch refs/heads/main is allowed"
        if pushed_ref.is_deletion:
            return "deleting remote main is forbidden"
        return None
    if pushed_ref.remote_ref.startswith("refs/tags/"):
        return "deleting remote tags is forbidden" if pushed_ref.is_deletion else None
    return "only remote main and tags are allowed"


def _peel_commit(
    repository: Path,
    object_id: str,
    cache: dict[str, str | None],
) -> str | None:
    if object_id not in cache:
        completed = _capture(
            ("git", "rev-parse", "--verify", f"{object_id}^{{commit}}"),
            cwd=repository,
        )
        cache[object_id] = (
            completed.stdout.strip().lower()
            if completed.returncode == 0 and completed.stdout.strip()
            else None
        )
    return cache[object_id]


def _pushed_ref_issue(
    repository: Path,
    pushed_ref: PushedRef,
    *,
    expected_head: str,
    peeled_commits: dict[str, str | None],
) -> str | None:
    oid_length = len(expected_head)
    if not _valid_object_id(pushed_ref.local_oid, oid_length):
        return "invalid local object id"
    if not _valid_object_id(pushed_ref.remote_oid, oid_length):
        return "invalid remote object id"
    if (pushed_ref.local_ref == "(delete)") != pushed_ref.is_deletion:
        return "inconsistent deletion marker"
    if destination_issue := _destination_issue(pushed_ref):
        return destination_issue
    peeled = _peel_commit(repository, pushed_ref.local_oid, peeled_commits)
    if peeled is None:
        return "local object does not peel to a commit"
    if peeled != expected_head:
        return f"peeled commit {peeled} differs from HEAD {expected_head}"
    return None


def pushed_ref_issues(
    repository: Path,
    pushed_refs: tuple[PushedRef, ...],
    *,
    expected_head: str,
) -> list[str]:
    issues = []
    peeled_commits: dict[str, str | None] = {}
    for pushed_ref in pushed_refs:
        issue = _pushed_ref_issue(
            repository,
            pushed_ref,
            expected_head=expected_head,
            peeled_commits=peeled_commits,
        )
        if issue:
            issues.append(f"line {pushed_ref.line_number} ({pushed_ref.remote_ref}): {issue}")
    return issues


def validate_push_refs(
    repository: Path,
    pushed_refs: tuple[PushedRef, ...],
    *,
    expected_head: str | None,
) -> tuple[str | None, list[str]]:
    current_head = repository_head(repository)
    if current_head is None:
        return None, ["cannot resolve HEAD"]
    baseline_head = expected_head.lower() if expected_head else current_head
    if current_head != baseline_head:
        return baseline_head, [f"expected HEAD {baseline_head}, found {current_head}"]
    return baseline_head, pushed_ref_issues(
        repository,
        pushed_refs,
        expected_head=baseline_head,
    )


def _gitmodules_paths(root: Path) -> set[str] | None:
    completed = _capture(
        (
            "git",
            "config",
            "--file",
            ".gitmodules",
            "--get-regexp",
            r"^submodule\..*\.path$",
        ),
        cwd=root,
    )
    if completed.returncode != 0:
        return None
    return {
        line.split(maxsplit=1)[1].strip()
        for line in completed.stdout.splitlines()
        if len(line.split(maxsplit=1)) == 2
    }


def _submodule_consistency_issues(
    root: Path,
    name: str,
    config: SubmoduleConfig,
) -> list[str]:
    repository = (root / config.path).resolve()
    if not repository.is_dir():
        return [f"{name}: missing repository {repository}"]
    expected = _capture(
        ("git", "rev-parse", f"HEAD:{config.path.as_posix()}"),
        cwd=root,
    )
    actual = _capture(("git", "rev-parse", "HEAD"), cwd=repository)
    issues: list[str] = []
    if expected.returncode != 0:
        issues.append(f"{name}: superproject HEAD has no gitlink")
    elif actual.returncode != 0:
        issues.append(f"{name}: cannot resolve submodule HEAD")
    elif expected.stdout.strip() != actual.stdout.strip():
        issues.append(f"{name}: checked-out HEAD differs from the superproject gitlink")
    status = _capture(("git", "status", "--porcelain=v1"), cwd=repository)
    if status.returncode != 0:
        issues.append(f"{name}: git status failed")
    elif status.stdout.strip():
        issues.append(f"{name}: working tree is dirty")
    return issues


def workspace_consistency_issues(
    root: Path,
    configs: dict[str, SubmoduleConfig],
) -> list[str]:
    root = root.resolve()
    manifest_paths = {config.path.as_posix() for config in configs.values()}
    gitmodule_paths = _gitmodules_paths(root)
    if gitmodule_paths is None:
        return ["cannot read .gitmodules paths"]
    issues = []
    if manifest_paths != gitmodule_paths:
        issues.append(".gitmodules paths differ from scripts/submodule_checks.json")
    for name in sorted(configs):
        issues.extend(_submodule_consistency_issues(root, name, configs[name]))
    return issues


def repository_clean_issue(repository: Path) -> str | None:
    status = _capture(("git", "status", "--porcelain=v1"), cwd=repository)
    if status.returncode != 0:
        return "git status failed"
    if status.stdout.strip():
        return "working tree is dirty; commit or discard changes before push"
    return None


def _display(command: tuple[str, ...]) -> str:
    return " ".join(command)


def _post_gate_state_issues(
    plan: GatePlan,
    *,
    root: Path,
    configs: dict[str, SubmoduleConfig],
    expected_head: str,
) -> list[str]:
    issues = []
    final_head = repository_head(plan.repository_root)
    if final_head is None:
        issues.append("cannot resolve HEAD after quality commands")
    elif final_head != expected_head:
        issues.append(f"HEAD changed from {expected_head} to {final_head}")
    clean_issue = repository_clean_issue(plan.repository_root)
    if clean_issue:
        issues.append(clean_issue)
    if plan.check_workspace_consistency:
        issues.extend(workspace_consistency_issues(root, configs))
    return issues


def _report_issues(label: str, issues: list[str]) -> bool:
    for issue in issues:
        print(f"[ERROR] {label}: {issue}", file=sys.stderr)
    return bool(issues)


def _render_dry_run(plan: GatePlan, pushed_refs: tuple[PushedRef, ...]) -> int:
    print(f"[DRY-RUN] push-refs: validate {len(pushed_refs)} update(s) against HEAD")
    print("[DRY-RUN] hook-installation: validate all managed repositories")
    print(f"[DRY-RUN] repository-head: snapshot and recheck {plan.repository_root}")
    print(f"[DRY-RUN] repository-clean: validate {plan.repository_root}")
    if plan.check_workspace_consistency:
        print("[DRY-RUN] workspace-consistency: validate gitlinks and clean submodules")
    for item in plan.commands:
        print(f"[DRY-RUN] {item.name}: ({item.cwd}) {_display(item.command)}")
    print("[DRY-RUN] final-state: recheck HEAD, clean worktree, and applicable consistency")
    return 0


def _validated_baseline_head(
    plan: GatePlan,
    pushed_refs: tuple[PushedRef, ...],
    expected_head: str | None,
) -> str | None:
    baseline_head, issues = validate_push_refs(
        plan.repository_root,
        pushed_refs,
        expected_head=expected_head,
    )
    if _report_issues("push-refs", issues) or baseline_head is None:
        return None
    print(f"[OK] push-refs: {len(pushed_refs)} update(s)")
    return baseline_head


def _pre_gate_state_is_valid(
    plan: GatePlan,
    *,
    root: Path,
    configs: dict[str, SubmoduleConfig],
) -> bool:
    if _report_issues("hook-installation", check_installation(root, configs)):
        return False
    print("[OK] hook-installation")
    if clean_issue := repository_clean_issue(plan.repository_root):
        return not _report_issues("repository-clean", [clean_issue])
    print("[OK] repository-clean")
    if plan.check_workspace_consistency:
        if _report_issues("workspace-consistency", workspace_consistency_issues(root, configs)):
            return False
        print("[OK] workspace-consistency")
    return True


def _run_gate_commands(commands: tuple[GateCommand, ...], *, timeout: int) -> bool:
    for item in commands:
        print(f"[RUN] {item.name}: {_display(item.command)}", flush=True)
        try:
            completed = subprocess.run(item.command, cwd=item.cwd, check=False, timeout=timeout)
        except (FileNotFoundError, PermissionError) as exc:
            print(f"[ERROR] {item.name}: {exc}", file=sys.stderr)
            return False
        except subprocess.TimeoutExpired:
            print(f"[ERROR] {item.name}: timed out after {timeout}s", file=sys.stderr)
            return False
        if completed.returncode != 0:
            print(f"[ERROR] {item.name}: exit code {completed.returncode}", file=sys.stderr)
            return False
        print(f"[OK] {item.name}")
    return True


def run_gate(
    plan: GatePlan,
    *,
    root: Path,
    configs: dict[str, SubmoduleConfig],
    timeout: int,
    dry_run: bool,
    pushed_refs: tuple[PushedRef, ...] = (),
    expected_head: str | None = None,
) -> int:
    if dry_run:
        return _render_dry_run(plan, pushed_refs)
    baseline_head = _validated_baseline_head(plan, pushed_refs, expected_head)
    if baseline_head is None or not _pre_gate_state_is_valid(plan, root=root, configs=configs):
        return 1

    commands_passed = _run_gate_commands(plan.commands, timeout=timeout)
    post_issues = _post_gate_state_issues(
        plan,
        root=root,
        configs=configs,
        expected_head=baseline_head,
    )
    post_state_passed = not _report_issues("final-state", post_issues)
    if post_state_passed:
        print("[OK] final-state")
    return 0 if commands_passed and post_state_passed else 1


def _repository_root(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    completed = _capture(("git", "rev-parse", "--show-toplevel"), cwd=Path.cwd())
    if completed.returncode != 0 or not completed.stdout.strip():
        raise ManifestError("cannot resolve the repository being pushed")
    return Path(completed.stdout.strip()).resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--expected-head")
    parser.add_argument("--validate-push-refs-only", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        root = Path(args.root).expanduser().resolve()
        configs = load_manifest(Path(args.manifest).expanduser().resolve())
        plan = plan_gate(root, _repository_root(args.repository), configs)
        payload = "" if args.dry_run and sys.stdin.isatty() else sys.stdin.read()
        pushed_refs = parse_pushed_refs(payload)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.validate_push_refs_only:
        _, issues = validate_push_refs(
            plan.repository_root,
            pushed_refs,
            expected_head=args.expected_head,
        )
        if issues:
            for issue in issues:
                print(f"[ERROR] push-refs: {issue}", file=sys.stderr)
            return 1
        print(f"[OK] push-refs preflight: {len(pushed_refs)} update(s)")
        return 0
    print(f"Pre-push gate: repository={plan.repository}")
    return run_gate(
        plan,
        root=root,
        configs=configs,
        timeout=args.timeout,
        dry_run=args.dry_run,
        pushed_refs=pushed_refs,
        expected_head=args.expected_head,
    )


if __name__ == "__main__":
    raise SystemExit(main())
