from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
INVENTORY = ROOT / "docs" / "boundary-refactor-inventory-20260831.json"
REQUIRED_FIELDS = {"repo", "path", "owner", "classification", "target", "status"}
REPOS = {
    "strategy-pipeline",
    "deep-learning-tick-data-prediction",
    "strategy-research",
    "market-intel",
}
CLASSIFICATIONS = {
    "runtime-owner",
    "research-reusable",
    "experiment-entry",
    "consumer-bridge",
    "deprecated-duplicate",
}


def test_boundary_inventory_has_stable_schema_and_scope() -> None:
    document = json.loads(INVENTORY.read_text(encoding="utf-8"))

    assert document["schema_version"] == "boundary_refactor_inventory.v1"
    assert set(document["scope"]) == REPOS
    assert set(document["classifications"]) == CLASSIFICATIONS
    assert document["entries"]
    assert all(REQUIRED_FIELDS <= set(entry) for entry in document["entries"])
    assert {entry["repo"] for entry in document["entries"]} == REPOS
    assert {entry["classification"] for entry in document["entries"]} <= CLASSIFICATIONS


def test_boundary_inventory_covers_the_known_leakage_families() -> None:
    entries = json.loads(INVENTORY.read_text(encoding="utf-8"))["entries"]
    paths = {entry["path"] for entry in entries}

    assert "src/strategy_pipeline/daily_watch20_ablation.py" in paths
    assert "src/strategy_pipeline/liquidity_proxy.py" in paths
    assert "src/ticknet/eventstream/canonical_adapter.py" in paths
    assert "src/ticknet/nextday/raw_snapshot.py" in paths
    assert "experiments" in paths
    assert "src/tushare_jobs" in paths
