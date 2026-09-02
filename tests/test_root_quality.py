from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_quality_checks.py"
EXPECTED_SUBMODULES = {
    "alpha-research",
    "market-data-platform",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
    "strategy-app",
    "deep-learning-tick-data-prediction",
    "strategy-research",
}

spec = importlib.util.spec_from_file_location("run_quality_checks", SCRIPT)
run_quality_checks = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = run_quality_checks
spec.loader.exec_module(run_quality_checks)


def test_root_ruff_scope_excludes_submodule_source_trees() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ruff = config["tool"]["ruff"]

    assert ruff["target-version"] == "py312"
    assert ruff["include"] == [
        "src/research_contracts/**/*.py",
        "scripts/**/*.py",
        "tests/**/*.py",
    ]
    assert EXPECTED_SUBMODULES <= set(ruff["extend-exclude"])


def test_root_typecheck_explicitly_excludes_all_submodules() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ty = config["tool"]["ty"]["src"]

    assert EXPECTED_SUBMODULES <= set(ty["exclude"])


def test_architecture_scanner_is_in_root_typecheck_scope() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ty_include = config["tool"]["ty"]["src"]["include"]

    assert "scripts/workspace_architecture*.py" in ty_include


def test_root_lint_profile_names_only_superproject_owned_paths() -> None:
    commands = run_quality_checks.plan_commands("lint")

    assert commands
    for item in commands:
        assert item.command[-1] == "."
        for submodule in EXPECTED_SUBMODULES:
            assert submodule not in item.command


def test_type_check_runs_with_workspace_dependencies() -> None:
    command = run_quality_checks._ty_command("check")

    assert command[:3] == ("uv", "run", "--project")
    assert command[3] == str(ROOT)
    assert command[4:7] == ("--with", "ty", "ty")
    assert command[-1] == "check"


def test_dependency_profile_runs_pip_audit_in_root_project() -> None:
    commands = run_quality_checks.plan_commands("dependencies")

    assert [item.name for item in commands] == ["pip-audit"]
    command = commands[0].command
    assert command[:4] == ("uv", "run", "--project", str(ROOT))
    assert command[4:6] == ("--group", "dev")
    assert command[6] == "pip-audit"
    assert "--progress-spinner" in command
    assert "off" in command


def test_hard_profile_includes_workspace_architecture_gates() -> None:
    commands = run_quality_checks.plan_commands("hard")

    names = [item.name for item in commands]

    assert "ty-check" in names
    assert "workspace-import-boundaries" in names
    assert "workspace-ownership-boundaries" in names
    assert "workspace-architecture" in names


def test_architecture_profile_includes_combined_projection_gate() -> None:
    commands = run_quality_checks.plan_commands("architecture")

    names = [item.name for item in commands]
    architecture = next(item for item in commands if item.name == "workspace-architecture")

    assert names == [
        "workspace-import-boundaries",
        "workspace-ownership-boundaries",
        "workspace-architecture",
    ]
    assert architecture.command[-2:] == (
        str(ROOT / "scripts" / "workspace_architecture.py"),
        "--check",
    )


def test_ci_smoke_profile_skips_private_workspace_gates_but_audits_dependencies() -> None:
    commands = run_quality_checks.plan_commands("ci-smoke")

    names = [item.name for item in commands]

    assert names == ["ruff-check", "ruff-format", "ty-check", "pip-audit", "secret-scan"]
    assert "workspace-import-boundaries" not in names
    assert "workspace-ownership-boundaries" not in names
    assert "workspace-architecture" not in names


def test_dead_code_profile_runs_advisory_wrapper() -> None:
    commands = run_quality_checks.plan_commands("dead-code")

    assert [item.name for item in commands] == ["dead-code-advisory"]
    assert commands[0].command[-1].endswith("scripts/dead_code_advisory.py")


def test_public_workflow_runs_root_regression_checks_without_private_submodules() -> None:
    active = ROOT / ".github" / "workflows" / "contracts.yml"
    obsolete = ROOT / ".github" / "workflows" / "superproject.yml.disabled"
    assert active.is_file()
    assert not obsolete.exists()
    workflow = active.read_text(encoding="utf-8")

    assert "submodules: false" in workflow
    assert "WORKSPACE_SUBMODULE_READ_TOKEN" not in workflow
    assert "tests/test_platform_publication.py" in workflow
    assert "tests/test_platform_asset_registry.py" in workflow
    assert "tests/test_run_submodule_fail_fast.py" in workflow
    assert "tests/test_check_script.py" in workflow
    assert "tests/test_root_quality.py" in workflow
