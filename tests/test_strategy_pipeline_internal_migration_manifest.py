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
    assert payload["inventory"] == {
        "python_source_files": 168,
        "test_files": 185,
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
    assert sum(group["file_count"] for group in groups) == 168
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


def test_style_replica_migrations_record_owner_and_consumer_switch() -> None:
    payload = _load_manifest()
    migrations = payload["completed_code_migrations"]
    assert isinstance(migrations, list)

    style_replica = {
        migration["source_path"]: migration
        for migration in migrations
        if "style_replica_pipeline" in migration["source_path"]
    }
    expected_sources = {
        "src/strategy_pipeline_internal/_style_replica_pipeline_core.py",
        "src/strategy_pipeline_internal/_style_replica_pipeline_output.py",
        "src/strategy_pipeline_internal/_style_replica_pipeline_owner_api.py",
        "src/strategy_pipeline_internal/style_replica_pipeline.py",
    }
    assert set(style_replica) == expected_sources

    for migration in style_replica.values():
        assert REQUIRED_RECORD_FIELDS <= migration.keys()
        assert migration["status"] == "complete"
        assert migration["owner_repo"] == "strategy-app"
        assert migration["target_path"].startswith("src/strategy_app/style_replica/")
        assert migration["owner_commit"] == "a30fe5af462c9baeabcb499eb5ae183a1873c419"
        assert migration["internal_commit"] == "3a4191213dd7f1645844076d628658aa66088178"
        assert migration["test_evidence"]
        assert migration["doc_evidence"]
        assert migration["consumer_switch"]


def test_d11_h5_migration_records_owner_and_consumer_switch() -> None:
    payload = _load_manifest()
    migrations = payload["completed_code_migrations"]
    migration = next(
        item
        for item in migrations
        if item["source_path"] == "src/strategy_pipeline_internal/d11_h5_shadow.py"
    )

    assert migration == {
        "source_path": "src/strategy_pipeline_internal/d11_h5_shadow.py",
        "owner_repo": "strategy-app",
        "target_path": "src/strategy_app/daily_watch20/d11_h5_shadow.py",
        "status": "complete",
        "owner_commit": "b59a881da300a06a65d8420b626e0306f4971fdd",
        "internal_commit": "8414f8a412b2d96fdb0fc48c062b7fb3e398dda7",
        "test_evidence": (
            "strategy-app tests/test_d11_h5_shadow_pipeline.py; "
            "internal tests/test_retired_d11_h5_shadow.py"
        ),
        "doc_evidence": "strategy-app/docs/application-catalog.md",
        "consumer_switch": "internal D11-H5 CLI registration now imports the strategy-app owner",
    }


def test_afml_lineage_migration_records_public_owner() -> None:
    payload = _load_manifest()
    migration = next(
        item
        for item in payload["completed_code_migrations"]
        if item["source_path"] == "src/strategy_pipeline_internal/afml_lineage.py"
    )

    assert migration["owner_repo"] == "strategy-pipeline"
    assert migration["target_path"] == "src/strategy_pipeline/control_plane/afml_lineage.py"
    assert migration["owner_commit"] == "e15d463cde0512e5cbf9cc24b95f09f6c9c898ea"
    assert migration["internal_commit"] == "e4f75b92c031e4e634d40f8581e614b0cf572633"
    assert migration["status"] == "complete"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]
