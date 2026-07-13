from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "framework-integration-ledger.yml"


def _load_ledger() -> dict[str, object]:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_framework_integration_ledger_has_owned_reversible_workstreams() -> None:
    payload = _load_ledger()

    assert payload["schema_version"] == "framework_integration_ledger.v1"
    assert payload["decision"] == "docs/adr/0001-framework-integration-boundaries.md"
    workstreams = payload["workstreams"]
    assert isinstance(workstreams, list)
    assert {item["id"] for item in workstreams} == {
        "artifact-envelope-v2",
        "qlib-data-adapter",
        "qlib-research-backend",
        "backtest-differential",
        "strategy-pipeline-thinning",
        "vnpy-execution-transport",
    }
    for item in workstreams:
        assert item["owner"]
        assert item["status"] in {"planned", "in_progress", "blocked", "complete"}
        assert item["entry_criteria"]
        assert item["exit_criteria"]
        assert item["rollback"]


def test_framework_policy_keeps_framework_types_out_of_contracts() -> None:
    policy = _load_ledger()["policy"]
    assert isinstance(policy, dict)

    assert policy["native_default_until_parity"] is True
    assert policy["optional_framework_dependencies"] == ["qlib", "vnpy"]
    assert policy["forbidden_contract_types"] == ["qlib.*", "vnpy.*", "QuantConnect.*"]
    assert policy["submodule_pin_after_downstream_merge"] is True
