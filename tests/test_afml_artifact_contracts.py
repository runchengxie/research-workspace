from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "artifact-contracts.yml"


def test_afml_artifact_contracts_have_owner_native_entrypoints() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {record["artifact"]: record for record in payload["artifacts"]}
    expected = {
        "label_events.parquet": "alpha-research",
        "sample_weights.parquet": "alpha-research",
        "sample_weights.receipt.json": "alpha-research",
        "research_features.parquet": "market-data-platform",
        "sizing_receipt.json": "portfolio-backtester",
        "strategy_risk_report.json": "portfolio-backtester",
        "hrp_receipt.json": "portfolio-backtester",
        "research_protocol_report.json": "strategy-pipeline",
        "execution_policy_receipt.json": "quant-execution-engine",
        "handoff_audit_report.json": "quant-execution-engine",
    }

    assert set(records) >= set(expected)
    for artifact, owner in expected.items():
        record = records[artifact]
        assert record["owner"] == owner
        assert record["entrypoints"]
        for entrypoint in record["entrypoints"]:
            assert (ROOT / entrypoint["repo"] / entrypoint["path"]).is_file()


def test_research_protocol_is_evidence_not_order_input() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {record["artifact"]: record for record in payload["artifacts"]}
    protocol = records["research_protocol_report.json"]
    execution = records["execution_policy_receipt.json"]

    assert "never changes target semantics" in protocol["notes"]
    assert protocol["consumers"] == ["quant-execution-engine"]
    assert execution["owner"] == "quant-execution-engine"
