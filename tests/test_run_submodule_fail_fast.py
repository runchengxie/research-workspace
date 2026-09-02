from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_submodule_checks.py"

spec = importlib.util.spec_from_file_location("run_submodule_checks_fail_fast", SCRIPT)
run_submodule_checks = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = run_submodule_checks
spec.loader.exec_module(run_submodule_checks)


def _planned(cwd: Path, *commands: tuple[str, ...]):
    return [
        run_submodule_checks.PlannedCommand(
            submodule="example",
            cwd=cwd,
            command=command,
        )
        for command in commands
    ]


def test_fail_fast_continues_after_success_until_first_error() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        planned = _planned(
            cwd,
            (sys.executable, "-c", "raise SystemExit(0)"),
            (sys.executable, "-c", "raise SystemExit(7)"),
            (sys.executable, "-c", "raise SystemExit(0)"),
        )
        results = run_submodule_checks.run_planned_commands(
            planned,
            timeout=5,
            dry_run=False,
            fail_fast=True,
        )

    assert [result.severity for result in results] == ["OK", "ERROR"]


def test_fail_fast_stops_immediately_when_first_command_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        marker = cwd / "should-not-run"
        planned = _planned(
            cwd,
            (sys.executable, "-c", "raise SystemExit(7)"),
            (
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            ),
        )
        results = run_submodule_checks.run_planned_commands(
            planned,
            timeout=5,
            dry_run=False,
            fail_fast=True,
        )

    assert [result.severity for result in results] == ["ERROR"]
    assert not marker.exists()
