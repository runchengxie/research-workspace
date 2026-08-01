from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

run_pre_push_checks = importlib.import_module("run_pre_push_checks")
run_submodule_checks = importlib.import_module("run_submodule_checks")


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ("git", "init", "-q"),
        cwd=path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def _commit_file(path: Path, name: str = "tracked.txt", content: str = "tracked\n") -> str:
    (path / name).write_text(content, encoding="utf-8")
    subprocess.run(("git", "add", name), cwd=path, check=True)
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-q",
            "-m",
            f"commit {name}",
        ),
        cwd=path,
        check=True,
    )
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _allow_installed_hooks(monkeypatch: object) -> None:
    monkeypatch.setattr(run_pre_push_checks, "check_installation", lambda *_a, **_k: [])


def test_root_gate_runs_root_quality_and_cross_repo_checks_only() -> None:
    configs = run_submodule_checks.load_manifest(ROOT / "scripts/submodule_checks.json")

    plan = run_pre_push_checks.plan_gate(ROOT, ROOT, configs)

    assert plan.repository == "research-workspace"
    assert plan.repository_root == ROOT
    assert plan.check_workspace_consistency is True
    assert [command.name for command in plan.commands] == [
        "root-quality",
        "workspace-doctor",
        "contract-smoke",
        "root-tests",
    ]
    assert all(command.cwd == ROOT for command in plan.commands)


def test_submodule_gate_expands_only_that_repositories_full_profile() -> None:
    configs = run_submodule_checks.load_manifest(ROOT / "scripts/submodule_checks.json")
    repository = ROOT / "alpha-research"

    plan = run_pre_push_checks.plan_gate(ROOT, repository, configs)
    expected = run_submodule_checks.plan_commands(
        ROOT,
        configs,
        profile="full",
        submodules=["alpha-research"],
    )

    assert plan.repository == "alpha-research"
    assert plan.repository_root == repository
    assert plan.check_workspace_consistency is False
    assert [command.command for command in plan.commands] == [item.command for item in expected]
    assert {command.cwd for command in plan.commands} == {repository}


def _pushed_ref(
    local_ref: str,
    local_oid: str,
    remote_ref: str,
    remote_oid: str | None = None,
    *,
    line_number: int = 1,
) -> run_pre_push_checks.PushedRef:
    return run_pre_push_checks.PushedRef(
        local_ref,
        local_oid,
        remote_ref,
        remote_oid or ("0" * len(local_oid)),
        line_number,
    )


def test_push_ref_policy_accepts_current_head_and_rejects_other_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    old_head = _commit_file(repository, content="old\n")
    current_head = _commit_file(repository, "second.txt", "current\n")

    current = (_pushed_ref("refs/heads/main", current_head, "refs/heads/main"),)
    other = (_pushed_ref("refs/heads/main", old_head, "refs/heads/main"),)

    assert (
        run_pre_push_checks.pushed_ref_issues(
            repository,
            current,
            expected_head=current_head,
        )
        == []
    )
    issues = run_pre_push_checks.pushed_ref_issues(
        repository,
        other,
        expected_head=current_head,
    )
    assert any("differs from HEAD" in issue for issue in issues)


def test_push_ref_policy_accepts_annotated_head_tag(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    head = _commit_file(repository)
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.invalid",
            "tag",
            "-a",
            "v1",
            "-m",
            "v1",
        ),
        cwd=repository,
        check=True,
    )
    tag_oid = subprocess.run(
        ("git", "rev-parse", "refs/tags/v1"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    issues = run_pre_push_checks.pushed_ref_issues(
        repository,
        (_pushed_ref("refs/tags/v1", tag_oid, "refs/tags/v1"),),
        expected_head=head,
    )

    assert issues == []


def test_push_ref_policy_accepts_main_and_head_tag_in_one_push(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    head = _commit_file(repository)
    pushed_refs = (
        _pushed_ref("refs/heads/main", head, "refs/heads/main", line_number=1),
        _pushed_ref("refs/tags/v1", head, "refs/tags/v1", line_number=2),
    )

    assert (
        run_pre_push_checks.pushed_ref_issues(
            repository,
            pushed_refs,
            expected_head=head,
        )
        == []
    )


def test_push_ref_policy_rejects_other_branch_and_remote_main_deletion(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    head = _commit_file(repository)
    zeros = "0" * len(head)
    pushed_refs = (
        _pushed_ref("refs/heads/topic", head, "refs/heads/topic", line_number=1),
        _pushed_ref("(delete)", zeros, "refs/heads/main", head, line_number=2),
    )

    issues = run_pre_push_checks.pushed_ref_issues(
        repository,
        pushed_refs,
        expected_head=head,
    )

    assert any(
        "only refs/heads/main or refs/heads/{feat,fix,hotfix,release}/* are allowed" in issue
        for issue in issues
    )
    assert any("deleting remote main is forbidden" in issue for issue in issues)


def test_destination_issue_allows_main_and_feature_prefixes() -> None:
    head = "a" * 40

    # main push allowed
    assert (
        run_pre_push_checks._destination_issue(
            _pushed_ref("refs/heads/main", head, "refs/heads/main")
        )
        is None
    )
    # allowed feature-prefix branches allowed (for PR flow)
    for prefix in ("feat", "fix", "hotfix", "release"):
        assert (
            run_pre_push_checks._destination_issue(
                _pushed_ref(
                    f"refs/heads/{prefix}/thing",
                    head,
                    f"refs/heads/{prefix}/thing",
                )
            )
            is None
        )


def test_destination_issue_rejects_unprefixed_branch() -> None:
    head = "a" * 40

    issue = run_pre_push_checks._destination_issue(
        _pushed_ref("refs/heads/topic", head, "refs/heads/topic")
    )
    assert issue is not None
    assert "refs/heads/{feat,fix,hotfix,release}/*" in issue


def test_destination_issue_forbids_deleting_main_and_feature_and_tag() -> None:
    head = "a" * 40
    zeros = "0" * 40

    main_del = run_pre_push_checks._destination_issue(
        _pushed_ref("(delete)", zeros, "refs/heads/main", head)
    )
    assert main_del == "deleting remote main is forbidden"

    feat_del = run_pre_push_checks._destination_issue(
        _pushed_ref("(delete)", zeros, "refs/heads/feat/thing", head)
    )
    assert feat_del is not None
    assert "deleting remote branch refs/heads/feat/thing is forbidden" in feat_del

    tag_del = run_pre_push_checks._destination_issue(
        _pushed_ref("(delete)", zeros, "refs/tags/v1", head)
    )
    assert tag_del == "deleting remote tags is forbidden"


def test_parse_pushed_refs_preserves_multiple_updates_and_rejects_duplicates() -> None:
    oid = "a" * 40
    zeros = "0" * 40
    payload = (
        f"refs/heads/main {oid} refs/heads/main {zeros}\nrefs/tags/v1 {oid} refs/tags/v1 {zeros}\n"
    )

    parsed = run_pre_push_checks.parse_pushed_refs(payload)

    assert [item.remote_ref for item in parsed] == ["refs/heads/main", "refs/tags/v1"]
    with pytest.raises(run_submodule_checks.ManifestError):
        run_pre_push_checks.parse_pushed_refs(
            f"refs/heads/main {oid} refs/heads/main {zeros}\nHEAD {oid} refs/heads/main {zeros}\n"
        )


def test_dirty_repository_blocks_before_any_quality_command(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    _commit_file(repository)
    _allow_installed_hooks(monkeypatch)
    (repository / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    marker = tmp_path / "command-ran"
    plan = run_pre_push_checks.GatePlan(
        "example",
        repository,
        False,
        (
            run_pre_push_checks.GateCommand(
                "must-not-run",
                repository,
                (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"),
            ),
        ),
    )

    result = run_pre_push_checks.run_gate(
        plan,
        root=tmp_path,
        configs={},
        timeout=10,
        dry_run=False,
    )

    assert result == 1
    assert not marker.exists()


def test_failed_quality_command_stops_the_gate(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    _commit_file(repository)
    _allow_installed_hooks(monkeypatch)
    marker = tmp_path / "second-command-ran"
    plan = run_pre_push_checks.GatePlan(
        "example",
        repository,
        False,
        (
            run_pre_push_checks.GateCommand(
                "fail",
                repository,
                (sys.executable, "-c", "raise SystemExit(7)"),
            ),
            run_pre_push_checks.GateCommand(
                "must-not-run",
                repository,
                (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"),
            ),
        ),
    )

    result = run_pre_push_checks.run_gate(
        plan,
        root=tmp_path,
        configs={},
        timeout=10,
        dry_run=False,
    )

    assert result == 1
    assert not marker.exists()


def test_missing_hook_installation_blocks_before_quality_commands(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    _commit_file(repository)
    marker = tmp_path / "command-ran"
    monkeypatch.setattr(
        run_pre_push_checks,
        "check_installation",
        lambda *_a, **_k: ["hooks are not installed"],
    )
    plan = run_pre_push_checks.GatePlan(
        "example",
        repository,
        False,
        (
            run_pre_push_checks.GateCommand(
                "must-not-run",
                repository,
                (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"),
            ),
        ),
    )

    result = run_pre_push_checks.run_gate(
        plan,
        root=tmp_path,
        configs={},
        timeout=10,
        dry_run=False,
    )

    assert result == 1
    assert not marker.exists()


def test_successful_command_that_dirties_repo_is_blocked_by_final_state(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    _commit_file(repository)
    _allow_installed_hooks(monkeypatch)
    marker = repository / "created-by-check.txt"
    plan = run_pre_push_checks.GatePlan(
        "example",
        repository,
        False,
        (
            run_pre_push_checks.GateCommand(
                "dirty",
                repository,
                (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"),
            ),
        ),
    )

    result = run_pre_push_checks.run_gate(
        plan,
        root=tmp_path,
        configs={},
        timeout=10,
        dry_run=False,
    )

    assert result == 1
    assert marker.is_file()


def test_successful_command_that_moves_head_is_blocked_by_final_state(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    _commit_file(repository)
    _commit_file(repository, "second.txt", "second\n")
    _allow_installed_hooks(monkeypatch)
    plan = run_pre_push_checks.GatePlan(
        "example",
        repository,
        False,
        (
            run_pre_push_checks.GateCommand(
                "move-head", repository, ("git", "reset", "--hard", "HEAD~")
            ),
        ),
    )

    result = run_pre_push_checks.run_gate(
        plan,
        root=tmp_path,
        configs={},
        timeout=10,
        dry_run=False,
    )

    assert result == 1


def test_dry_run_does_not_require_clean_repo_or_execute_commands(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    _init_repo(repository)
    (repository / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
    marker = tmp_path / "command-ran"
    plan = run_pre_push_checks.GatePlan(
        "example",
        repository,
        False,
        (
            run_pre_push_checks.GateCommand(
                "must-not-run",
                repository,
                (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"),
            ),
        ),
    )

    result = run_pre_push_checks.run_gate(
        plan,
        root=tmp_path,
        configs={},
        timeout=10,
        dry_run=True,
    )

    assert result == 0
    assert not marker.exists()


def test_is_same_git_repo_distinguishes_worktree_from_separate_repo(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-a"
    _init_repo(repo_a)
    _commit_file(repo_a, content="a\n")

    worktree_b = tmp_path / "worktree-b"
    subprocess.run(
        ("git", "worktree", "add", "-q", str(worktree_b), "HEAD"),
        cwd=repo_a,
        check=True,
    )

    repo_c = tmp_path / "repo-c"
    _init_repo(repo_c)
    _commit_file(repo_c, content="c\n")

    assert run_pre_push_checks._is_same_git_repo(repo_a, worktree_b) is True
    assert run_pre_push_checks._is_same_git_repo(repo_a, repo_c) is False
    assert run_pre_push_checks._is_same_git_repo(repo_a, repo_a) is True


def test_plan_gate_treats_superproject_worktree_as_root(
    monkeypatch: object,
) -> None:
    configs = run_submodule_checks.load_manifest(ROOT / "scripts/submodule_checks.json")
    fake_worktree = ROOT / "some-fake-worktree"
    monkeypatch.setattr(run_pre_push_checks, "_is_same_git_repo", lambda _a, _b: True)

    plan = run_pre_push_checks.plan_gate(ROOT, fake_worktree, configs)

    assert plan.repository == "research-workspace"
    assert plan.repository_root == fake_worktree
    assert plan.check_workspace_consistency is True
    assert [command.name for command in plan.commands] == [
        "root-quality",
        "workspace-doctor",
        "contract-smoke",
        "root-tests",
    ]
    assert all(command.cwd == fake_worktree for command in plan.commands)
