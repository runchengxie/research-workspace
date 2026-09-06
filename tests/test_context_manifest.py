from __future__ import annotations

import importlib.util
import json
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


def test_default_context_paths_exist_or_use_an_external_marker() -> None:
    context_manifest = load_context_manifest()

    missing: list[str] = []
    external: list[str] = []
    for area in context_manifest.available_areas():
        for context in context_manifest.build_manifest(area).default_context:
            if context.startswith("external checkout: "):
                external.append(context)
            elif not (ROOT / context).is_file():
                missing.append(context)

    assert missing == []
    assert external == ["external checkout: market-intel/AGENTS.md"]


def test_direct_consumers_have_an_owned_contract_route() -> None:
    context_manifest = load_context_manifest()

    unsupported: dict[str, list[str]] = {}
    for area in context_manifest.available_areas():
        manifest = context_manifest.build_manifest(area)
        routed_consumers = {
            consumer
            for route in manifest.contracts
            if route.producer in manifest.repositories
            for consumer in route.consumers
        }
        missing = sorted(set(manifest.direct_consumers) - routed_consumers)
        if missing:
            unsupported[area] = missing

    assert unsupported == {}


def test_data_alpha_and_portfolio_consumers_match_artifact_routes() -> None:
    context_manifest = load_context_manifest()

    data = context_manifest.build_manifest("data")
    research_features = next(
        route for route in data.contracts if route.contract == "research_features.parquet"
    )

    assert research_features.producer == "market-data-platform"
    assert set(research_features.consumers) == {"alpha-research", "strategy-pipeline"}
    assert set(context_manifest.build_manifest("alpha").direct_consumers) == {
        "portfolio-backtester",
        "strategy-pipeline",
    }
    assert context_manifest.build_manifest("portfolio").direct_consumers == ("strategy-pipeline",)


def test_watchlist_route_matches_authoritative_registry() -> None:
    context_manifest = load_context_manifest()
    registry = json.loads((ROOT / "docs" / "artifact-contracts.yml").read_text())
    authoritative = next(
        item for item in registry["artifacts"] if item["artifact"] == "watchlist_20.csv"
    )
    watchlist_routes = [
        (area, route)
        for area in context_manifest.available_areas()
        for route in context_manifest.build_manifest(area).contracts
        if route.contract == "watchlist_20.csv"
    ]

    assert len(watchlist_routes) == 2
    assert {area for area, _route in watchlist_routes} == {"market-intel", "orchestration"}
    for _area, route in watchlist_routes:
        assert route.producer == authoritative["producer"]
        assert list(route.consumers) == authoritative["consumers"]
    orchestration = context_manifest.build_manifest("orchestration")
    assert "market-intel" in orchestration.direct_consumers
