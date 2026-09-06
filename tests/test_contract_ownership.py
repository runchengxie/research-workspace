from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "contracts" / "contract-ownership.yml"
ARTIFACT_MANIFEST = ROOT / "docs" / "artifact-contracts.yml"


def _load_contracts_package():
    contracts_src = ROOT / "src"
    if str(contracts_src) not in sys.path:
        sys.path.insert(0, str(contracts_src))
    import research_contracts

    return research_contracts


def _valid_record() -> dict[str, object]:
    return {
        "name": "example.json",
        "schema": "example.v1",
        "producer": "example-producer",
        "consumers": ["example-consumer"],
        "versioning": "immutable",
        "compatibility": "exact schema",
        "test_command": "pytest tests/test_example.py -q",
        "rollback": "restore the previous artifact",
    }


def _write_registry(path: Path, record: object) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "contract_ownership.v1",
                "contracts": [record],
            }
        ),
        encoding="utf-8",
    )


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


def test_contract_ownership_rejects_non_object_entries_before_loading(tmp_path: Path) -> None:
    contracts_package = _load_contracts_package()
    registry = tmp_path / "contract-ownership.yml"
    _write_registry(registry, "not-an-object")

    result = contracts_package.validate_contract_ownership(registry_path=registry)

    assert result.issues == ("contracts[0]: must be an object",)
    with pytest.raises(ValueError, match=r"contracts\[0\]: must be an object"):
        contracts_package.load_contract_ownership(registry)


@pytest.mark.parametrize(
    ("field", "malformed", "expected"),
    [
        ("name", 7, "contracts[0].name: must be a string"),
        ("schema", None, "contracts[0].schema: must be a string"),
        ("producer", False, "contracts[0].producer: must be a string"),
        ("versioning", ["v1"], "contracts[0].versioning: must be a string"),
        ("compatibility", {}, "contracts[0].compatibility: must be a string"),
        ("test_command", 1.5, "contracts[0].test_command: must be a string"),
        ("rollback", True, "contracts[0].rollback: must be a string"),
    ],
)
def test_contract_ownership_rejects_non_string_scalar_fields(
    tmp_path: Path,
    field: str,
    malformed: object,
    expected: str,
) -> None:
    contracts_package = _load_contracts_package()
    registry = tmp_path / "contract-ownership.yml"
    record = _valid_record()
    record[field] = malformed
    _write_registry(registry, record)

    result = contracts_package.validate_contract_ownership(registry_path=registry)

    assert result.issues == (expected,)
    with pytest.raises(ValueError, match="must be a string"):
        contracts_package.load_contract_ownership(registry)


def test_contract_ownership_rejects_non_list_consumers_before_loading(tmp_path: Path) -> None:
    contracts_package = _load_contracts_package()
    registry = tmp_path / "contract-ownership.yml"
    record = _valid_record()
    record["consumers"] = "example-consumer"
    _write_registry(registry, record)

    result = contracts_package.validate_contract_ownership(registry_path=registry)

    assert result.issues == ("contracts[0].consumers: must be a list",)
    with pytest.raises(ValueError, match="consumers: must be a list"):
        contracts_package.load_contract_ownership(registry)


def test_contract_ownership_rejects_non_string_consumer_values(tmp_path: Path) -> None:
    contracts_package = _load_contracts_package()
    registry = tmp_path / "contract-ownership.yml"
    record = _valid_record()
    record["consumers"] = ["example-consumer", 42]
    _write_registry(registry, record)

    result = contracts_package.validate_contract_ownership(registry_path=registry)

    assert result.issues == ("contracts[0].consumers[1]: must be a string",)
    with pytest.raises(ValueError, match=r"consumers\[1\]: must be a string"):
        contracts_package.load_contract_ownership(registry)
