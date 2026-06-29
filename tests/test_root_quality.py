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
        "src/research_contracts/**/*.py",
        "src/style_factors/**/*.py",
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

    assert "ty-check" in names
    assert "workspace-import-boundaries" in names


def test_ci_smoke_profile_skips_workspace_import_boundary_gate() -> None:
    commands = run_quality_checks.plan_commands("ci-smoke")

    names = [item.name for item in commands]

    assert names == ["ruff-check", "ruff-format", "ty-check", "secret-scan"]
    assert "workspace-import-boundaries" not in names


def test_basedpyright_profile_is_advisory() -> None:
    commands = run_quality_checks.plan_commands("basedpyright")

    assert [item.name for item in commands] == ["basedpyright-advisory"]


def test_dead_code_profile_runs_advisory_wrapper() -> None:
    commands = run_quality_checks.plan_commands("dead-code")

    assert [item.name for item in commands] == ["dead-code-advisory"]
    assert commands[0].command[-1].endswith("scripts/dead_code_advisory.py")


def test_superproject_ci_runs_top_level_quality_gates() -> None:
    workflow = (ROOT / ".github" / "workflows" / "superproject.yml").read_text(encoding="utf-8")

    assert "submodules: false" in workflow
    assert "WORKSPACE_SUBMODULE_READ_TOKEN" in workflow
    assert "Checkout private submodules" in workflow
    assert "python scripts/run_quality_checks.py --profile hard" in workflow
    assert "Run superproject smoke quality profile without private submodules" in workflow
    assert "python scripts/run_quality_checks.py --profile ci-smoke" in workflow
    assert "python scripts/run_quality_checks.py --profile basedpyright" in workflow
    assert "continue-on-error: true" in workflow
    assert "uv run --with pytest python -m pytest tests -q" in workflow
    assert "Run superproject smoke tests without private submodules" in workflow
    assert "python scripts/run_submodule_checks.py --profile full --dry-run" in workflow
    assert "python src/research_contracts/smoke_contracts.py --timeout 10" in workflow
