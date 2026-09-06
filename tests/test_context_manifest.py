from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "context_manifest.py"
EXPECTED_AREAS = {
    "alpha",
    "data",
    "execution",
    "market-intel",
    "microstructure",
    "orchestration",
    "portfolio",
    "strategy",
}


def load_context_manifest():
    assert SCRIPT.is_file(), "context manifest CLI must exist"
    spec = importlib.util.spec_from_file_location("context_manifest", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_alpha_manifest_includes_direct_contracts() -> None:
    context_manifest = load_context_manifest()

    result = context_manifest.build_manifest("alpha")

    assert "alpha-research" in result.repositories
    assert "portfolio-backtester" in result.direct_consumers
    assert "market-intel" not in result.default_context


def test_manifest_registry_is_explicit_and_rejects_unknown_areas() -> None:
    context_manifest = load_context_manifest()

    assert set(context_manifest.available_areas()) == EXPECTED_AREAS
    with pytest.raises(ValueError, match="unknown task area"):
        context_manifest.build_manifest("all")


def test_rendered_alpha_manifest_names_contract_route_and_test() -> None:
    context_manifest = load_context_manifest()

    rendered = context_manifest.render_manifest(context_manifest.build_manifest("alpha"))

    assert "Producer: `alpha-research`" in rendered
    assert "Contract: `signals.parquet`" in rendered
    assert "Consumer: `portfolio-backtester`" in rendered
    assert "Test: `pytest alpha-research/tests/test_signal_artifact.py -q`" in rendered


def test_cli_renders_one_requested_area() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--task", "strategy"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.startswith("# Task context: strategy\n")
    assert "`strategy-research`" in completed.stdout
    assert "# Task context: alpha" not in completed.stdout


def test_manifest_pytest_targets_exist() -> None:
    context_manifest = load_context_manifest()

    missing: list[str] = []
    for area in context_manifest.available_areas():
        for route in context_manifest.build_manifest(area).contracts:
            command = route.test_command.split()
            if command[0] == "pytest" and not (ROOT / command[1]).is_file():
                missing.append(command[1])

    assert missing == []
