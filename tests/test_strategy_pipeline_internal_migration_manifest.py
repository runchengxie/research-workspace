from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "migrations" / "strategy-pipeline-internal-migration-manifest.md"
VALID_STATUSES = {"complete", "private", "planned", "archive"}
REQUIRED_RECORD_FIELDS = {"source_path", "owner_repo", "target_path", "status"}


def _load_manifest() -> dict[str, object]:
    text = MANIFEST.read_text(encoding="utf-8")
    start = text.index("```json") + len("```json")
    end = text.index("```", start)
    return json.loads(text[start:end])


def test_manifest_has_verified_inventory_baseline() -> None:
    payload = _load_manifest()
    assert payload["schema_version"] == "strategy_pipeline_internal_migration.v1"
    assert payload["source_repository"] == "runchengxie/strategy-pipeline-internal"
    inventory = payload["inventory"]
    assert inventory == {
        "python_source_files": 181,
        "test_files": 183,
        "script_files": 34,
        "config_files": 18,
        "ownership_document_files": 114,
        "ownership_document_status_counts": {
            "complete": 8,
            "private": 58,
            "planned": 16,
            "archive": 32,
        },
    }


def test_module_groups_have_unique_active_ownership_and_evidence() -> None:
    payload = _load_manifest()
    groups = payload["module_groups"]
    assert isinstance(groups, list)
    assert sum(group["file_count"] for group in groups) == 181
    assert len({group["source_path"] for group in groups}) == len(groups)

    for group in groups:
        assert REQUIRED_RECORD_FIELDS <= group.keys()
        assert group["status"] in VALID_STATUSES
        assert group["owner_repo"] != "strategy-pipeline-internal"
        assert group["test_evidence"]
        assert group["doc_evidence"]
        assert group["removal_condition"]


def test_planned_document_inventory_has_target_and_no_duplicate_source() -> None:
    payload = _load_manifest()
    documents = payload["planned_documents"]
    assert isinstance(documents, list)
    assert len(documents) == 16
    assert len({document["source_path"] for document in documents}) == 16

    for document in documents:
        assert REQUIRED_RECORD_FIELDS <= document.keys()
        assert document["status"] in VALID_STATUSES
        assert document["owner_repo"] != "strategy-pipeline-internal"
        if document["status"] == "complete":
            assert document["test_evidence"]


def test_completed_code_migrations_record_owner_and_consumer_switch() -> None:
    payload = _load_manifest()
    migrations = payload["completed_code_migrations"]
    assert migrations == [
        {
            "source_path": "src/strategy_pipeline_internal/liquidity_proxy.py",
            "owner_repo": "portfolio-backtester",
            "target_path": "src/portfolio_backtester/liquidity_proxy.py",
            "status": "complete",
            "owner_commit": "6eefb9668d10c11f0098b44bf578b462db218299",
            "internal_commit": "cd25c8985f3e52486f11d7244aaa06fcc06dd8e5",
            "test_evidence": "portfolio-backtester tests/test_liquidity_proxy.py; internal tests/test_retired_liquidity_proxy.py; internal tests/test_pipeline_memory_path.py",
            "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
            "consumer_switch": "internal panel loading now imports liquidity proxy helpers directly from portfolio_backtester",
        },
        {
            "source_path": "src/strategy_pipeline_internal/contracts/backtest.py",
            "owner_repo": "portfolio-backtester",
            "target_path": "src/portfolio_backtester/backtest_contracts.py",
            "status": "complete",
            "owner_commit": "7a7338629e19f4d8639cd13dcb31765a22acd2b3",
            "internal_commit": "c50b101b9c200914404a080eed77f47df6116891",
            "test_evidence": (
                "portfolio-backtester tests/test_backtest_output_contracts.py; "
                "internal tests/test_backtest_contracts.py"
            ),
            "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
            "consumer_switch": (
                "internal compatibility exports now delegate to "
                "portfolio_backtester.backtest_contracts"
            ),
        },
        {
            "source_path": "src/strategy_pipeline_internal/contracts/signals.py",
            "owner_repo": "alpha-research",
            "target_path": "src/alpha_research/signal_artifact.py",
            "status": "complete",
            "owner_commit": "e2b71e6871ae1b0f9ce16511a9dca1244a23415a",
            "internal_commit": "9d895b411cc4425878ab896ce7efbacd8310ae9f",
            "test_evidence": (
                "alpha-research tests/test_signal_artifact.py; "
                "internal tests/test_signal_contracts.py; "
                "internal tests/test_research_abstractions.py; "
                "internal tests/test_external_signals.py"
            ),
            "doc_evidence": "alpha-research/docs/reference/signal-artifacts.md",
            "consumer_switch": (
                "internal compatibility exports now delegate to alpha_research.signal_artifact"
            ),
        },
        {
            "source_path": "src/strategy_pipeline_internal/contracts/rebalance.py",
            "owner_repo": "portfolio-backtester",
            "target_path": "src/portfolio_backtester/rebalance.py",
            "status": "complete",
            "owner_commit": "7a7338629e19f4d8639cd13dcb31765a22acd2b3",
            "internal_commit": "df444be",
            "test_evidence": (
                "portfolio-backtester tests/test_rebalance.py; "
                "internal tests/test_rebalance_contracts.py"
            ),
            "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
            "consumer_switch": (
                "internal compatibility exports now delegate to portfolio_backtester.rebalance"
            ),
        },
    ]
