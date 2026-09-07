from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
ALLOWED_STATUSES = {
    "TRANSFER_REQUIRED",
    "REVIEW_REQUIRED",
    "PUBLICLY_EXCLUDED_PRIVATE_TARGET_REQUIRED",
    "DOCUMENTATION_RELOCATE",
    "HISTORICAL_ARCHIVE",
    "RETAIN_IN_WORKSPACE",
}


def test_convergence_inventory_covers_every_component_with_evidence_and_rollback():
    inventory = json.loads(
        (ROOT / "migration/2026-09-07-convergence-inventory.json").read_text()
    )
    component_map = json.loads(
        (ROOT / "migration/supersession-component-map.json").read_text()
    )

    components = inventory["components"]
    assert {entry["legacy"] for entry in components} == {
        entry["legacy"] for entry in component_map["components"]
    }
    assert all(entry["status"] in ALLOWED_STATUSES for entry in components)
    assert all(entry["source"]["head"] for entry in components)
    assert all(entry["parity_evidence"] for entry in components)
    assert all(entry["rollback"]["required"] for entry in components)


def test_convergence_inventory_resolves_market_data_owner_conflict():
    inventory = json.loads(
        (ROOT / "migration/2026-09-07-convergence-inventory.json").read_text()
    )
    market_data = next(
        entry for entry in inventory["components"] if entry["legacy"] == "market-data-platform"
    )

    assert market_data["ownership_decision"] in {
        "independent_quant_market_data_platform",
        "split_public_private",
    }
    assert market_data["decision_evidence"]
