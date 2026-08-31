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


def test_root_gate_runs_capability_registry_and_trial_ledger_checks() -> None:
    configs = run_submodule_checks.load_manifest(ROOT / "scripts/submodule_checks.json")

    plan = run_pre_push_checks.plan_gate(ROOT, ROOT, configs)
    commands = {command.name: command for command in plan.commands}

    assert "research-capability-registry" in commands
    assert commands["research-capability-registry"].cwd == ROOT
    assert commands["research-capability-registry"].command == (
        sys.executable,
        "scripts/research_capability_registry_check.py",
    )

    assert "trial-ledger" in commands
    assert commands["trial-ledger"].cwd == ROOT / "strategy-research"
    assert commands["trial-ledger"].command == (
        sys.executable,
        "scripts/trial_ledger_check.py",
    )
