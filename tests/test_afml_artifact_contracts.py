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
        "afml_evidence_fragment.json": "strategy-pipeline",
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
            entrypoint_path = ROOT / entrypoint["repo"] / entrypoint["path"]
            if entrypoint["repo"] == "strategy-pipeline-internal":
                assert entrypoint["path"].startswith("src/strategy_pipeline_internal/")
            else:
                assert entrypoint_path.is_file()


def test_generated_evidence_keeps_algorithm_and_producer_ownership_separate() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {record["artifact"]: record for record in payload["artifacts"]}

    for artifact in ("sizing_receipt.json", "strategy_risk_report.json", "hrp_receipt.json"):
        record = records[artifact]
        assert record["owner"] == "portfolio-backtester"
        assert record["producer"] == "strategy-pipeline"
        roles = {entrypoint["role"] for entrypoint in record["entrypoints"]}
        assert roles == {"canonical_implementation", "artifact_producer"}


def test_migrated_artifact_contracts_do_not_retain_internal_entrypoints() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {record["artifact"]: record for record in payload["artifacts"]}

    for artifact in (
        "signals.parquet",
        "watchlist_20.csv",
        "selection_receipt.json",
        "sizing_receipt.json",
        "strategy_risk_report.json",
        "hrp_receipt.json",
        "afml_evidence_fragment.json",
        "research_protocol_report.json",
    ):
        assert all(
            entrypoint["repo"] != "strategy-pipeline-internal"
            for entrypoint in records[artifact]["entrypoints"]
        )


def test_research_protocol_is_evidence_not_order_input() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = {record["artifact"]: record for record in payload["artifacts"]}
    protocol = records["research_protocol_report.json"]
    execution = records["execution_policy_receipt.json"]

    assert "never changes target semantics" in protocol["notes"]
    assert protocol["consumers"] == ["quant-execution-engine"]
    assert execution["owner"] == "quant-execution-engine"
