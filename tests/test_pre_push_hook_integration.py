from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

install_pre_push_hooks = importlib.import_module("install_pre_push_hooks")
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


def _config(name: str) -> run_submodule_checks.SubmoduleConfig:
    return run_submodule_checks.SubmoduleConfig(
        name=name,
        path=Path(name),
        profiles={
            "smoke": [[sys.executable, "-c", "pass"]],
            "lint": [[sys.executable, "-c", "pass"]],
            "type": [[sys.executable, "-c", "pass"]],
            "test": [[sys.executable, "-c", "pass"]],
            "full": ["@smoke", "@lint", "@type", "@test"],
        },
    )


def _copy_shared_hooks(root: Path) -> None:
    hooks = root / ".githooks"
    hooks.mkdir(parents=True)
    for name in ("pre-commit", "pre-push"):
        shutil.copy2(ROOT / ".githooks" / name, hooks / name)
        (hooks / name).chmod(0o755)


def _write_hook(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body, encoding="utf-8")
    path.chmod(0o755)


def test_installer_dry_run_install_and_check_preserve_native_hooks(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    _init_repo(root)
    _copy_shared_hooks(root)
    configs = {name: _config(name) for name in ("native", "plain")}
    for name in configs:
        _init_repo(root / name)
    native_pre_commit = root / "native/.githooks/pre-commit"
    native_pre_push = root / "native/.githooks/pre-push"
    _write_hook(native_pre_commit, "exit 0\n")
    _write_hook(native_pre_push, "exit 0\n")

    assert install_pre_push_hooks.install_hooks(root, configs, dry_run=True) == 0
    for target in install_pre_push_hooks.hook_targets(root, configs):
        assert install_pre_push_hooks._configured_hooks_path(target) is None

    assert install_pre_push_hooks.install_hooks(root, configs, dry_run=False) == 0
    assert install_pre_push_hooks.check_installation(root, configs) == []
    targets = {target.name: target for target in install_pre_push_hooks.hook_targets(root, configs)}
    assert install_pre_push_hooks._target_mode(root, targets["native"]) == (
        "managed+owner-native-chained"
    )
    assert install_pre_push_hooks._target_mode(root, targets["plain"]) == "managed-shared"
    assert native_pre_commit.is_file()
    assert native_pre_push.is_file()

    subprocess.run(
        ("git", "-C", str(root / "plain"), "config", "--local", "--unset", "core.hooksPath"),
        check=True,
    )
    issues = install_pre_push_hooks.check_installation(root, configs)
    assert any("plain: core.hooksPath=unset" in issue for issue in issues)


def test_installer_rejects_nested_directory_that_resolves_to_parent_repo(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    _init_repo(root)
    _copy_shared_hooks(root)
    configs = {"uninitialized": _config("uninitialized")}
    (root / "uninitialized").mkdir()

    result = install_pre_push_hooks.install_hooks(root, configs, dry_run=False)

    assert result == 1
    target = install_pre_push_hooks.HookTarget("research-workspace", root)
    assert install_pre_push_hooks._configured_hooks_path(target) is None
    issue = install_pre_push_hooks._repository_issue(
        install_pre_push_hooks.HookTarget("uninitialized", root / "uninitialized")
    )
    assert issue is not None
    assert "resolves to" in issue


def test_installer_rejects_non_managed_hooks_path_without_partial_writes(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    _init_repo(root)
    _copy_shared_hooks(root)
    configs = {"plain": _config("plain")}
    _init_repo(root / "plain")
    subprocess.run(
        (
            "git",
            "-C",
            str(root / "plain"),
            "config",
            "--local",
            "core.hooksPath",
            "custom-hooks",
        ),
        check=True,
    )

    result = install_pre_push_hooks.install_hooks(root, configs, dry_run=False)

    assert result == 1
    targets = {target.name: target for target in install_pre_push_hooks.hook_targets(root, configs)}
    assert install_pre_push_hooks._configured_hooks_path(targets["research-workspace"]) is None
    assert (
        install_pre_push_hooks._configured_hooks_path(targets["plain"])
        == (root / "plain/custom-hooks").resolve()
    )


def test_installer_preserves_executable_default_git_hook_for_shared_chaining(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    _init_repo(root)
    _copy_shared_hooks(root)
    configs = {"plain": _config("plain")}
    _init_repo(root / "plain")
    git_dir = subprocess.run(
        ("git", "-C", str(root / "plain"), "rev-parse", "--absolute-git-dir"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    default_hook = Path(git_dir) / "hooks/pre-push"
    _write_hook(default_hook, "exit 0\n")

    result = install_pre_push_hooks.install_hooks(root, configs, dry_run=False)

    assert result == 0
    assert install_pre_push_hooks.check_installation(root, configs) == []
    targets = {target.name: target for target in install_pre_push_hooks.hook_targets(root, configs)}
    assert install_pre_push_hooks._target_mode(root, targets["plain"]) == (
        "managed+owner-native-chained"
    )
    assert default_hook.is_file()


def _prepare_hook_execution(
    tmp_path: Path,
    *,
    native_exit: int | None,
) -> tuple[Path, dict[str, str]]:
    workspace = tmp_path / "workspace"
    repository = workspace / "repo"
    _copy_shared_hooks(workspace)
    _init_repo(repository)
    _commit_file(repository)
    scripts = workspace / "scripts"
    scripts.mkdir()
    fake_runner = scripts / "run_pre_push_checks.py"
    fake_runner.write_text(
        "from pathlib import Path\n"
        "import os, sys\n"
        "payload = sys.stdin.read()\n"
        "if '--validate-push-refs-only' in sys.argv:\n"
        "    Path(os.environ['PREFLIGHT_STDIN']).write_text(payload)\n"
        "    Path(os.environ['PREFLIGHT_GIT_DIR']).write_text(os.getenv('GIT_DIR', '<unset>'))\n"
        "    if os.environ.get('REJECT_PREFLIGHT') == '1':\n"
        "        raise SystemExit(29)\n"
        "else:\n"
        "    Path(os.environ['RUNNER_STDIN']).write_text(payload)\n"
        "    Path(os.environ['RUNNER_GIT_DIR']).write_text(os.getenv('GIT_DIR', '<unset>'))\n"
        "    Path(os.environ['RUNNER_MARKER']).write_text('runner\\n')\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["RUNNER_MARKER"] = str(tmp_path / "runner-marker")
    env["RUNNER_STDIN"] = str(tmp_path / "runner-stdin")
    env["RUNNER_GIT_DIR"] = str(tmp_path / "runner-git-dir")
    env["PREFLIGHT_STDIN"] = str(tmp_path / "preflight-stdin")
    env["PREFLIGHT_GIT_DIR"] = str(tmp_path / "preflight-git-dir")
    env["NATIVE_MARKER"] = str(tmp_path / "native-marker")
    env["NATIVE_STDIN"] = str(tmp_path / "native-stdin")
    env["NATIVE_GIT_DIR"] = str(tmp_path / "native-git-dir")
    if native_exit is not None:
        _write_hook(
            repository / ".githooks/pre-push",
            'cat > "$NATIVE_STDIN"\n'
            'printf %s "${GIT_DIR-<unset>}" > "$NATIVE_GIT_DIR"\n'
            f'echo native > "$NATIVE_MARKER"\nexit {native_exit}\n',
        )
    return repository, env


def test_shared_pre_push_does_not_invoke_missing_native_hook(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=None)
    hook = repository.parent / ".githooks/pre-push"

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert Path(env["RUNNER_MARKER"]).is_file()
    assert not Path(env["NATIVE_MARKER"]).exists()


def test_owner_native_pre_push_failure_blocks_shared_full_gate(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=23)
    hook = repository.parent / ".githooks/pre-push"

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        check=False,
    )

    assert completed.returncode == 23
    assert Path(env["NATIVE_MARKER"]).is_file()
    assert not Path(env["RUNNER_MARKER"]).exists()


def test_owner_native_pre_push_success_continues_to_shared_full_gate(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=0)
    hook = repository.parent / ".githooks/pre-push"

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert Path(env["NATIVE_MARKER"]).is_file()
    assert Path(env["RUNNER_MARKER"]).is_file()


def test_shared_pre_push_replays_identical_stdin_to_native_and_runner(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=0)
    hook = repository.parent / ".githooks/pre-push"
    cache_dir = tmp_path / "cache with spaces"
    cache_dir.mkdir()
    env["TMPDIR"] = str(cache_dir)
    payload = (
        "refs/heads/main aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa "
        "refs/heads/main 0000000000000000000000000000000000000000\n"
        "refs/tags/v1 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb "
        "refs/tags/v1 0000000000000000000000000000000000000000\n"
    )

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        input=payload,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert Path(env["PREFLIGHT_STDIN"]).read_text(encoding="utf-8") == payload
    assert Path(env["NATIVE_STDIN"]).read_text(encoding="utf-8") == payload
    assert Path(env["RUNNER_STDIN"]).read_text(encoding="utf-8") == payload
    assert list(cache_dir.iterdir()) == []


def test_shared_pre_push_clears_git_local_env_only_for_shared_runner(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=0)
    hook = repository.parent / ".githooks/pre-push"
    git_dir = subprocess.run(
        ("git", "rev-parse", "--absolute-git-dir"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    env["GIT_DIR"] = git_dir

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert Path(env["PREFLIGHT_GIT_DIR"]).read_text(encoding="utf-8") == "<unset>"
    assert Path(env["RUNNER_GIT_DIR"]).read_text(encoding="utf-8") == "<unset>"
    assert Path(env["NATIVE_GIT_DIR"]).read_text(encoding="utf-8") == git_dir


def test_shared_pre_push_rejects_refs_before_owner_native_side_effects(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=0)
    hook = repository.parent / ".githooks/pre-push"
    env["REJECT_PREFLIGHT"] = "1"
    payload = "malicious ref update\n"

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        input=payload,
        text=True,
        check=False,
    )

    assert completed.returncode == 29
    assert Path(env["PREFLIGHT_STDIN"]).read_text(encoding="utf-8") == payload
    assert not Path(env["NATIVE_MARKER"]).exists()
    assert not Path(env["RUNNER_MARKER"]).exists()


def test_real_ref_preflight_rejects_other_branch_before_native_hook(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repository = workspace / "repo"
    _copy_shared_hooks(workspace)
    _init_repo(repository)
    head = _commit_file(repository)
    scripts = workspace / "scripts"
    scripts.mkdir()
    for name in (
        "install_pre_push_hooks.py",
        "run_pre_push_checks.py",
        "run_submodule_checks.py",
    ):
        shutil.copy2(ROOT / "scripts" / name, scripts / name)
    (scripts / "submodule_checks.json").write_text(
        json.dumps(
            {
                "submodules": {
                    "repo": {
                        "path": "repo",
                        "profiles": {"full": [[sys.executable, "-c", "pass"]]},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    native_marker = tmp_path / "native-marker"
    _write_hook(repository / ".githooks/pre-push", f"touch {native_marker!s}\n")
    zeros = "0" * len(head)
    payload = f"refs/heads/topic {head} refs/heads/topic {zeros}\n"

    completed = subprocess.run(
        (str(workspace / ".githooks/pre-push"), "origin", "example.invalid"),
        cwd=repository,
        input=payload,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert not native_marker.exists()


def test_shared_pre_push_invokes_executable_default_git_hook(tmp_path: Path) -> None:
    repository, env = _prepare_hook_execution(tmp_path, native_exit=None)
    hook = repository.parent / ".githooks/pre-push"
    git_dir = subprocess.run(
        ("git", "rev-parse", "--absolute-git-dir"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    default_marker = tmp_path / "default-native-marker"
    default_stdin = tmp_path / "default-native-stdin"
    env["DEFAULT_MARKER"] = str(default_marker)
    env["DEFAULT_STDIN"] = str(default_stdin)
    _write_hook(
        Path(git_dir) / "hooks/pre-push",
        'cat > "$DEFAULT_STDIN"\necho default > "$DEFAULT_MARKER"\n',
    )
    payload = "payload for default hook\n"

    completed = subprocess.run(
        (str(hook), "origin", "example.invalid"),
        cwd=repository,
        env=env,
        input=payload,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert default_marker.is_file()
    assert default_stdin.read_text(encoding="utf-8") == payload
    assert Path(env["RUNNER_STDIN"]).read_text(encoding="utf-8") == payload


def test_shared_pre_commit_delegates_to_owner_native_hook_without_recursion(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repository = workspace / "repo"
    _copy_shared_hooks(workspace)
    _init_repo(repository)
    marker = tmp_path / "native-pre-commit"
    native = repository / ".githooks/pre-commit"
    _write_hook(native, f"echo native > {marker!s}\n")

    completed = subprocess.run(
        (str(workspace / ".githooks/pre-commit"),),
        cwd=repository,
        check=False,
    )

    assert completed.returncode == 0
    assert marker.is_file()


def test_shared_pre_commit_invokes_executable_default_git_hook(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    repository = workspace / "repo"
    _copy_shared_hooks(workspace)
    _init_repo(repository)
    git_dir = subprocess.run(
        ("git", "rev-parse", "--absolute-git-dir"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    marker = tmp_path / "default-pre-commit"
    _write_hook(Path(git_dir) / "hooks/pre-commit", f"echo default > {marker!s}\n")

    completed = subprocess.run(
        (str(workspace / ".githooks/pre-commit"),),
        cwd=repository,
        check=False,
    )

    assert completed.returncode == 0
    assert marker.is_file()


def test_shared_hooks_have_no_custom_bypass() -> None:
    for name in ("pre-commit", "pre-push"):
        text = (ROOT / ".githooks" / name).read_text(encoding="utf-8")
        assert "SKIP" not in text
        assert "NO_VERIFY" not in text
