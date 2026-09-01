from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

run_quality_checks = importlib.import_module("run_quality_checks")


def test_hard_quality_profile_runs_research_governance_checks() -> None:
    commands = {
        command.name: command.command
        for command in run_quality_checks.plan_commands("hard")
    }

    assert commands["research-capability-registry"] == (
        sys.executable,
        "-m",
        "src.research_contracts.research_capability_registry",
    )
    assert commands["trial-ledger"] == (
        sys.executable,
        str(
            ROOT
            / "strategy-research"
            / "tools"
            / "scripts"
            / "trial_ledger_check.py"
        ),
    )
