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
        "python_source_files": 146,
        "test_files": 201,
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
    assert sum(group["file_count"] for group in groups) == 146
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


def test_train_eval_contract_facade_migration_records_alpha_owner() -> None:
    payload = _load_manifest()
    migration = next(
        item
        for item in payload["completed_code_migrations"]
        if item["source_path"] == "src/strategy_pipeline_internal/pipeline/contracts.py"
    )

    assert migration["owner_repo"] == "alpha-research"
    assert migration["target_path"] == "src/alpha_research/train_eval_contracts.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "6dd0de84e3639d233e6b71a8820b198b117cc22f"
    assert migration["internal_commit"] == "7513bd72c9ac8162670fabb0439c7d66062f979a"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_owner_facade_migrations_record_owner_repositories() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    expected = {
        "src/strategy_pipeline_internal/pipeline/eval_benchmark.py": (
            "portfolio-backtester",
            "src/portfolio_backtester/benchmarking.py",
        ),
        "src/strategy_pipeline_internal/pipeline/train_eval_request_builder.py": (
            "alpha-research",
            "src/alpha_research/train_eval_request_builder.py",
        ),
        "src/strategy_pipeline_internal/pipeline/train_eval_result.py": (
            "alpha-research",
            "src/alpha_research/train_eval_result.py",
        ),
    }
    for source_path, (owner_repo, target_path) in expected.items():
        assert migrations[source_path]["owner_repo"] == owner_repo
        assert migrations[source_path]["target_path"] == target_path
        assert migrations[source_path]["status"] == "complete"


def test_dataset_sampling_migration_records_alpha_owner() -> None:
    payload = _load_manifest()
    migration = next(
        item
        for item in payload["completed_code_migrations"]
        if item["source_path"] == "src/strategy_pipeline_internal/pipeline/dataset_sampling.py"
    )

    assert migration["owner_repo"] == "alpha-research"
    assert migration["target_path"] == "src/alpha_research/dataset_sampling.py"
    assert migration["status"] == "complete"
    assert migration["internal_commit"] == "1b6d54b1e29867793f2a0b56f3b0a8d1a578f46c"


def test_date_migration_records_alpha_owner() -> None:
    payload = _load_manifest()
    migration = next(
        item
        for item in payload["completed_code_migrations"]
        if item["source_path"] == "src/strategy_pipeline_internal/pipeline/dates.py"
    )

    assert migration["owner_repo"] == "alpha-research"
    assert migration["target_path"] == (
        "src/alpha_research/date_slices.py; src/alpha_research/walk_forward_windows.py"
    )
    assert migration["status"] == "complete"
    assert migration["internal_commit"] == "3e1e1660dd0a8362d5ae45f71610ffb2aa049a11"


def test_freshness_overlay_migration_records_alpha_owner() -> None:
    payload = _load_manifest()
    migration = next(
        item
        for item in payload["completed_code_migrations"]
        if item["source_path"] == "src/strategy_pipeline_internal/pipeline/freshness_overlay.py"
    )

    assert migration["owner_repo"] == "alpha-research"
    assert migration["target_path"] == "src/alpha_research/freshness_overlay.py"
    assert migration["status"] == "complete"
    assert migration["internal_commit"] == "29cf2f2d3a98549ce05c62c6d82a7de9b839224c"


def test_publication_tier_migration_records_strategy_app_owner() -> None:
    payload = _load_manifest()
    migration = next(
        item
        for item in payload["completed_code_migrations"]
        if item["source_path"] == "src/strategy_pipeline_internal/daily_watch20_publication_tier.py"
    )

    assert migration["owner_repo"] == "strategy-app"
    assert migration["target_path"] == "src/strategy_app/daily_watch20/publication_tier.py"
    assert migration["status"] == "complete"
    assert migration["internal_commit"] == "3d7ac1d6535e5181dbea91b2bd8be45670d81330"


def test_promotion_gate_migrations_record_alpha_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    expected = {
        "src/strategy_pipeline_internal/pipeline/research_ops/promotion_gate.py": (
            "src/alpha_research/promotion_gate.py"
        ),
        "src/strategy_pipeline_internal/pipeline/research_ops/promotion_gate_thresholds.py": (
            "src/alpha_research/promotion_gate_thresholds.py"
        ),
    }
    for source_path, target_path in expected.items():
        assert migrations[source_path]["owner_repo"] == "alpha-research"
        assert migrations[source_path]["target_path"] == target_path
        assert migrations[source_path]["status"] == "complete"


def test_retired_internal_facades_are_recorded_with_evidence() -> None:
    payload = _load_manifest()
    facades = {item["source_path"]: item for item in payload["retired_internal_facades"]}
    facade = facades["src/strategy_pipeline_internal/pipeline/panel_enrichment.py"]

    assert facade["status"] == "complete"
    assert facade["internal_commit"] == "2d6d132f0588001dcbd244000af52109603050c8"
    assert facade["test_evidence"]
    assert facade["rationale"]

    context_builder = facades["src/strategy_pipeline_internal/pipeline/context_builder.py"]
    assert context_builder["status"] == "complete"
    assert context_builder["internal_commit"] == "5b51c2059b987869c9d4e876073bcf22288f3a19"
    assert context_builder["test_evidence"]
    assert context_builder["rationale"]

    panel_load_steps = facades[
        "src/strategy_pipeline_internal/pipeline/panel_load_steps.py"
    ]
    assert panel_load_steps["status"] == "complete"
    assert panel_load_steps["internal_commit"] == "2f9f5c144ee218cc99fbac8fbe973831b3cac2a9"
    assert panel_load_steps["test_evidence"]
    assert panel_load_steps["rationale"]

    external_signals = facades[
        "src/strategy_pipeline_internal/pipeline/external_signals.py"
    ]
    assert external_signals["status"] == "complete"
    assert external_signals["internal_commit"] == "77519f89828a72fc3141e5aacb60bd2f9a06ddc5"
    assert external_signals["test_evidence"]
    assert external_signals["rationale"]

    summarize_runs = facades[
        "src/strategy_pipeline_internal/pipeline/research_ops/summarize_runs.py"
    ]
    assert summarize_runs["status"] == "complete"
    assert summarize_runs["internal_commit"] == "adf73b0caa93a1ecec6d806ac1079e3fd785ace6"
    assert summarize_runs["test_evidence"]
    assert summarize_runs["rationale"]

    runner = facades["src/strategy_pipeline_internal/pipeline/runner.py"]
    assert runner["status"] == "complete"
    assert runner["internal_commit"] == "311592c8a0d12ee586a39ec54800065c0b72ae98"
    assert runner["test_evidence"]
    assert runner["rationale"]

    linear_sweep = facades["src/strategy_pipeline_internal/commands/linear_sweep.py"]
    assert linear_sweep["status"] == "complete"
    assert linear_sweep["internal_commit"] == "18f59c659fbf2500d9d4a9727edaf63e6cef1fab"
    assert linear_sweep["test_evidence"]
    assert linear_sweep["rationale"]

    freshness = facades["src/strategy_pipeline_internal/daily_watch20_freshness.py"]
    assert freshness["status"] == "complete"
    assert freshness["internal_commit"] == "5a7dd5ad594d5defd5c9dbb4e02b5ac858a88986"
    assert freshness["test_evidence"]
    assert freshness["rationale"]

    publication_validation = facades[
        "src/strategy_pipeline_internal/daily_watch20_publication_validation.py"
    ]
    assert publication_validation["status"] == "complete"
    assert publication_validation["internal_commit"] == "7b5ef7ba1179910ae017e15e7b0884b6d007f267"
    assert publication_validation["test_evidence"]
    assert publication_validation["rationale"]

    publish = facades["src/strategy_pipeline_internal/daily_watch20_publish.py"]
    assert publish["status"] == "complete"
    assert publish["internal_commit"] == "5cb4f61bda260a3a31e13908858d7cc5bd52ae2c"
    assert publish["test_evidence"]
    assert publish["rationale"]

    publication_inputs = facades[
        "src/strategy_pipeline_internal/daily_watch20_publication_inputs.py"
    ]
    assert publication_inputs["status"] == "complete"
    assert publication_inputs["internal_commit"] == "19e5924b72e7ebd83aa79c6a054c885f9aa3b8ff"
    assert publication_inputs["test_evidence"]
    assert publication_inputs["rationale"]

    hotsector_support = facades[
        "src/strategy_pipeline_internal/hotsector_deepseek_campaign_support.py"
    ]
    assert hotsector_support["status"] == "complete"
    assert hotsector_support["internal_commit"] == "9c695366023613f2b3544f18b07c6996103f1da9"
    assert hotsector_support["test_evidence"]
    assert hotsector_support["rationale"]


def test_completed_boundary_cleanups_are_recorded_with_evidence() -> None:
    payload = _load_manifest()
    cleanups = {
        item["source_path"]: item for item in payload["completed_boundary_cleanups"]
    }
    cleanup = cleanups["src/strategy_pipeline_internal/pipeline/research_ops/__init__.py"]

    assert cleanup["status"] == "complete"
    assert cleanup["internal_commit"] == "cd5d9e0411a97242d71eabc971824d79024cbdd9"
    assert cleanup["test_evidence"]
    assert cleanup["consumer_switch"]
