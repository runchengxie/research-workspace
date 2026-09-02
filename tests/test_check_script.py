from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check.sh"

FAKE_COMMAND = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path

log_path = Path(os.environ["CHECK_SH_TEST_LOG"])
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(Path(sys.argv[0]).name + " " + " ".join(sys.argv[1:]) + "\\n")
match = os.environ.get("CHECK_SH_FAIL_MATCH", "")
if match and match in " ".join(sys.argv[1:]):
    raise SystemExit(7)
"""


def _fake_environment(tmp: str, *, fail_match: str = "") -> tuple[dict[str, str], Path]:
    root = Path(tmp)
    bin_dir = root / "bin"
    bin_dir.mkdir()
    log = root / "commands.log"
    for name in ("python", "uv"):
        path = bin_dir / name
        path.write_text(FAKE_COMMAND, encoding="utf-8")
        path.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CHECK_SH_TEST_LOG"] = str(log)
    env["CHECK_SH_FAIL_MATCH"] = fail_match
    return env, log


def test_standard_returns_nonzero_when_an_early_gate_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env, _log = _fake_environment(tmp, fail_match="scripts/run_quality_checks.py")
        completed = subprocess.run(
            ["bash", str(SCRIPT), "standard"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    assert completed.returncode != 0


def test_standard_delegates_root_tests_to_workspace_runner() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env, log = _fake_environment(tmp)
        completed = subprocess.run(
            ["bash", str(SCRIPT), "standard"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        commands = log.read_text(encoding="utf-8")

    assert completed.returncode == 0
    assert "python scripts/run_workspace_tests.py\n" in commands
    assert "uv run --project strategy-pipeline" not in commands


def test_full_executes_submodule_full_profile_instead_of_dry_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env, log = _fake_environment(tmp)
        completed = subprocess.run(
            ["bash", str(SCRIPT), "full"],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        commands = log.read_text(encoding="utf-8")

    assert completed.returncode == 0
    assert "scripts/run_submodule_checks.py --profile full\n" in commands
    assert "scripts/run_submodule_checks.py --profile full --dry-run" not in commands
