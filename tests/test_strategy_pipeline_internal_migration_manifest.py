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
        "python_source_files": 95,
        "test_files": 225,
        "script_files": 34,
        "config_files": 18,
        "ownership_document_files": 114,
        "ownership_document_status_counts": {
            "complete": 14,
            "private": 58,
            "planned": 10,
            "archive": 32,
        },
    }


def test_module_groups_have_unique_active_ownership_and_evidence() -> None:
    payload = _load_manifest()
    groups = payload["module_groups"]
    assert isinstance(groups, list)
    assert sum(group["file_count"] for group in groups) == 95
    assert len({group["source_path"] for group in groups}) == len(groups)

    for group in groups:
        assert REQUIRED_RECORD_FIELDS <= group.keys()
        assert group["status"] in VALID_STATUSES
        assert group["owner_repo"] != "strategy-pipeline-internal"
        assert group["test_evidence"]
        assert group["doc_evidence"]
        assert group["removal_condition"]


def test_policy_snapshot_migration_records_strategy_app_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/daily_watch20_policy_snapshot.py"]

    assert migration["owner_repo"] == "strategy-app"
    assert migration["target_path"] == "src/strategy_app/daily_watch20/policy_snapshot.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "5871a404aff95a0d8d1495dba627e0da127ced80"
    assert migration["internal_commit"] == "4e2f5edf9fc1168113fe1b06fd2dd76b745ddef9"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_identity_migration_records_public_owner_and_retirement() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/identity.py"]

    assert migration["owner_repo"] == "strategy-pipeline"
    assert migration["target_path"] == "src/strategy_pipeline/identity.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "6571c9cc110c98c26e0ac209eac45f3c91fd24d0"
    assert migration["internal_commit"] == "5a4aa78c51ae6910de28f2804130b45b1d8dfd19"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_owner_ports_migration_records_public_control_plane_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/pipeline/owner_ports.py"]

    assert migration["owner_repo"] == "strategy-pipeline"
    assert migration["target_path"] == "src/strategy_pipeline/control_plane/ports.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "96b1381a0c098c239938400334abb0e6a1b5a752"
    assert migration["internal_commit"] == "f66bda6f066aa9df6adaa6b4a8407c6395561f7a"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_trial_registry_migration_records_strategy_research_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/pipeline/research_ops/trial_registry.py"]

    assert migration["owner_repo"] == "strategy-research"
    assert migration["target_path"] == "src/strategy_research/trial_registry.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "478ac23583784e6c6080b3a14f16c98f4c623aae"
    assert migration["internal_commit"] == "2818bf2421bc4e3a1c453b0669ce8aca966bb58c"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_weekly_analysis_migration_records_strategy_research_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/weekly_analysis_artifacts.py"]

    assert migration["owner_repo"] == "strategy-research"
    assert migration["target_path"] == "src/strategy_research/weekly_analysis_artifacts.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "1be76c5fca862404028843faa4cc29fc1578c640"
    assert migration["internal_commit"] == "2ace7c2bba8817e281d2e105ad6171b8ead105c8"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_news_heat_export_migration_records_owner_and_consumer_switch() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/daily_watch20_news_heat_export.py"]

    assert migration["owner_repo"] == "strategy-app"
    assert migration["target_path"] == "src/strategy_app/daily_watch20/news_heat_export.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "60b87f454552311e874f837471d2e9b38300fc3e"
    assert migration["internal_commit"] == "442eb4b6c5dcbc341991641530cc1eb66348a93c"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_style_factor_refresh_migration_records_owner_and_consumer_switch() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/style_factor_publication.py"]

    assert migration["owner_repo"] == "strategy-research"
    assert migration["target_path"] == "src/style_factors/refresh.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "da296bf5fc4761d44bc1da28e65d600ab5b39590"
    assert migration["internal_commit"] == "6efa17cfb58dc0a67cc07fd3c46540baafb486f1"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_allocation_reference_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/liveops/allocation_reference.py"]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/allocation_reference.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "8a6d836110f81678415d7eb02ec8a7e8e156655c"
    assert migration["internal_commit"] == "ba7b4a2b86822506a95f5d67971d92db19bb8637"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_allocation_rendering_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/liveops/alloc_rendering.py"]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/allocation_rendering.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "622c3874200438e6dda80748795f223ede6d3009"
    assert migration["internal_commit"] == "1f5f2c3d594e0f52ed90c43faa5b7070d882f512"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_allocation_selection_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/liveops/alloc_selection.py"]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/allocation_selection.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "81c80ee8054a35f1566b0f5f82756992f805ae2b"
    assert migration["internal_commit"] == "cfe5cf69191cd40a102c5625faa13dd895f25cca"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_afml_evidence_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/afml_evidence.py"]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/afml_evidence.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "5476e6c21219e24eadd44807e54aae7c6c1e1733"
    assert migration["internal_commit"] == "136357b2e0372943c9064d5d2e97b0ac729ddb45"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_target_lineage_migration_records_workspace_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/liveops/export_targets_envelope.py"]

    assert migration["owner_repo"] == "research-workspace"
    assert migration["target_path"] == "src/research_contracts/target_lineage.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "b017163dc94a3cb51d8d7048703873e2f07cb9a8"
    assert migration["internal_commit"] == "29c07385157a18e5a6a3ccf788688a77825976ac"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_promotion_sidecar_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/promotion_sidecar.py"]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/promotion_sidecar.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "8cdb4d6971ca489088b84a72d6ae472b1f54a9cc"
    assert migration["internal_commit"] == "4d2ea8028456d9a0b19f2bbf4f876d0fe28a7d11"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_position_output_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/pipeline/position_output_artifacts.py"]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/position_outputs.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "e06e48eb443dad47b492eee084cf3299edcd3024"
    assert migration["internal_commit"] == "4d2ea8028456d9a0b19f2bbf4f876d0fe28a7d11"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_position_postprocess_migration_records_portfolio_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations[
        "src/strategy_pipeline_internal/pipeline/position_postprocess_artifacts.py"
    ]

    assert migration["owner_repo"] == "portfolio-backtester"
    assert migration["target_path"] == "src/portfolio_backtester/position_postprocess_outputs.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "9357711768d8c58febbc57b9ba1d9877ea1a046a"
    assert migration["internal_commit"] == "a763a0d957a08c517b56f5a5504269d88004b613"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_output_context_migration_records_public_owner() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/pipeline/output_context.py"]

    assert migration["owner_repo"] == "strategy-pipeline"
    assert migration["target_path"] == "src/strategy_pipeline/control_plane/output_context.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "02f8b789ed66eadf664365d38358ae298bb2dab4"
    assert migration["internal_commit"] == "cc0824e8b5f991dbb7781b8637414d69ff956409"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


def test_minute_feature_migration_records_owner_and_consumer_switch() -> None:
    payload = _load_manifest()
    migrations = {item["source_path"]: item for item in payload["completed_code_migrations"]}
    migration = migrations["src/strategy_pipeline_internal/daily_watch20_minute.py"]

    assert migration["owner_repo"] == "strategy-app"
    assert migration["target_path"] == "src/strategy_app/daily_watch20/minute_features.py"
    assert migration["status"] == "complete"
    assert migration["owner_commit"] == "c9a4273c6befaad50abe114cc529866e80c44469"
    assert migration["internal_commit"] == "f9e07e2427d677c535d998f1f41d9c9451fecbf1"
    assert migration["test_evidence"]
    assert migration["doc_evidence"]
    assert migration["consumer_switch"]


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


def test_daily_watch20_research_documents_record_strategy_app_owner() -> None:
    payload = _load_manifest()
    documents = {document["source_path"]: document for document in payload["planned_documents"]}
    expected = {
        "docs/research/daily-watch20-live-readiness-20260714.md",
        "docs/research/incumbent-challenger-evidence-v2.md",
        "docs/research/next-open-to-high-audit.md",
    }
    for source_path in expected:
        document = documents[source_path]
        assert document["owner_repo"] == "strategy-app"
        assert document["status"] == "complete"
        assert document["test_evidence"]


def test_cross_repository_playbooks_record_workspace_owner() -> None:
    payload = _load_manifest()
    documents = {document["source_path"]: document for document in payload["planned_documents"]}
    baseline = documents["docs/playbooks/a-share-baseline.md"]
    assert baseline["owner_repo"] == "research-workspace"
    assert baseline["status"] == "complete"
    assert baseline["test_evidence"]

    catalog = documents["docs/strategy-catalog.md"]
    assert catalog["owner_repo"] == "research-workspace"
    assert catalog["status"] == "complete"
    assert catalog["test_evidence"]


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

    for source_path in (
        "src/strategy_pipeline_internal/commands/tune/__init__.py",
        "src/strategy_pipeline_internal/__init__.py",
        "src/strategy_pipeline_internal/liveops/__init__.py",
        "src/strategy_pipeline_internal/commands/__init__.py",
        "src/strategy_pipeline_internal/release_tools/__init__.py",
    ):
        empty_package_facade = facades[source_path]
        assert empty_package_facade["status"] == "complete"
        expected_commit = (
            "52ad0e5b7c35b368ac52e2b22b4d245a6f56f508"
            if source_path
            == "src/strategy_pipeline_internal/commands/tune/__init__.py"
            else "80a53406128b0cf0e817cb7cb43dbee5c88ea199"
            if source_path
            in {
                "src/strategy_pipeline_internal/__init__.py",
                "src/strategy_pipeline_internal/liveops/__init__.py",
            }
            else "4da45c7d64168d1bd51f609592111ab189b17a0a"
        )
        assert empty_package_facade["internal_commit"] == expected_commit
        assert empty_package_facade["test_evidence"]
        assert empty_package_facade["rationale"]

    assert facade["status"] == "complete"
    assert facade["internal_commit"] == "2d6d132f0588001dcbd244000af52109603050c8"
    assert facade["test_evidence"]
    assert facade["rationale"]

    context_builder = facades["src/strategy_pipeline_internal/pipeline/context_builder.py"]
    assert context_builder["status"] == "complete"
    assert context_builder["internal_commit"] == "5b51c2059b987869c9d4e876073bcf22288f3a19"
    assert context_builder["test_evidence"]
    assert context_builder["rationale"]

    panel_load_steps = facades["src/strategy_pipeline_internal/pipeline/panel_load_steps.py"]
    assert panel_load_steps["status"] == "complete"
    assert panel_load_steps["internal_commit"] == "2f9f5c144ee218cc99fbac8fbe973831b3cac2a9"
    assert panel_load_steps["test_evidence"]
    assert panel_load_steps["rationale"]

    external_signals = facades["src/strategy_pipeline_internal/pipeline/external_signals.py"]
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

    hotsector_plans = facades["src/strategy_pipeline_internal/hotsector_deepseek_v4_month_plans.py"]
    assert hotsector_plans["status"] == "complete"
    assert hotsector_plans["internal_commit"] == "510bd117337919309c565999d1d9260f286988b3"
    assert hotsector_plans["test_evidence"]
    assert hotsector_plans["rationale"]

    hotsector_execution = facades[
        "src/strategy_pipeline_internal/hotsector_deepseek_v4_month_execution.py"
    ]
    assert hotsector_execution["status"] == "complete"
    assert hotsector_execution["internal_commit"] == "941ed0eca9b03d5c48991150b3401c1a0dc7e3f0"
    assert hotsector_execution["test_evidence"]
    assert hotsector_execution["rationale"]

    hotsector_backtest = facades[
        "src/strategy_pipeline_internal/hotsector_deepseek_v4_month_backtest.py"
    ]
    assert hotsector_backtest["status"] == "complete"
    assert hotsector_backtest["internal_commit"] == "b603ff7a9628dc449d721104816b6062549920dd"
    assert hotsector_backtest["test_evidence"]
    assert hotsector_backtest["rationale"]

    hotsector_campaign = facades["src/strategy_pipeline_internal/hotsector_deepseek_campaign.py"]
    assert hotsector_campaign["status"] == "complete"
    assert hotsector_campaign["internal_commit"] == "f8fffa5172af7640784f5fb8cb6f6a5ba70c88b1"
    assert hotsector_campaign["test_evidence"]
    assert hotsector_campaign["rationale"]

    daily_watch20_ablation = facades["src/strategy_pipeline_internal/daily_watch20_ablation.py"]
    assert daily_watch20_ablation["status"] == "complete"
    assert daily_watch20_ablation["internal_commit"] == "58068cd719022559822d93ba9b105b5c37020bae"
    assert daily_watch20_ablation["test_evidence"]
    assert daily_watch20_ablation["rationale"]

    package_runs = facades["src/strategy_pipeline_internal/release_tools/package_runs.py"]
    assert package_runs["status"] == "complete"
    assert package_runs["internal_commit"] == "b38f69f3168412c1df0aee2abc65568f93a14bf6"
    assert package_runs["test_evidence"]
    assert package_runs["rationale"]

    slow_minute_campaign = facades[
        "src/strategy_pipeline_internal/daily_watch20_slow_minute_campaign.py"
    ]
    assert slow_minute_campaign["status"] == "complete"
    assert slow_minute_campaign["internal_commit"] == "5cf7c2f8731324071ae2ead7bd8ec7825ff27cf1"
    assert slow_minute_campaign["test_evidence"]
    assert slow_minute_campaign["rationale"]

    minute_campaign = facades["src/strategy_pipeline_internal/daily_watch20_minute_campaign.py"]
    assert minute_campaign["status"] == "complete"
    assert minute_campaign["internal_commit"] == "a198c155a5cc59ca04e0d7b1bcfd5f0ba48980d4"
    assert minute_campaign["test_evidence"]
    assert minute_campaign["rationale"]

    minute_campaign_inputs = facades[
        "src/strategy_pipeline_internal/daily_watch20_minute_campaign_inputs.py"
    ]
    assert minute_campaign_inputs["status"] == "complete"
    assert minute_campaign_inputs["internal_commit"] == "9c9555de0b1bdff85ebbb0dcc813795d5535f075"
    assert minute_campaign_inputs["test_evidence"]
    assert minute_campaign_inputs["rationale"]

    market_shadow = facades["src/strategy_pipeline_internal/daily_watch20_market_shadow.py"]
    assert market_shadow["status"] == "complete"
    assert market_shadow["internal_commit"] == "8be7c39894bcbb338b981a6868aee97f0d4dbc11"
    assert market_shadow["test_evidence"]
    assert market_shadow["rationale"]

    application_policy = facades[
        "src/strategy_pipeline_internal/daily_watch20_application_policy.py"
    ]
    assert application_policy["status"] == "complete"
    assert application_policy["internal_commit"] == "e405209db006989bdd7288ebd324e845d822e5b7"
    assert application_policy["test_evidence"]
    assert application_policy["rationale"]


def test_completed_boundary_cleanups_are_recorded_with_evidence() -> None:
    payload = _load_manifest()
    cleanups = {item["source_path"]: item for item in payload["completed_boundary_cleanups"]}
    cleanup = cleanups["src/strategy_pipeline_internal/pipeline/research_ops/__init__.py"]

    assert cleanup["status"] == "complete"
    assert cleanup["internal_commit"] == "2ba256df7f50f5457a78c8f1d34eb7691cbd122c"
    assert cleanup["test_evidence"]
    assert cleanup["consumer_switch"]
