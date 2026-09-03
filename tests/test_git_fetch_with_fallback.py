from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "git-fetch-with-fallback.sh"


def _fake_bin(tmp_path: Path, git_body: str, gh_body: str = "") -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git = bin_dir / "git"
    git.write_text("#!/usr/bin/env bash\nset -u\n" + git_body)
    git.chmod(0o755)
    gh = bin_dir / "gh"
    gh.write_text("#!/usr/bin/env bash\nset -u\n" + gh_body)
    gh.chmod(0o755)
    return bin_dir, git


def test_fetch_falls_back_to_ssh_after_configured_remote_fails(tmp_path: Path) -> None:
    log = tmp_path / "git.log"
    git_body = f"""\
printf '%s\\n' "$*" >> {log}
if [[ "$1" == "-C" && "$3" == "remote" ]]; then
  printf '%s\\n' 'https://github.com/acme/widgets.git'
  exit 0
fi
    if [[ "$*" == *" fetch origin +main:"* ]]; then
  exit 1
fi
if [[ "$*" == *"git@github.com:acme/widgets.git"* ]]; then
  exit 0
fi
exit 0
"""
    bin_dir, _ = _fake_bin(tmp_path, git_body, "exit 1\n")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(tmp_path / "repo"), "origin", "main"],
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[fetch] ssh" in result.stdout
    assert "git@github.com:acme/widgets.git" in log.read_text()


def test_fetch_reports_all_attempts_when_every_route_fails(tmp_path: Path) -> None:
    log = tmp_path / "git.log"
    git_body = f"""\
printf '%s\\n' "$*" >> {log}
if [[ "$1" == "-C" && "$3" == "remote" ]]; then
  printf '%s\\n' 'git@github.com:acme/widgets.git'
  exit 0
fi
exit 1
"""
    bin_dir, _ = _fake_bin(tmp_path, git_body, "exit 1\n")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(tmp_path / "repo"), "origin", "main"],
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "all fetch methods failed" in result.stderr
    assert "configured remote" in result.stderr
    assert "github cli" in result.stderr
    assert "ssh" in result.stderr
    assert "https" in result.stderr


def test_fetch_falls_back_to_plain_https_after_ssh_fails(tmp_path: Path) -> None:
    git_body = """\
if [[ "$1" == "-C" && "$3" == "remote" ]]; then
  printf '%s\\n' 'git@github.com:acme/widgets.git'
  exit 0
fi
if [[ "$*" == *"https://github.com/acme/widgets.git"* ]]; then
  if [[ -n "${GIT_FETCH_AUTHORIZATION:-}" ]]; then exit 1; fi
  if [[ "$*" == *"git@github.com:acme/widgets.git"* ]]; then exit 1; fi
  exit 0
fi
exit 1
"""
    bin_dir, _ = _fake_bin(tmp_path, git_body, "printf '%s\\n' token\n")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(tmp_path / "repo"), "origin", "main"],
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[fetch] https" in result.stdout


def test_github_cli_auth_is_passed_via_environment_not_argv(tmp_path: Path) -> None:
    argv_log = tmp_path / "argv.log"
    auth_log = tmp_path / "auth.log"
    git_body = f"""\
if [[ "$1" == "-C" && "$3" == "remote" ]]; then
  printf '%s\\n' 'https://github.com/acme/widgets.git'
  exit 0
fi
printf '%s\\n' "$*" >> {argv_log}
printf '%s\\n' "${{GIT_FETCH_AUTHORIZATION:-}}" >> {auth_log}
if [[ "$*" == *"https://github.com/acme/widgets.git"* ]]; then exit 0; fi
exit 1
"""
    bin_dir, _ = _fake_bin(tmp_path, git_body, "printf '%s\\n' secret-token\n")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(tmp_path / "repo"), "origin", "main"],
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[fetch] github cli (authenticated HTTPS)" in result.stdout
    assert "secret-token" not in argv_log.read_text()
    assert "secret-token" in auth_log.read_text()
    assert "+main:refs/remotes/origin/main" in argv_log.read_text()
