from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_quality_checks.py"

spec = importlib.util.spec_from_file_location("run_quality_checks", SCRIPT)
run_quality_checks = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = run_quality_checks
spec.loader.exec_module(run_quality_checks)


def test_root_ruff_scope_excludes_submodule_source_trees() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ruff = config["tool"]["ruff"]

    assert ruff["include"] == [
        "research-contracts/src/**/*.py",
        "style_factors/**/*.py",
        "scripts/**/*.py",
        "tests/**/*.py",
    ]
    assert {
        "alpha-research",
        "market-data-platform",
        "portfolio-backtester",
        "strategy-pipeline",
        "quant-execution-engine",
    } <= set(ruff["extend-exclude"])


def test_root_lint_profile_names_only_superproject_owned_paths() -> None:
    commands = run_quality_checks.plan_commands("lint")

    assert commands
    for item in commands:
        assert item.command[-1] == "."
        assert "alpha-research" not in item.command
        assert "market-data-platform" not in item.command
        assert "portfolio-backtester" not in item.command
        assert "strategy-pipeline" not in item.command
        assert "quant-execution-engine" not in item.command


def test_hard_profile_includes_workspace_import_boundary_gate() -> None:
    commands = run_quality_checks.plan_commands("hard")

    names = [item.name for item in commands]

    assert "workspace-import-boundaries" in names
