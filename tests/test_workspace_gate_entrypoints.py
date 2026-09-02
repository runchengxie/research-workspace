from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

run_pre_push_checks = importlib.import_module("run_pre_push_checks")
run_submodule_checks = importlib.import_module("run_submodule_checks")


def test_pre_push_root_tests_use_workspace_runner() -> None:
    configs = run_submodule_checks.load_manifest(ROOT / "scripts/submodule_checks.json")

    plan = run_pre_push_checks.plan_gate(ROOT, ROOT, configs)
    root_tests = next(command for command in plan.commands if command.name == "root-tests")

    assert root_tests.cwd == ROOT
    assert root_tests.command == (sys.executable, "scripts/run_workspace_tests.py")
