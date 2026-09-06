from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "contracts" / "contract-ownership.yml"
ARTIFACT_MANIFEST = ROOT / "docs" / "artifact-contracts.yml"


def _load_contracts_package():
    contracts_src = ROOT / "src"
    if str(contracts_src) not in sys.path:
        sys.path.insert(0, str(contracts_src))
    import research_contracts

    return research_contracts


def test_contract_ownership_covers_required_cross_repository_handoffs() -> None:
    contracts_package = _load_contracts_package()
    contracts = contracts_package.load_contract_ownership(REGISTRY)

    assert {item.name for item in contracts} >= {
        "targets.json",
        "research context snapshot",
        "metadata/current_assets/a_share_current.json",
        "formal_predictions.parquet",
        "signals.parquet",
        "backtest pricing frame",
        "watchlist_20.csv",
        "selection_receipt.json",
    }


def test_every_contract_has_one_producer_and_consumer() -> None:
    contracts_package = _load_contracts_package()
    contracts = contracts_package.load_contract_ownership(REGISTRY)

    assert all(item.producer for item in contracts)
    assert all(item.consumers for item in contracts)


def test_contract_ownership_records_only_governance_metadata() -> None:
    registry_text = REGISTRY.read_text(encoding="utf-8")
    payload = json.loads(registry_text)

    assert payload["schema_version"] == "contract_ownership.v1"
    assert payload["contracts"]
    required_fields = {
        "name",
        "schema",
        "producer",
        "consumers",
        "versioning",
        "compatibility",
        "test_command",
        "rollback",
    }
    assert all(set(record) == required_fields for record in payload["contracts"])
    assert "/home/" not in registry_text


def test_contract_ownership_matches_authoritative_artifact_manifest() -> None:
    contracts_package = _load_contracts_package()
    result = contracts_package.validate_contract_ownership(
        registry_path=REGISTRY,
        artifact_manifest_path=ARTIFACT_MANIFEST,
    )

    assert result.ok, result.issues


def test_contract_ownership_rejects_missing_producer_and_consumers(tmp_path: Path) -> None:
    contracts_package = _load_contracts_package()
    registry = tmp_path / "contract-ownership.yml"
    registry.write_text(
        json.dumps(
            {
                "schema_version": "contract_ownership.v1",
                "contracts": [
                    {
                        "name": "orphan.json",
                        "schema": "orphan.v1",
                        "producer": "",
                        "consumers": [],
                        "versioning": "immutable",
                        "compatibility": "exact schema",
                        "test_command": "pytest tests/test_orphan.py -q",
                        "rollback": "restore the previous immutable artifact",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = contracts_package.validate_contract_ownership(registry_path=registry)

    assert "orphan.json: producer is required" in result.issues
    assert "orphan.json: consumers must be non-empty" in result.issues
