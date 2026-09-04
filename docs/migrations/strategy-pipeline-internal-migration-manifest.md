# strategy-pipeline-internal 迁移清单

> status: active
> owner: workspace
> source_of_truth: yes
> source_commit: `dd67539d6057189b8d04b463974defd338b6dbc2`
> last_verified: 2026-09-05

这份清单记录 internal 当前 main 的迁移起点。模块记录按职责分组，文件数量来自 Git tree。文档记录保留逐文件的迁移判断，后续每个切片合并后更新 `status`、目标路径和证据字段。

```json
{
  "schema_version": "strategy_pipeline_internal_migration.v1",
  "source_repository": "runchengxie/strategy-pipeline-internal",
  "source_commit": "dd67539d6057189b8d04b463974defd338b6dbc2",
  "inventory": {
    "python_source_files": 95,
    "test_files": 226,
    "script_files": 34,
    "config_files": 18,
    "ownership_document_files": 114,
    "ownership_document_status_counts": {
        "complete": 16,
      "private": 58,
        "planned": 8,
      "archive": 32
    }
  },
  "module_groups": [
    {
      "source_path": "src/strategy_pipeline_internal/cli",
      "file_count": 7,
      "owner_repo": "research-workspace",
      "target_path": "workspace entrypoints and owner-native commands",
      "status": "private",
      "test_evidence": "workspace CLI smoke is the migration gate",
      "doc_evidence": "docs/cli.md and workspace bootstrap docs",
      "removal_condition": "no active workspace command invokes internal CLI"
    },
    {
      "source_path": "src/strategy_pipeline_internal/commands",
      "file_count": 9,
      "owner_repo": "research-workspace",
      "target_path": "scripts and workspace entrypoints",
      "status": "private",
      "test_evidence": "workspace command and pre-push smoke tests",
      "doc_evidence": "workspace maintenance and bootstrap docs",
      "removal_condition": "all commands have owner-native replacements"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops",
      "file_count": 4,
      "owner_repo": "quant-execution-engine",
      "target_path": "src/quant_execution_engine/liveops",
      "status": "planned",
      "test_evidence": "execution audit and run smoke tests",
      "doc_evidence": "execution and operational runbook",
      "removal_condition": "execution engine owns liveops and audit entrypoints"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline",
      "file_count": 31,
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/control_plane",
      "status": "planned",
      "test_evidence": "public clean-room control-plane tests",
      "doc_evidence": "strategy-pipeline public API docs",
      "removal_condition": "remaining pipeline modules contain no domain knowledge"
    },
    {
      "source_path": "src/strategy_pipeline_internal/release_tools",
      "file_count": 5,
      "owner_repo": "research-workspace",
      "target_path": "scripts and release governance",
      "status": "private",
      "test_evidence": "release gate and version matrix tests",
      "doc_evidence": "release checklist and version matrix",
      "removal_condition": "workspace release tooling no longer imports internal"
    },
    {
      "source_path": "src/strategy_pipeline_internal/root_modules",
      "file_count": 39,
      "owner_repo": "strategy-app",
      "target_path": "owner-specific modules recorded in the next slice manifest",
      "status": "private",
      "test_evidence": "per-module tests required before status changes",
      "doc_evidence": "per-module owner documentation required before status changes",
      "removal_condition": "every active root module has a unique owner and migrated test"
    }
  ],
  "planned_documents": [
    {"source_path": "docs/concepts/afml-lineage.md", "owner_repo": "alpha-research", "target_path": "docs/concepts/afml-methodology.md; docs/reference/signal-artifacts.md", "status": "complete", "test_evidence": "tests/test_afml_methodology.py; tests/test_signal_artifact.py"},
    {"source_path": "docs/concepts/data-sources.md", "owner_repo": "market-data-platform", "target_path": "docs/contracts.md; docs/operations/a-share-tushare.md", "status": "complete", "test_evidence": "tests/test_tushare_platform_assets.py; tests/test_data_providers_cache.py"},
    {"source_path": "docs/concepts/metric-ownership.md", "owner_repo": "research-workspace", "target_path": "docs/metric-ownership.md", "status": "complete", "test_evidence": "tests/test_metric_ownership_document.py", "doc_evidence": "docs/metric-ownership.md", "migration_pr": "pending"},
    {"source_path": "docs/concepts/pit-coverage.md", "owner_repo": "market-data-platform", "target_path": "docs/a-share-fundamentals.md; docs/contracts.md", "status": "complete", "test_evidence": "tests/test_tushare_a_share_fundamentals.py; tests/test_current_path_audit.py"},
    {"source_path": "docs/concepts/research-protocols.md", "owner_repo": "alpha-research", "target_path": "docs/concepts/feature-research-protocol.md; docs/concepts/overfitting-controls.md", "status": "complete", "test_evidence": "tests/test_feature_evidence.py; tests/test_promotion_gate.py"},
    {"source_path": "docs/concepts/shared-hk-data-platform.md", "owner_repo": "market-data-platform", "target_path": "docs/operations/hk-archive-restore.md; docs/contracts.md", "status": "complete", "test_evidence": "tests/test_quality_governance.py; tests/test_dataset_contracts.py"},
    {"source_path": "docs/playbooks/a-share-baseline.md", "owner_repo": "strategy-app", "target_path": "docs/playbooks/a-share-baseline.md", "status": "complete", "test_evidence": "tests/test_a_share_baseline_playbook.py", "doc_evidence": "strategy-app/docs/playbooks/a-share-baseline.md; strategy-app PR #73", "migration_pr": "strategy-app PR #73"},
    {"source_path": "docs/playbooks/hk-selected.md", "owner_repo": "strategy-app", "target_path": "docs/playbooks/hk-selected.md", "status": "complete", "test_evidence": "strategy-app docs index", "doc_evidence": "strategy-app/docs/playbooks/hk-selected.md; strategy-app PR #73", "migration_pr": "strategy-app PR #73"},
    {"source_path": "docs/providers.md", "owner_repo": "market-data-platform", "target_path": "docs/integrations.md; docs/operations/credentials.md", "status": "complete", "test_evidence": "tests/test_data_providers_cache.py; tests/test_cli_dependency_boundaries.py"},
    {"source_path": "docs/reference/outputs/full-reference.md", "owner_repo": "research-workspace", "target_path": "docs/reference/outputs/full-reference.md", "status": "complete", "test_evidence": "workspace migration manifest validation; cross-repository output contract links reviewed", "doc_evidence": "docs/reference/outputs/full-reference.md"},
    {"source_path": "docs/reference/outputs/platform-assets.md", "owner_repo": "market-data-platform", "target_path": "docs/contracts.md; docs/data-warehouse.md", "status": "complete", "test_evidence": "tests/test_paths.py; tests/test_data_warehouse.py"},
    {"source_path": "docs/research/README.md", "owner_repo": "strategy-app", "target_path": "docs/research/README.md", "status": "complete", "test_evidence": "strategy-app docs index", "doc_evidence": "strategy-app/docs/research/README.md; strategy-app PR #65", "migration_pr": "strategy-app PR #65"},
    {"source_path": "docs/research/daily-watch20-live-readiness-20260714.md", "owner_repo": "strategy-app", "target_path": "docs/research/daily-watch20-live-readiness-20260714.md", "status": "complete", "test_evidence": "strategy-app PR #65; strategy-app docs/research/README.md"},
    {"source_path": "docs/research/incumbent-challenger-evidence-v2.md", "owner_repo": "strategy-app", "target_path": "docs/research/incumbent-challenger-evidence-v2.md", "status": "complete", "test_evidence": "strategy-app PR #65; strategy-app docs/research/README.md"},
    {"source_path": "docs/research/next-open-to-high-audit.md", "owner_repo": "strategy-app", "target_path": "docs/research/next-open-to-high-audit.md", "status": "complete", "test_evidence": "strategy-app PR #65; strategy-app docs/research/README.md"},
    {"source_path": "docs/strategy-catalog.md", "owner_repo": "research-workspace", "target_path": "docs/strategy-catalog.md", "status": "complete", "test_evidence": "tests/test_strategy_catalog_document.py", "doc_evidence": "docs/strategy-catalog.md", "migration_pr": "pending"}
  ],
  "completed_code_migrations": [
    {
      "source_path": "src/strategy_pipeline_internal/_hotsector_deepseek_v4_month_execution_api.py; src/strategy_pipeline_internal/_hotsector_deepseek_v4_month_execution_core.py; src/strategy_pipeline_internal/hotsector_deepseek_v4_month_execution_support.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_deepseek_v4_month_execution_api.py; hotsector_deepseek_v4_month_execution_core.py; hotsector_deepseek_v4_month_execution_support.py",
      "status": "complete",
      "owner_commit": "82457420b400c13f4b0d819015a2b6a75af2fd42",
      "internal_commit": "883acb1b847123cff184c06dfed50610c662e865",
      "test_evidence": "strategy-app owner execution tests; internal V4-month execution, backtest, and analysis tests: 29 passed",
      "doc_evidence": "strategy-app/docs/hotsector-deepseek-v4-month-execution.md",
      "consumer_switch": "internal execution and backtest callers now import strategy-app execution modules, while historical paths remain compatibility wrappers"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_hotsector_deepseek_v4_month_plans_core.py; src/strategy_pipeline_internal/_hotsector_deepseek_v4_month_plans_api.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_deepseek_v4_month_plans_core.py; hotsector_deepseek_v4_month_plans_api.py",
      "status": "complete",
      "owner_commit": "d59b5df7f2382ec9ba2e83f6afa7f581b066b0da",
      "internal_commit": "84f8f7dbeefb0813ffeea9af1675f5899ec7f27a",
      "test_evidence": "strategy-app owner plan tests; internal test_hotsector_deepseek_v4_month.py: 20 passed",
      "doc_evidence": "strategy-app/docs/hotsector-deepseek-v4-month-plans.md",
      "consumer_switch": "internal V4-month plan paths now delegate to strategy-app, and the plan regression suite patches the owner module directly"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_hotsector_deepseek_campaign_core.py; src/strategy_pipeline_internal/_hotsector_deepseek_campaign_api.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_deepseek_campaign_core.py; hotsector_deepseek_campaign_api.py",
      "status": "complete",
      "owner_commit": "8cb31eab7937061d0fe183bdecd79260bc2b47b4",
      "internal_commit": "23e30d9eb2d48e97a366931a94ac9f767879e808",
      "test_evidence": "strategy-app tests/test_hotsector_deepseek_campaign_runner.py: 7 passed; internal V4-month and documentation entrypoint tests",
      "doc_evidence": "strategy-app/docs/hotsector-deepseek-campaign-runner.md",
      "consumer_switch": "internal campaign runner paths now delegate to strategy-app compatibility wrappers, and the complete runner regression suite is owned by strategy-app"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_hotsector_deepseek_campaign_support_api.py; src/strategy_pipeline_internal/_hotsector_deepseek_campaign_support_core.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_deepseek_campaign_support_api.py; hotsector_deepseek_campaign_support_core.py",
      "status": "complete",
      "owner_commit": "2ea44ce7dc9f5462fcb929b0b0ea01242237c452",
      "internal_commit": "b626a05484711d911f10ab94f32d8a2511884815",
      "test_evidence": "strategy-app tests/test_hotsector_deepseek_campaign_support.py; internal Hotsector DeepSeek campaign and V4-month regression tests",
      "doc_evidence": "strategy-app/docs/hotsector-deepseek-campaign-support.md",
      "consumer_switch": "Hotsector campaign and V4-month consumers now import serialization, file-integrity, and ledger helpers from strategy-app, while historical paths remain compatibility wrappers"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_daily_watch20_publish_api.py; src/strategy_pipeline_internal/daily_watch20_pipeline_publication.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/publish_api.py; src/strategy_app/daily_watch20/pipeline_publication.py",
      "status": "complete",
      "owner_commit": "fcebf5eaf2b443d8f6e329cd3a4a6d4d60750975",
      "internal_commit": "e681e8e4d49fe5c591a3d36b88ce0bb30ec0992f",
      "test_evidence": "strategy-app tests/test_daily_watch20_publication_orchestration.py; internal publication edge-guard tests; workspace migration contract tests",
      "doc_evidence": "strategy-app/docs/daily-watch20-publication-orchestration.md",
      "consumer_switch": "daily_watch20_pipeline now imports the owner publication adapter directly, while historical publication paths remain compatibility wrappers"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_live_inputs.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/live_input_adapter.py",
      "status": "complete",
      "owner_commit": "e67cb8cc55b93a25ae8654c350e7c178b7784f2f",
      "internal_commit": "1ff1e110da6f12f0f9527bcc52802c79016da457",
      "test_evidence": "strategy-app tests/test_daily_watch20_live_input_adapter.py; internal DailyWatch20 publication safety and tier tests",
      "doc_evidence": "strategy-app/docs/daily-watch20-live-input-adapter.md",
      "consumer_switch": "daily_watch20_pipeline now imports the owner adapter directly, while the historical module path remains a compatibility wrapper"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_daily_watch20_publication_inputs_core.py; src/strategy_pipeline_internal/_daily_watch20_publication_inputs_api.py; src/strategy_pipeline_internal/_daily_watch20_publication_validation_api.py; src/strategy_pipeline_internal/_daily_watch20_publish_core.py; src/strategy_pipeline_internal/_daily_watch20_freshness_core.py; src/strategy_pipeline_internal/_daily_watch20_freshness_api.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/publication_inputs_core.py; publication_inputs_api.py; publication_validation_api.py; publish_core.py; freshness_core.py; freshness_api.py",
      "status": "complete",
      "owner_commit": "1f88c985159f80d2191d83db59fc7cc6a3e93524",
      "internal_commit": "994971292bd3eb3e7d8d25c73affe69611c951c2",
      "test_evidence": "strategy-app tests/test_daily_watch20_freshness.py; tests/test_daily_watch20_publication_validation_core.py; tests/test_daily_watch20_publication_contracts.py; internal DailyWatch20 publication safety, tier, and edge-guard tests: 63 passed",
      "doc_evidence": "strategy-app/docs/daily-watch20-publication-validation.md",
      "consumer_switch": "internal freshness and publication consumers now import strategy-app contracts directly, while six historical module paths remain compatibility wrappers"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_daily_watch20_publication_validation_core.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/publication_validation_core.py",
      "status": "complete",
      "owner_commit": "ae4a6c58181827a86546a2cfd34ba2bfa7865d64",
      "internal_commit": "203e46eb40d72cc2572f8c52835e508d265e2fe8",
      "test_evidence": "strategy-app tests/test_daily_watch20_publication_validation_core.py; internal tests/test_daily_watch20_publication_edge_guards.py",
      "doc_evidence": "strategy-app/docs/daily-watch20-publication-validation.md",
      "consumer_switch": "internal publication validation API now imports the owner module directly, while the historical core path remains a compatibility wrapper"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_pipeline_inputs.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/pipeline_inputs.py",
      "status": "complete",
      "owner_commit": "ea1b9c69261c436e1af5898f05f55157f8fe73da",
      "internal_commit": "cb1e100837627579ac02cc6cfeb056e80788e820",
      "test_evidence": "strategy-app tests/test_pipeline_inputs.py; internal tests/test_daily_watch20_publication_safety.py; internal tests/test_daily_watch20_pipeline.py",
      "doc_evidence": "strategy-app/docs/daily-watch20-publication-window.md; strategy-app DailyWatch20 input planning API",
      "consumer_switch": "internal DailyWatch20 input planning imports now delegate date resolution, overlay roots, and minute asset construction to strategy-app"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_publication_window.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/publication_window.py",
      "status": "complete",
      "owner_commit": "148421802443c4d367e4b809865d0947905b1e1f",
      "internal_commit": "2a49df45f23bcd31eea76696ffc60c6ac7b982e9",
      "test_evidence": "strategy-app tests/test_publication_window.py; internal tests/test_daily_watch20_late_recovery.py",
      "doc_evidence": "strategy-app/docs/daily-watch20-publication-window.md",
      "consumer_switch": "internal DailyWatch20 publication-window imports now delegate to strategy-app while preserving the compatibility surface"
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_challenger_campaign.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_challenger_campaign.py",
      "status": "complete",
      "owner_commit": "6f8eeca7a5c80f1aee1f58ecda91e19004e66d6b",
      "internal_commit": "8fe74ab88b6754fbe4d109feab0fa1d91900b9f7",
      "test_evidence": "strategy-app tests/test_hotsector_challenger_campaign.py; internal tests/test_hotsector_challenger_campaign.py",
      "doc_evidence": "strategy-app/docs/hotsector-challenger-campaign.md",
      "consumer_switch": "internal hotsector challenger imports now delegate to strategy-app while preserving the research script compatibility surface"
    },
    {
      "source_path": "src/strategy_pipeline_internal/e2_evidence.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/e2_evidence.py",
      "status": "complete",
      "owner_commit": "1038c093dd1008ef06d6b11c12b1e4af82f37987",
      "internal_commit": "8b498ce71f47762584061bf0b8caeeb009c48e9b",
      "test_evidence": "strategy-research tests/test_e2_evidence.py; internal tests/test_e2_evidence.py; internal tests/test_e2_promotion_receipt.py",
      "doc_evidence": "strategy-research/docs/evidence-profiles.md; internal docs/evidence/a-share-final-oos-top800-20260824.md",
      "consumer_switch": "internal e2_evidence now delegates benchmark and turnover-cost evidence builders and CLI to strategy-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/research_run.py::ArtifactRef, ValidationSection, ResearchRun, ResearchWorkspace",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/run_artifacts.py",
      "status": "complete",
      "owner_commit": "6f63aeb662c0c7674bdcb28b0e7d48a76bf092bd",
      "internal_commit": "4b4e89af93570e5586e182518a5667a4dd0c7fef",
      "test_evidence": "strategy-research tests/test_run_artifacts.py; internal tests/test_research_run_bundle.py",
      "doc_evidence": "strategy-research/docs/run-artifacts.md; strategy-research PR #46",
      "consumer_switch": "internal research_run now delegates artifact reading and validation to strategy-research while retaining target export in the execution compatibility layer"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/fundamentals_overlay.py::_daily_clean_overlay_frame",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/provider_overlay.py::select_daily_clean_overlay_columns",
      "status": "complete",
      "owner_commit": "5b0979790e1167c62a7d18cdf89b7adb06e7dd69",
      "internal_commit": "4eb6a68d4126bcb7c5bc97e73c279a8403f186ca",
      "test_evidence": "market-data-platform tests/test_provider_overlay.py; internal tests/test_pipeline_validation.py, tests/test_panel_join_support.py, and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "market-data-platform provider overlay API; internal data operations boundary",
      "consumer_switch": "fundamentals overlay now delegates daily-clean provider valuation column selection to market-data-platform"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/industry_enrichment.py::_expand_effective_industry_to_panel_dates",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/industry_history.py::expand_effective_industry_to_panel_dates",
      "status": "complete",
      "owner_commit": "87f543de635c10e1874edb620cb67a76e2905262",
      "internal_commit": "0704f4c85a61efdb6ea519eca05d9c00be216761",
      "test_evidence": "market-data-platform tests/test_industry_history.py; internal tests/test_pipeline_validation.py, tests/test_pipeline_filters_industry.py, tests/test_panel_join_support.py, and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "market-data-platform/docs/concepts/historical-industry-labels.md",
      "consumer_switch": "pipeline industry enrichment now delegates effective-date label expansion to market-data-platform"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/stats.py::_ensure_execution_daily_fields",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/execution_fields.py::ensure_execution_daily_fields",
      "status": "complete",
      "owner_commit": "c80f3e797712e5ab55c60e41e2cbec0d3a035804",
      "internal_commit": "23ff8450b4b7987fb7225338af3c30ee8538ff60",
      "test_evidence": "market-data-platform tests/test_execution_fields.py; internal tests/test_pipeline_validation.py, tests/test_migrated_evaluation_config_normalizers.py, and tests/test_pipeline_leakage_warning.py",
      "doc_evidence": "market-data-platform execution field API; internal data operations boundary",
      "consumer_switch": "pipeline config_backtest now delegates RQData execution field expansion to market-data-platform"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/stats.py::_warn_if_purge_too_small",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::warn_if_purge_too_small",
      "status": "complete",
      "owner_commit": "58e4eced77a71eb45a0b21ab76b74d1b509887a7",
      "internal_commit": "d24d81c37d4288043f10a827c9e7016bcbe59adf",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_leakage_warning.py, tests/test_pipeline_validation.py, and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline runtime now delegates the generic purge-window leakage warning to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_backtest.py::_resolve_backtest_execution_settings",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/execution_config.py::resolve_execution_settings",
      "status": "complete",
      "owner_commit": "f24e0c561c279d6a6c7d1b4baea86ce8b1d6164d",
      "internal_commit": "223d3072a270092ebbc88464c3592d178826496d",
      "test_evidence": "portfolio-backtester tests/test_execution_config.py; internal tests/test_pipeline_validation.py, tests/test_execution_calendar.py, and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "portfolio-backtester execution configuration API; internal pipeline data-field checks",
      "consumer_switch": "internal config_backtest now delegates execution model and simulation configuration while retaining provider field checks"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_backtest.py::_resolve_backtest_base_settings",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/backtest_config.py::resolve_backtest_base_settings",
      "status": "complete",
      "owner_commit": "d9f0e6889e805b27dd1fb8bcc1925e8d8c62a609",
      "internal_commit": "50321e59887dc850ed19fa7b455f77f5617d901b",
      "test_evidence": "portfolio-backtester tests/test_backtest_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "portfolio-backtester/docs/concepts/backtest-configuration.md",
      "consumer_switch": "internal config_backtest now delegates provider-independent base backtest settings to portfolio-backtester while retaining execution model and data-field checks"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_rolling_windows",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_rolling_windows",
      "status": "complete",
      "owner_commit": "3437f18ed41b5f219a686866917e9bd5be755fa2",
      "internal_commit": "f760ceb1a5b2bb86555eef79621f84f0aa610fa1",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates rolling-window normalization to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_recency",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_recency_settings",
      "status": "complete",
      "owner_commit": "3437f18ed41b5f219a686866917e9bd5be755fa2",
      "internal_commit": "f760ceb1a5b2bb86555eef79621f84f0aa610fa1",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates recency-window normalization to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_final_oos",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_final_oos",
      "status": "complete",
      "owner_commit": "3437f18ed41b5f219a686866917e9bd5be755fa2",
      "internal_commit": "f760ceb1a5b2bb86555eef79621f84f0aa610fa1",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates final-OOS settings normalization to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_artifact_settings",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_artifact_settings",
      "status": "complete",
      "owner_commit": "3437f18ed41b5f219a686866917e9bd5be755fa2",
      "internal_commit": "f760ceb1a5b2bb86555eef79621f84f0aa610fa1",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates artifact-output settings normalization to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_score_postprocess",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_score_postprocess",
      "status": "complete",
      "owner_commit": "41038b1c17ae683618ead694ee27d339f22173f2",
      "internal_commit": "8d4473f20e1cf9b1b67a1d546fd4c8d86eb06d54",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates score postprocess validation to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_signal_settings",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_signal_settings",
      "status": "complete",
      "owner_commit": "8bd760adf7ff3bc9d5c72dfbf320134215590f66",
      "internal_commit": "d9ca3f4c02d619fff7f16b44bdbb75e9f116ab01",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates signal direction validation to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_permutation_test",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_permutation_test",
      "status": "complete",
      "owner_commit": "8bd760adf7ff3bc9d5c72dfbf320134215590f66",
      "internal_commit": "d9ca3f4c02d619fff7f16b44bdbb75e9f116ab01",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates permutation-test validation to alpha-research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_walk_forward_permutation",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_walk_forward_permutation",
      "status": "complete",
      "owner_commit": "8bd760adf7ff3bc9d5c72dfbf320134215590f66",
      "internal_commit": "d9ca3f4c02d619fff7f16b44bdbb75e9f116ab01",
      "test_evidence": "alpha-research tests/test_evaluation_config.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation_config API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "pipeline config_eval now delegates walk-forward permutation settings to alpha-research while retaining pipeline backtest composition"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/stats.py::_normalize_window_months",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/metrics.py::normalize_window_months",
      "status": "complete",
      "owner_commit": "8cafa8ec9749c63e1326e5784a6d25b03ef788df",
      "internal_commit": "8673357cdcd511ca211bd793476c7f311c4e82cd",
      "test_evidence": "alpha-research tests/test_metrics.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation metrics API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "config_eval now imports the alpha-owned rolling-window normalizer and the duplicate pipeline stats helper was removed"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/stats.py::_normalize_bucket_schemes",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/metrics.py::normalize_bucket_schemes",
      "status": "complete",
      "owner_commit": "8cafa8ec9749c63e1326e5784a6d25b03ef788df",
      "internal_commit": "8673357cdcd511ca211bd793476c7f311c4e82cd",
      "test_evidence": "alpha-research tests/test_metrics.py; internal tests/test_pipeline_validation.py and tests/test_migrated_evaluation_config_normalizers.py",
      "doc_evidence": "alpha-research evaluation metrics API; internal docs/internal/alpha-backtesting-boundaries.md",
      "consumer_switch": "config_eval now imports the alpha-owned bucket-IC scheme normalizer and the duplicate pipeline stats helper was removed"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/export_targets.py::_execution_symbol",
      "owner_repo": "quant-execution-engine",
      "target_path": "src/quant_execution_engine/targets.py::normalize_execution_symbol",
      "status": "complete",
      "owner_commit": "608ff9cb1820d43464017763191730abe4257d4e",
      "internal_commit": "4ca785a33bca556bf46b2989b54e02aadaddd6f2",
      "test_evidence": "quant-execution-engine tests/unit/test_targets_contract.py; internal tests/test_export_targets.py, tests/test_cli_liveops.py, and tests/test_migrated_execution_symbol.py",
      "doc_evidence": "internal docs/internal/data-ops-boundary-inventory.md and docs/internal/strategy-pipeline-transition.md; quant-execution-engine target contract",
      "consumer_switch": "internal target export now lazily delegates broker-facing symbol normalization to quant-execution-engine while retaining holdings selection, target serialization, and lineage orchestration"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/owner_ports.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/control_plane/ports.py",
      "status": "complete",
      "owner_commit": "96b1381a0c098c239938400334abb0e6a1b5a752",
      "internal_commit": "f66bda6f066aa9df6adaa6b4a8407c6395561f7a",
      "test_evidence": "strategy-pipeline tests/control_plane/test_owner_ports.py; internal tests/test_migrated_owner_ports.py and pipeline runtime tests",
      "doc_evidence": "strategy-pipeline/docs/control-plane.md; workspace dependency map",
      "consumer_switch": "internal pipeline APIs and runner adapters now import strategy_pipeline.control_plane.ports, the internal owner_ports module was deleted, and the public dependency is locked to the owner commit"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/trial_registry.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/trial_registry.py",
      "status": "complete",
      "owner_commit": "478ac23583784e6c6080b3a14f16c98f4c623aae",
      "internal_commit": "2818bf2421bc4e3a1c453b0669ce8aca966bb58c",
      "test_evidence": "strategy-research tests/test_trial_registry_migration.py; strategy-research full test suite; internal trial registry and CLI tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md; internal docs/internal/data-ops-boundary-inventory.md and docs/internal/strategy-pipeline-transition.md",
      "consumer_switch": "internal research CLI now imports strategy_research.trial_registry, the internal implementation was deleted, and the workspace strategy-research gitlink points to the owner commit"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/_summarize_runs_api.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/summarize_runs/api.py",
      "status": "complete",
      "owner_commit": "0c1c280975353ea52efff491c270c3d062460d57",
      "internal_commit": "7e0047e786785e2431a6fcb2576d22ac362e0803",
      "test_evidence": "strategy-research tests/test_summarize_runs.py and related summarize-runs tests; internal CLI, sweep, tune, release, and migration tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md; internal docs/internal/strategy-pipeline-transition.md",
      "consumer_switch": "internal research CLI and orchestration callers now import strategy_research.summarize_runs.api, and the internal API module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/_summarize_runs_core.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/summarize_runs/core.py",
      "status": "complete",
      "owner_commit": "0c1c280975353ea52efff491c270c3d062460d57",
      "internal_commit": "7e0047e786785e2431a6fcb2576d22ac362e0803",
      "test_evidence": "strategy-research tests/test_summarize_runs.py and provenance tests; internal summarize-runs regression tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md",
      "consumer_switch": "the core summarization implementation is now maintained under strategy_research.summarize_runs.core"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/summarize_runs_args.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/summarize_runs/args.py",
      "status": "complete",
      "owner_commit": "0c1c280975353ea52efff491c270c3d062460d57",
      "internal_commit": "7e0047e786785e2431a6fcb2576d22ac362e0803",
      "test_evidence": "strategy-research summarize-runs CLI tests; internal research CLI tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md",
      "consumer_switch": "the summarize-runs argument parser is now owned by strategy_research.summarize_runs.args"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/summarize_runs_common.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/summarize_runs/common.py",
      "status": "complete",
      "owner_commit": "0c1c280975353ea52efff491c270c3d062460d57",
      "internal_commit": "7e0047e786785e2431a6fcb2576d22ac362e0803",
      "test_evidence": "strategy-research summarize-runs, provenance, and scoring tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md",
      "consumer_switch": "shared run-summary parsing helpers are now imported only through the strategy-research implementation package"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/summarize_runs_provenance.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/summarize_runs/provenance.py",
      "status": "complete",
      "owner_commit": "0c1c280975353ea52efff491c270c3d062460d57",
      "internal_commit": "7e0047e786785e2431a6fcb2576d22ac362e0803",
      "test_evidence": "strategy-research tests/test_summarize_runs_provenance.py; internal provenance regression tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md",
      "consumer_switch": "run input provenance enrichment is now maintained by strategy_research.summarize_runs.provenance"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/summarize_runs_scoring.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/summarize_runs/scoring.py",
      "status": "complete",
      "owner_commit": "0c1c280975353ea52efff491c270c3d062460d57",
      "internal_commit": "7e0047e786785e2431a6fcb2576d22ac362e0803",
      "test_evidence": "strategy-research tests/test_summarize_runs_scoring.py; internal scoring and summarize-runs tests",
      "doc_evidence": "strategy-research/docs/trial-ledger.md",
      "consumer_switch": "run comparison flags and DSR scoring are now maintained by strategy_research.summarize_runs.scoring"
    },
    {
      "source_path": "src/strategy_pipeline_internal/e2_promotion_receipt.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/e2_promotion_receipt.py",
      "status": "complete",
      "owner_commit": "cbdbdd38b7b99199c5fcf3974045a6646e509a36",
      "internal_commit": "d8cd956b53000b578d950795726b98d83283c660",
      "test_evidence": "strategy-pipeline tests/test_e2_promotion_receipt.py; internal tests/test_e2_promotion_receipt.py and tests/test_retired_e2_promotion_receipt.py",
      "doc_evidence": "strategy-pipeline/docs/e2-promotion-receipt.md; workspace docs/runbooks/a-share-long-window-evidence.md",
      "consumer_switch": "internal E2 evidence tests now import strategy_pipeline.e2_promotion_receipt, the internal module was deleted, and the workspace submodule points to the public commit"
    },
    {
      "source_path": "src/strategy_pipeline_internal/research_evidence.py",
      "owner_repo": "research-workspace",
      "target_path": "src/research_contracts/research_run_manifest_writer.py",
      "status": "complete",
      "owner_commit": "6cd93d4372ff19a912732bd0f92ba7d9ceb2b883",
      "internal_commit": "a99764837b2cc2c377715c13ad5efa3452a20da7",
      "test_evidence": "workspace tests/test_research_run_manifest_writer.py and tests/test_research_run_manifest.py; internal tests/test_research_evidence.py and tests/test_retired_research_evidence.py",
      "doc_evidence": "workspace docs/artifact-contracts.yml and docs/contracts.md",
      "consumer_switch": "internal research evidence tests now import research_contracts, the internal writer was deleted, and the workspace contract package owns manifest creation"
    },
    {
      "source_path": "src/strategy_pipeline_internal/research_protocols.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/research_protocols.py",
      "status": "complete",
      "owner_commit": "f529f9d6385f6834a1da62be9c653c9f16a35c8f",
      "internal_commit": "a79fdd5e289910903cbc0288baf489c75e8b8bd6",
      "test_evidence": "alpha-research tests/test_research_protocols.py; internal protocol, AFML, CLI, and retirement tests",
      "doc_evidence": "alpha-research/docs/concepts/research-protocols.md; alpha-research/docs/README.md",
      "consumer_switch": "internal CLI and liveops quality gate now import alpha_research.research_protocols and the internal module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/identity.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/identity.py",
      "status": "complete",
      "owner_commit": "6571c9cc110c98c26e0ac209eac45f3c91fd24d0",
      "internal_commit": "5a4aa78c51ae6910de28f2804130b45b1d8dfd19",
      "test_evidence": "strategy-pipeline tests/control_plane/test_identity.py; internal tests/test_retired_identity.py and CLI/liveops regression tests",
      "doc_evidence": "strategy-pipeline/docs/control-plane.md",
      "consumer_switch": "internal target-source consumers now import strategy_pipeline.identity and the internal module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_policy_snapshot.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/policy_snapshot.py",
      "status": "complete",
      "owner_commit": "5871a404aff95a0d8d1495dba627e0da127ced80",
      "internal_commit": "4e2f5edf9fc1168113fe1b06fd2dd76b745ddef9",
      "test_evidence": "strategy-app tests/test_daily_watch20_policy_snapshot.py; internal tests/test_retired_daily_watch20_policy_snapshot.py and DailyWatch20 pipeline regression tests",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal DailyWatch20 pipeline consumers now import strategy_app.daily_watch20.policy_snapshot and the internal module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/weekly_analysis_artifacts.py",
      "owner_repo": "strategy-research",
      "target_path": "src/strategy_research/weekly_analysis_artifacts.py",
      "status": "complete",
      "owner_commit": "1be76c5fca862404028843faa4cc29fc1578c640",
      "internal_commit": "2ace7c2bba8817e281d2e105ad6171b8ead105c8",
      "test_evidence": "strategy-research tests/test_weekly_analysis_artifacts.py; internal tests/test_retired_weekly_analysis_artifacts.py and weekly-analysis CLI regression tests",
      "doc_evidence": "strategy-research/docs/weekly-analysis-artifacts.md",
      "consumer_switch": "internal weekly-analysis CLI now imports strategy_research.weekly_analysis_artifacts and the internal module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/style_factor_publication.py",
      "owner_repo": "strategy-research",
      "target_path": "src/style_factors/refresh.py",
      "status": "complete",
      "owner_commit": "da296bf5fc4761d44bc1da28e65d600ab5b39590",
      "internal_commit": "6efa17cfb58dc0a67cc07fd3c46540baafb486f1",
      "test_evidence": "strategy-research tests/test_refresh.py; internal tests/test_cli_style_factor_refresh.py and full test suite",
      "doc_evidence": "strategy-research/docs/style-factor-refresh.md; internal docs/internal/data-ops-boundary-inventory.md",
      "consumer_switch": "internal style-factors CLI now imports style_factors.refresh, the internal bridge and its owner tests were deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/allocation_reference.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/allocation_reference.py",
      "status": "complete",
      "owner_commit": "8a6d836110f81678415d7eb02ec8a7e8e156655c",
      "internal_commit": "ba7b4a2b86822506a95f5d67971d92db19bb8637",
      "test_evidence": "portfolio-backtester tests/test_allocation_reference.py; internal tests/test_retired_allocation_reference.py and allocation regression tests",
      "doc_evidence": "portfolio-backtester/docs/reference/allocation-reference.md; portfolio-backtester/docs/README.md",
      "consumer_switch": "internal allocation core now imports portfolio_backtester.allocation_reference, the internal implementation and tests were deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/alloc_rendering.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/allocation_rendering.py",
      "status": "complete",
      "owner_commit": "622c3874200438e6dda80748795f223ede6d3009",
      "internal_commit": "1f5f2c3d594e0f52ed90c43faa5b7070d882f512",
      "test_evidence": "portfolio-backtester tests/test_allocation_rendering.py; internal tests/test_retired_allocation_rendering.py and allocation regression tests",
      "doc_evidence": "portfolio-backtester/docs/reference/allocation-reference.md; portfolio-backtester/docs/README.md",
      "consumer_switch": "internal allocation core now imports portfolio_backtester.allocation_rendering, the internal renderer and formatting test were deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/alloc_selection.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/allocation_selection.py",
      "status": "complete",
      "owner_commit": "81c80ee8054a35f1566b0f5f82756992f805ae2b",
      "internal_commit": "cfe5cf69191cd40a102c5625faa13dd895f25cca",
      "test_evidence": "portfolio-backtester tests/test_allocation_selection.py; internal tests/test_retired_allocation_selection.py and allocation regression tests",
      "doc_evidence": "portfolio-backtester/docs/reference/allocation-reference.md; portfolio-backtester/docs/README.md",
      "consumer_switch": "internal allocation core now delegates pure selection to portfolio_backtester.allocation_selection, the internal selection module was deleted, and holdings payload loading remains in alloc_core"
    },
    {
      "source_path": "src/strategy_pipeline_internal/afml_evidence.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/afml_evidence.py",
      "status": "complete",
      "owner_commit": "5476e6c21219e24eadd44807e54aae7c6c1e1733",
      "internal_commit": "136357b2e0372943c9064d5d2e97b0ac729ddb45",
      "test_evidence": "portfolio-backtester tests/test_afml_evidence.py; internal tests/test_retired_afml_evidence.py and AFML regression tests",
      "doc_evidence": "portfolio-backtester/docs/concepts/afml-sizing-and-risk.md",
      "consumer_switch": "internal CLI and pipeline output now import portfolio_backtester.afml_evidence, and the internal implementation was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/export_targets_envelope.py",
      "owner_repo": "research-workspace",
      "target_path": "src/research_contracts/target_lineage.py",
      "status": "complete",
      "owner_commit": "b017163dc94a3cb51d8d7048703873e2f07cb9a8",
      "internal_commit": "29c07385157a18e5a6a3ccf788688a77825976ac",
      "test_evidence": "workspace tests/test_target_lineage.py; internal tests/test_retired_target_lineage.py and export-targets regression tests",
      "doc_evidence": "workspace docs/contracts.md",
      "consumer_switch": "internal export_targets now imports target lineage helpers from research_contracts, and the internal envelope module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/promotion_sidecar.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/promotion_sidecar.py",
      "status": "complete",
      "owner_commit": "8cdb4d6971ca489088b84a72d6ae472b1f54a9cc",
      "internal_commit": "4d2ea8028456d9a0b19f2bbf4f876d0fe28a7d11",
      "test_evidence": "portfolio-backtester tests/test_promotion_sidecar.py; internal tests/test_retired_promotion_sidecar.py and pipeline regression tests",
      "doc_evidence": "portfolio-backtester/docs/guides/promotion-sidecar.md; portfolio-backtester/docs/README.md",
      "consumer_switch": "internal output orchestration now imports portfolio_backtester.promotion_sidecar, the internal simulation module was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/position_output_artifacts.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/position_outputs.py",
      "status": "complete",
      "owner_commit": "e06e48eb443dad47b492eee084cf3299edcd3024",
      "internal_commit": "4d2ea8028456d9a0b19f2bbf4f876d0fe28a7d11",
      "test_evidence": "portfolio-backtester tests/test_position_outputs.py; internal tests/test_retired_position_output_artifacts.py and pipeline regression tests",
      "doc_evidence": "portfolio-backtester/docs/reference/outputs/positions.md",
      "consumer_switch": "internal output artifacts now import portfolio_backtester.position_outputs, and the internal writer was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/position_postprocess_artifacts.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/position_postprocess_outputs.py",
      "status": "complete",
      "owner_commit": "9357711768d8c58febbc57b9ba1d9877ea1a046a",
      "internal_commit": "a763a0d957a08c517b56f5a5504269d88004b613",
      "test_evidence": "portfolio-backtester tests/test_position_postprocess_outputs.py; internal tests/test_retired_position_postprocess_artifacts.py and pipeline regression tests",
      "doc_evidence": "portfolio-backtester/docs/reference/outputs/positions.md",
      "consumer_switch": "internal output artifacts now import portfolio_backtester.position_postprocess_outputs, and the internal writer was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_context.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/control_plane/output_context.py",
      "status": "complete",
      "owner_commit": "02f8b789ed66eadf664365d38358ae298bb2dab4",
      "internal_commit": "cc0824e8b5f991dbb7781b8637414d69ff956409",
      "test_evidence": "strategy-pipeline tests/control_plane/test_output_context.py; internal tests/test_retired_output_context.py and pipeline regression tests",
      "doc_evidence": "strategy-pipeline/docs/control-plane.md",
      "consumer_switch": "internal output orchestration now imports strategy_pipeline.control_plane.output_context, and the internal context implementation was deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_news_heat_export.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/news_heat_export.py",
      "status": "complete",
      "owner_commit": "60b87f454552311e874f837471d2e9b38300fc3e",
      "internal_commit": "442eb4b6c5dcbc341991641530cc1eb66348a93c",
      "test_evidence": "strategy-app tests/test_daily_watch20_news_heat_export.py; internal tests/test_daily_watch20_news_heat_export_owner.py and test_retired_daily_watch20_news_heat_export.py; import boundary check",
      "doc_evidence": "strategy-app/docs/daily-watch20-news-heat-export.md; internal docs/outputs.md",
      "consumer_switch": "internal watchlist20 CLI now imports strategy_app.daily_watch20.news_heat_export"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_minute.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/minute_features.py",
      "status": "complete",
      "owner_commit": "c9a4273c6befaad50abe114cc529866e80c44469",
      "internal_commit": "f9e07e2427d677c535d998f1f41d9c9451fecbf1",
      "test_evidence": "strategy-app tests/test_daily_watch20_minute_features.py; internal tests/test_daily_watch20_minute.py and test_retired_daily_watch20_minute.py; import boundary check",
      "doc_evidence": "strategy-app/docs/application-catalog.md; internal docs/cli.md",
      "consumer_switch": "internal pipeline, research scripts, and market-shadow runtime metadata now import strategy_app.daily_watch20.minute_features"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_policy.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/daily_watch20_policy.py",
      "status": "complete",
      "owner_commit": "7daf1ce50aaa804ffa6491dbd301bdf0f0cd3af4",
      "internal_commit": "f456533f5b3600e182ebac2e752bbd8ed3e27ada",
      "test_evidence": "strategy-app tests/test_daily_watch20_policy.py; internal tests/test_daily_watch20_strategy_policy.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal DailyWatch20 consumers now import the policy contract from strategy_app"
    },
    {
      "source_path": "src/strategy_pipeline_internal/policy_canonical.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/policy_canonical.py",
      "status": "complete",
      "owner_commit": "7daf1ce50aaa804ffa6491dbd301bdf0f0cd3af4",
      "internal_commit": "f456533f5b3600e182ebac2e752bbd8ed3e27ada",
      "test_evidence": "strategy-app tests/test_daily_watch20_policy.py; internal tests/test_daily_watch20_strategy_policy.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "policy canonicalization now resolves within strategy_app.daily_watch20"
    },
    {
      "source_path": "src/strategy_pipeline_internal/policy_primitives.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/policy_primitives.py",
      "status": "complete",
      "owner_commit": "7daf1ce50aaa804ffa6491dbd301bdf0f0cd3af4",
      "internal_commit": "f456533f5b3600e182ebac2e752bbd8ed3e27ada",
      "test_evidence": "strategy-app tests/test_daily_watch20_policy.py; internal tests/test_daily_watch20_strategy_policy.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "policy primitives now resolve within strategy_app.daily_watch20"
    },
    {
      "source_path": "src/strategy_pipeline_internal/policy_validation_model.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/policy_validation_model.py",
      "status": "complete",
      "owner_commit": "7daf1ce50aaa804ffa6491dbd301bdf0f0cd3af4",
      "internal_commit": "f456533f5b3600e182ebac2e752bbd8ed3e27ada",
      "test_evidence": "strategy-app tests/test_daily_watch20_policy.py; internal tests/test_daily_watch20_strategy_policy.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "model and feature validation now resolves within strategy_app.daily_watch20"
    },
    {
      "source_path": "src/strategy_pipeline_internal/policy_validation_strategy.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/policy_validation_strategy.py",
      "status": "complete",
      "owner_commit": "7daf1ce50aaa804ffa6491dbd301bdf0f0cd3af4",
      "internal_commit": "f456533f5b3600e182ebac2e752bbd8ed3e27ada",
      "test_evidence": "strategy-app tests/test_daily_watch20_policy.py; internal tests/test_daily_watch20_strategy_policy.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "strategy validation now resolves within strategy_app.daily_watch20"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liquidity_proxy.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/liquidity_proxy.py",
      "status": "complete",
      "owner_commit": "6eefb9668d10c11f0098b44bf578b462db218299",
      "internal_commit": "cd25c8985f3e52486f11d7244aaa06fcc06dd8e5",
      "test_evidence": "portfolio-backtester tests/test_liquidity_proxy.py; internal tests/test_retired_liquidity_proxy.py; internal tests/test_pipeline_memory_path.py",
      "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
      "consumer_switch": "internal panel loading now imports liquidity proxy helpers directly from portfolio_backtester"
    },
    {
      "source_path": "src/strategy_pipeline_internal/contracts/backtest.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/backtest_contracts.py",
      "status": "complete",
      "owner_commit": "7a7338629e19f4d8639cd13dcb31765a22acd2b3",
      "internal_commit": "c50b101b9c200914404a080eed77f47df6116891",
      "test_evidence": "portfolio-backtester tests/test_backtest_output_contracts.py; internal tests/test_backtest_contracts.py",
      "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
      "consumer_switch": "internal compatibility exports now delegate to portfolio_backtester.backtest_contracts"
    },
    {
      "source_path": "src/strategy_pipeline_internal/contracts/signals.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/signal_artifact.py",
      "status": "complete",
      "owner_commit": "e2b71e6871ae1b0f9ce16511a9dca1244a23415a",
      "internal_commit": "9d895b411cc4425878ab896ce7efbacd8310ae9f",
      "test_evidence": "alpha-research tests/test_signal_artifact.py; internal tests/test_signal_contracts.py; internal tests/test_research_abstractions.py; internal tests/test_external_signals.py",
      "doc_evidence": "alpha-research/docs/reference/signal-artifacts.md",
      "consumer_switch": "internal compatibility exports now delegate to alpha_research.signal_artifact"
    },
    {
      "source_path": "src/strategy_pipeline_internal/contracts/rebalance.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/rebalance.py",
      "status": "complete",
      "owner_commit": "7a7338629e19f4d8639cd13dcb31765a22acd2b3",
      "internal_commit": "df444be",
      "test_evidence": "portfolio-backtester tests/test_rebalance.py; internal tests/test_rebalance_contracts.py",
      "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
      "consumer_switch": "internal compatibility exports now delegate to portfolio_backtester.rebalance"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_style_replica_pipeline_core.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/style_replica/_style_replica_pipeline_core.py",
      "status": "complete",
      "owner_commit": "a30fe5af462c9baeabcb499eb5ae183a1873c419",
      "internal_commit": "3a4191213dd7f1645844076d628658aa66088178",
      "test_evidence": "strategy-app tests/test_style_replica_pipeline.py; internal tests/test_retired_style_replica_pipeline.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal StyleReplica pipeline tests now import the strategy-app owner"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_style_replica_pipeline_output.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/style_replica/_style_replica_pipeline_output.py",
      "status": "complete",
      "owner_commit": "a30fe5af462c9baeabcb499eb5ae183a1873c419",
      "internal_commit": "3a4191213dd7f1645844076d628658aa66088178",
      "test_evidence": "strategy-app tests/test_style_replica_output_ownership.py; internal tests/test_retired_style_replica_pipeline.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal output ownership tests now import the strategy-app owner"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_style_replica_pipeline_owner_api.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/style_replica/_style_replica_pipeline_owner_api.py",
      "status": "complete",
      "owner_commit": "a30fe5af462c9baeabcb499eb5ae183a1873c419",
      "internal_commit": "3a4191213dd7f1645844076d628658aa66088178",
      "test_evidence": "strategy-app tests/test_style_replica_data_boundary.py; internal tests/test_style_replica_data_boundary.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal data-boundary tests now import the strategy-app owner"
    },
    {
      "source_path": "src/strategy_pipeline_internal/style_replica_pipeline.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/style_replica/style_replica_pipeline.py",
      "status": "complete",
      "owner_commit": "a30fe5af462c9baeabcb499eb5ae183a1873c419",
      "internal_commit": "3a4191213dd7f1645844076d628658aa66088178",
      "test_evidence": "strategy-app tests/test_style_replica_pipeline.py; internal tests/test_style_replica_ownership.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal StyleReplica ownership tests now import the strategy-app owner"
    },
    {
      "source_path": "src/strategy_pipeline_internal/d11_h5_shadow.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/d11_h5_shadow.py",
      "status": "complete",
      "owner_commit": "b59a881da300a06a65d8420b626e0306f4971fdd",
      "internal_commit": "8414f8a412b2d96fdb0fc48c062b7fb3e398dda7",
      "test_evidence": "strategy-app tests/test_d11_h5_shadow_pipeline.py; internal tests/test_retired_d11_h5_shadow.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal D11-H5 CLI registration now imports the strategy-app owner"
    },
    {
      "source_path": "src/strategy_pipeline_internal/afml_lineage.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/control_plane/afml_lineage.py",
      "status": "complete",
      "owner_commit": "e15d463cde0512e5cbf9cc24b95f09f6c9c898ea",
      "internal_commit": "e4f75b92c031e4e634d40f8581e614b0cf572633",
      "test_evidence": "strategy-pipeline tests/control_plane/test_afml_lineage.py; internal tests/test_retired_afml_lineage.py",
      "doc_evidence": "strategy-pipeline/docs/control-plane.md",
      "consumer_switch": "internal AFML lineage tests now import the public control-plane owner"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/contracts.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/train_eval_contracts.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "7513bd72c9ac8162670fabb0439c7d66062f979a",
      "test_evidence": "alpha-research train-eval contract tests; internal tests/test_retired_train_eval_contract_facade.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal train-eval contract tests now import alpha_research.train_eval_contracts"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/eval_benchmark.py",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/benchmarking.py",
      "status": "complete",
      "owner_commit": "7a7338629e19f4d8639cd13dcb31765a22acd2b3",
      "internal_commit": "eaa14daf88d4d9c30de98d0b74f839d94102a08c",
      "test_evidence": "portfolio-backtester benchmarking tests; internal tests/test_retired_owner_facades.py",
      "doc_evidence": "portfolio-backtester/docs/reference/public-api.md",
      "consumer_switch": "internal benchmark tests now import portfolio_backtester.benchmarking"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/train_eval_request_builder.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/train_eval_request_builder.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "eaa14daf88d4d9c30de98d0b74f839d94102a08c",
      "test_evidence": "alpha-research train-eval request tests; internal tests/test_retired_owner_facades.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal train-eval request consumers now import alpha_research.train_eval_request_builder"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/train_eval_result.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/train_eval_result.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "eaa14daf88d4d9c30de98d0b74f839d94102a08c",
      "test_evidence": "alpha-research train-eval result tests; internal tests/test_retired_owner_facades.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal train-eval result consumers now import alpha_research.train_eval_result"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/dataset_sampling.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/dataset_sampling.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "1b6d54b1e29867793f2a0b56f3b0a8d1a578f46c",
      "test_evidence": "alpha-research dataset sampling tests; internal tests/test_retired_dataset_sampling_facade.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal dataset sampling consumers now import alpha_research.dataset_sampling"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/dates.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/date_slices.py; src/alpha_research/walk_forward_windows.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "3e1e1660dd0a8362d5ae45f71610ffb2aa049a11",
      "test_evidence": "alpha-research date and walk-forward tests; internal tests/test_retired_date_facade.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal runtime and date tests now import alpha_research date owners"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/freshness_overlay.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/freshness_overlay.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "29cf2f2d3a98549ce05c62c6d82a7de9b839224c",
      "test_evidence": "alpha-research freshness overlay tests; internal tests/test_retired_freshness_overlay_facade.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal freshness overlay consumers now import alpha_research.freshness_overlay"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_publication_tier.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/publication_tier.py",
      "status": "complete",
      "owner_commit": "2dac0322ab60baa0dbcf59cf46c8ed51d59948fd",
      "internal_commit": "3d7ac1d6535e5181dbea91b2bd8be45670d81330",
      "test_evidence": "strategy-app tests/test_publication_tier.py; internal tests/test_retired_publication_tier.py",
      "doc_evidence": "strategy-app/docs/application-catalog.md",
      "consumer_switch": "internal DailyWatch20 pipeline now imports strategy_app.daily_watch20.publication_tier"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/promotion_gate.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/promotion_gate.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "37151c5a9e46098137fa94d0364e18aaf56acc0a",
      "test_evidence": "alpha-research promotion gate tests; internal tests/test_retired_promotion_gate_facades.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal promotion gate consumers now resolve through alpha_research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/promotion_gate_thresholds.py",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/promotion_gate_thresholds.py",
      "status": "complete",
      "owner_commit": "6dd0de84e3639d233e6b71a8820b198b117cc22f",
      "internal_commit": "37151c5a9e46098137fa94d0364e18aaf56acc0a",
      "test_evidence": "alpha-research promotion gate threshold tests; internal tests/test_retired_promotion_gate_facades.py",
      "doc_evidence": "alpha-research/docs/README.md",
      "consumer_switch": "internal promotion threshold consumers now resolve through alpha_research"
    },
    {
      "source_path": "src/strategy_pipeline_internal/_hotsector_deepseek_v4_month_backtest_api.py; src/strategy_pipeline_internal/_hotsector_deepseek_v4_month_backtest_core.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_deepseek_v4_month_backtest_api.py; src/strategy_app/hotsector/hotsector_deepseek_v4_month_backtest_core.py",
      "status": "complete",
      "owner_commit": "811bd97664e1b6e76cabb0774ce01447cfb5cc46",
      "internal_commit": "74179c2225256d29e539b05e549219275b170313",
      "test_evidence": "strategy-app V4-month backtest tests: 2 passed; internal V4-month backtest validation and regression tests: 24 passed",
      "doc_evidence": "strategy-app/docs/hotsector-deepseek-v4-month-backtest.md",
      "consumer_switch": "internal V4-month backtest modules now provide compatibility imports and all backtest callers use strategy-app owner modules"
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_ai_shadow.py; src/strategy_pipeline_internal/hotsector_ai_shadow_observation.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/hotsector/hotsector_ai_shadow.py; src/strategy_app/hotsector/hotsector_ai_shadow_observation.py",
      "status": "complete",
      "owner_commit": "a6c2a813b8b5fbd75117b1fc2c1c592086254004",
      "internal_commit": "64663169e39e8178f990562beca991081ea618a2",
      "test_evidence": "strategy-app tests/test_hotsector_ai_shadow.py: 17 passed; internal compatibility and owner-import regression tests",
      "doc_evidence": "strategy-app/docs/hotsector-ai-shadow.md",
      "consumer_switch": "internal Hotsector AI shadow modules and research CLI now delegate to strategy-app owner modules"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_long_horizon_buffer_resources.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/daily_watch20_long_horizon_buffer_resources.py",
      "status": "complete",
      "owner_commit": "d964c7f097624b615198cf5d8fe2ce007a2f3d89",
      "internal_commit": "da98c64c350c22e310119b3e57ffd9187c7a59d1",
      "test_evidence": "strategy-app tests/test_daily_watch20_long_horizon_buffer_resources.py: 3 passed; internal tests/test_daily_watch20_long_horizon_buffer.py: 12 passed",
      "doc_evidence": "strategy-app/docs/daily-watch20-long-horizon-buffer-resources.md",
      "consumer_switch": "internal long-horizon IO and tests now import the strategy-app resource planner, while the historical module remains a compatibility wrapper"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_ablation_publish.py; src/strategy_pipeline_internal/daily_watch20_ablation_postprocess.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/daily_watch20_ablation_publish.py; src/strategy_app/daily_watch20/daily_watch20_ablation_postprocess.py",
      "status": "complete",
      "owner_commit": "d990f2f765ad3f21c51dc6f4a0440ac7a943f6f1",
      "internal_commit": "1b8f745d2cddfc9c825569377d26b91149cf5ddb",
      "test_evidence": "strategy-app and internal DailyWatch20 ablation publication regression tests: 19 passed",
      "doc_evidence": "strategy-app/docs/daily-watch20-ablation-publication.md",
      "consumer_switch": "internal ablation API, publisher, postprocessor, and regression tests now resolve through strategy-app owner modules"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_market_shadow_publish.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/daily_watch20_market_shadow_publish.py",
      "status": "complete",
      "owner_commit": "c927767382e575aa257fd2885db772bb3f421de2",
      "internal_commit": "cc7efcd0b1ac825339c6be31b6567be47eea268f",
      "test_evidence": "strategy-app and internal DailyWatch20 market shadow publication tests: 6 passed",
      "doc_evidence": "strategy-app/docs/daily-watch20-market-shadow-publication.md",
      "consumer_switch": "internal candidate OOS orchestration and publication tests now use the strategy-app owner publisher"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_long_horizon_buffer_io.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/daily_watch20_long_horizon_buffer_io.py",
      "status": "complete",
      "owner_commit": "a5e29a1",
      "internal_commit": "85f03abafa164ee3a8e9431706b4caefeef76f1f",
      "test_evidence": "strategy-app tests/test_daily_watch20_long_horizon_buffer_io.py: 2 passed; internal tests/test_daily_watch20_long_horizon_buffer.py: 12 passed",
      "doc_evidence": "strategy-app/docs/daily-watch20-long-horizon-buffer-io.md; strategy-app PR #98",
      "consumer_switch": "internal long-horizon runner and regression tests now import the strategy-app IO owner, while the historical module remains a compatibility wrapper"
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_pipeline.py",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/daily_watch20/pipeline.py",
      "status": "complete",
      "owner_commit": "6f9653f",
      "internal_commit": "458574545455663765b80744e501c6aa21db8e7f",
      "test_evidence": "strategy-app tests/test_daily_watch20_pipeline.py: 2 passed; internal DailyWatch20 pipeline, lifecycle, policy, publication safety, ablation, market shadow, and fundamental shadow tests: 161 passed",
      "doc_evidence": "strategy-app/docs/daily-watch20-pipeline.md; strategy-app PR #99",
      "consumer_switch": "internal research scripts, ablation APIs, and DailyWatch20 regression tests now import the strategy-app pipeline owner, while the historical module remains a compatibility facade"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/eval.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/eval.py",
      "status": "complete",
      "owner_commit": "d422145",
      "internal_commit": "bc5d8093cfe75e25d0ae7c6e046bc6b4f09acf87",
      "test_evidence": "strategy-pipeline tests/test_pipeline_eval.py: 1 passed; internal execution-calendar, namespace, position-postprocess, and pipeline-runtime tests: 125 passed",
      "doc_evidence": "strategy-pipeline/docs/evaluation.md; strategy-pipeline PR #11",
      "consumer_switch": "internal runner, final-OOS stage, and evaluation regression consumers now import the public strategy-pipeline evaluation owner, while the historical module remains a narrow compatibility facade"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_summary_sections.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/output_summary_sections.py",
      "status": "complete",
      "owner_commit": "d7fb15c3527a752d6c80f0daae712f9e45f2a652",
      "internal_commit": "5b3adcdaab8066233cf8733a6d48e0843de50389",
      "test_evidence": "strategy-pipeline tests/test_pipeline_output_summary_sections.py and test_pipeline_eval.py: 2 passed; internal pipeline-runtime, output-summary-metadata, and namespace tests: 120 passed",
      "doc_evidence": "strategy-pipeline/docs/output-summary.md; strategy-pipeline PR #12",
      "consumer_switch": "internal output persistence now imports the public run-summary assembler, while the historical module remains a narrow compatibility facade"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_artifacts.py; src/strategy_pipeline_internal/pipeline/diagnostic_artifacts.py; src/strategy_pipeline_internal/pipeline/support.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/output_artifacts.py; src/strategy_pipeline/pipeline/diagnostic_artifacts.py; src/strategy_pipeline/pipeline/support.py",
      "status": "complete",
      "owner_commit": "70e0ff62bbb28b4c4b42286867e874e6d7dd779d",
      "internal_commit": "22652ea93b01d3541fd47c668020047f8edfcdbf",
      "test_evidence": "strategy-pipeline output-artifacts, output-summary, and evaluation tests: 8 passed; internal output-artifacts, diagnostics, runtime, and namespace tests: 129 passed",
      "doc_evidence": "strategy-pipeline/docs/output-artifacts.md; strategy-pipeline PR #13",
      "consumer_switch": "internal output persistence now imports public artifact writers, diagnostic tests import the public diagnostic owner, and the duplicated internal implementations were deleted"
    },
    {
      "source_path": "src/strategy_pipeline_internal/legacy_rqdata_runtime.py::normalize_legacy_symbol_for_market",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/symbols.py::normalize_historical_hk_symbol",
      "status": "complete",
      "owner_commit": "f8506e996a9076e14d3031a378554e0ea262581e",
      "internal_commit": "8dcf457f9bb442c2b517effbcedbcd35f7143bff",
      "test_evidence": "market-data-platform tests/test_market_specs.py; internal tests/test_historical_hk_symbol_owner.py",
      "consumer_switch": "legacy_rqdata_runtime.py was deleted in internal PR #143 after its remaining callers were removed"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/quality.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/quality.py",
      "status": "complete",
      "owner_commit": "5416e2f20b4023ef7c2ed619690832ca5829ec67",
      "internal_commit": "29bf6675c11d10a23bf196a3ac71a63fc197b683",
      "test_evidence": "strategy-pipeline quality, artifact, summary, and evaluation tests: 10 passed; internal quality, protocol, export-target, snapshot, validation, and namespace tests: passed",
      "doc_evidence": "strategy-pipeline/docs/quality-gates.md; strategy-pipeline PR #14",
      "consumer_switch": "internal runner, preflight, external-signal, and liveops consumers now import the public quality-gate owner through a compatibility facade"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/runtime.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/runtime.py",
      "status": "complete",
      "owner_commit": "93207ce0e36ab9469d839ac56d3080bf1cf99d6a",
      "internal_commit": "e670f1f6e2141f14c2a5d4e0d7604c62424bc07f",
      "test_evidence": "strategy-pipeline runtime, quality, artifact, summary, and evaluation tests: 12 passed; internal runtime, quality, validation, and namespace tests passed",
      "doc_evidence": "strategy-pipeline/docs/runtime-helpers.md; strategy-pipeline PR #15",
      "consumer_switch": "internal context builder, runner, and config consumers now import public runtime helpers through a compatibility facade"
    },
    {
      "source_path": "src/strategy_pipeline_internal/data_interface.py",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/research_data_interface.py",
      "status": "complete",
      "owner_commit": "fdda91891e371538588e5c2facb087a2ee546546",
      "internal_commit": "d3f45b2836e2b47f71db68f7d8e6a2c7241128a1",
      "test_evidence": "market-data-platform tests/test_research_data_interface.py: 8 passed; internal data-interface, TuShare interface, provider-fundamentals, and file-build tests: 18 passed",
      "doc_evidence": "market-data-platform/docs/research-data-interface.md; market-data-platform PR #114",
      "consumer_switch": "internal DataInterface now subclasses the market-data-platform adapter and preserves the historical import and test seams"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/output.py",
      "status": "complete",
      "owner_commit": "157ea08897893d4bfc0bcb0fe88563594073f04c",
      "internal_commit": "f282b3d68c0023e814eff75085f6d86e33a8a4a2",
      "test_evidence": "strategy-pipeline tests/test_pipeline_output.py: 2 passed; internal quality, runtime, validation, external-signal, snapshot, and export-target tests: 63 passed",
      "doc_evidence": "strategy-pipeline/docs/output-orchestration.md; strategy-pipeline PR #18",
      "consumer_switch": "internal output persistence now delegates lifecycle ordering to the public orchestrator and injects only private evidence, summary, and metadata callbacks"
    },
    {
      "source_path": "src/strategy_pipeline_internal/cli/evidence.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/cli_evidence.py",
      "status": "complete",
      "owner_commit": "48b5a97b711a60a943c6c2ace7c0dbd1a2a75aa8",
      "internal_commit": "a7927998b0cbef4fc1e00b89038c457195ad0a60",
      "test_evidence": "strategy-pipeline tests/test_cli_evidence_protocol.py; internal CLI, protocol, namespace, and strategy-pipeline regression tests passed",
      "doc_evidence": "strategy-pipeline/docs/evidence-protocol-cli.md; strategy-pipeline PR #19",
      "consumer_switch": "internal AFML evidence CLI now delegates argument handling and execution to the public command handler"
    },
    {
      "source_path": "src/strategy_pipeline_internal/cli/protocol.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/cli_protocol.py",
      "status": "complete",
      "owner_commit": "48b5a97b711a60a943c6c2ace7c0dbd1a2a75aa8",
      "internal_commit": "a7927998b0cbef4fc1e00b89038c457195ad0a60",
      "test_evidence": "strategy-pipeline tests/test_cli_evidence_protocol.py; internal CLI, protocol, namespace, and strategy-pipeline regression tests passed",
      "doc_evidence": "strategy-pipeline/docs/evidence-protocol-cli.md; strategy-pipeline PR #19",
      "consumer_switch": "internal research-protocol CLI now delegates manifest initialization and evaluation to the public command handler"
    },
    {
      "source_path": "src/strategy_pipeline_internal/cli/common.py::format_bytes, render_pct_bar, coerce_float, append_arg, append_repeat_args, append_bool_switch, append_passthrough",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/cli_helpers.py",
      "status": "complete",
      "owner_commit": "060557b14b168b62f72fb4fdc63835e2df86e5bf",
      "internal_commit": "122837c0209e127564578fad83bee6fb08b30b98",
      "test_evidence": "strategy-pipeline tests/test_cli_helpers.py: 2 passed; internal CLI core, entrypoint, research, liveops, style-factor, and namespace regression tests passed",
      "doc_evidence": "strategy-pipeline/docs/cli-helpers.md; strategy-pipeline PR #20",
      "consumer_switch": "internal CLI common helpers now import the public implementations, while quota formatting and private config loading remain internal"
    },
    {
      "source_path": "src/strategy_pipeline_internal/cli/common.py::augment_quota_entry, augment_quota_payload, format_quota_entry, format_quota_pretty",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/quota_rendering.py",
      "status": "complete",
      "owner_commit": "8591073962c1ceb7441d5fa85bed4d5e970f41b2",
      "internal_commit": "ef2b353e6a13879d474b11ba456c04f3e36519b0",
      "test_evidence": "market-data-platform tests/test_quota_rendering.py: 2 passed; internal CLI core, entrypoint, research, liveops, style-factor, and namespace regression tests passed",
      "doc_evidence": "market-data-platform/docs/quota-rendering.md; market-data-platform PR #115",
      "consumer_switch": "internal quota display helpers now import the market-data-platform owner implementation"
    },
    {
      "source_path": "src/strategy_pipeline_internal/commands/run_grid_common.py::_resolve_output_path, _safe_run_name, _parse_date_list, _resolve_rebalance_dates",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/grid_support.py",
      "status": "complete",
      "owner_commit": "29a08d639c3b12bb5f3d966644a44a150cbb167e",
      "internal_commit": "fd1d70319d08951f145dfc48793ec1f3c414a057",
      "test_evidence": "portfolio-backtester tests/test_grid_support.py: 3 passed; internal CLI research, CLI core, test-impact, and pipeline E2E tests passed",
      "doc_evidence": "portfolio-backtester/docs/grid-support.md; portfolio-backtester PR #77",
      "consumer_switch": "internal grid command now delegates path, run-name, date-list, and rebalance-date parsing to portfolio-backtester"
    },
    {
      "source_path": "src/strategy_pipeline_internal/commands/run_grid_common.py::_init_row, _write_grid_rows",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/grid_support.py",
      "status": "complete",
      "owner_commit": "38d113782fc23b2bf3a8391f4a05e5114ebc2694",
      "internal_commit": "0dc8015ead94a0a125d7c417ba183d3ba82d0baa",
      "test_evidence": "portfolio-backtester tests/test_grid_support.py: 4 passed; internal CLI research, CLI core, test-impact, and pipeline E2E tests passed",
      "doc_evidence": "portfolio-backtester/docs/grid-support.md; portfolio-backtester PR #78",
      "consumer_switch": "internal grid common module now delegates result-row initialization and stable CSV writing to portfolio-backtester"
    },
    {
      "source_path": "src/strategy_pipeline_internal/config_utils.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/config.py",
      "status": "complete",
      "owner_commit": "25843f243900da63dff74725dd2e8dd4a894eeb8",
      "internal_commit": "e28541810a31dbea93b3289c77507ab53f80bce1",
      "test_evidence": "strategy-pipeline tests/test_config.py: 5 passed; internal configuration, CLI, linear sweep, external signal, and data-interface tests: 49 passed",
      "doc_evidence": "strategy-pipeline/docs/configuration.md; strategy-pipeline PR #21",
      "consumer_switch": "internal config_utils now delegates generic YAML loading, extends resolution, aliases, and normalization to strategy-pipeline, retaining only private path discovery and workspace preset routing"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_summary_metadata.py::write_run_metadata",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/output.py::write_run_metadata",
      "status": "complete",
      "owner_commit": "330d597827d66f9aa4d2064592164064f37b3353; 7c0a02794640880c3178814e8a018b182c6a500e; dfd76252b1d3ca7a74272d361edd99ebcdb1249e; b4add3b3d49906b3416f819359a15375c6616dc6; a5c3bb25d9387056113f6e289538e32ecdeefa8f; 85280accc7c4ea7066431089e18f134cd7d7b829; d6b3c8a9ca8737ef7febe0fa078f711771b49625",
      "internal_commit": "f128215e45087b9ed8e57f237232b993c0b676ec",
      "migration_pr": "strategy-pipeline PR #22; strategy-research PR #94; market-data-platform PR #117, #118, #119, #120, #121, #122; strategy-pipeline-internal PR #271, #272, #273, #274, #275, #276, #277, #278, #279, #281",
      "test_evidence": "strategy-pipeline clean-room control-plane tests: 21 passed; strategy-research tests/test_run_metadata.py: 2 passed; market-data-platform contract matching and loader tests: 4 passed, path-kind tests: 2 passed, configured-root tests: 2 passed, path tests: 14 passed, describe-input-path test: 1 passed; internal output metadata, provenance, contract matching, input path, manifest, loader, migrated path-kind, configured-root, and input-description regression tests passed",
      "doc_evidence": "strategy-pipeline/docs/pipeline-overview.md; strategy-research/docs/run-artifacts.md; market-data-platform/docs/contracts.md",
      "consumer_switch": "internal generic metadata writing, provenance aggregation, current-contract path handling, and input path description now delegate to strategy-pipeline, strategy-research, and market-data-platform"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output.py::_maybe_generate_afml_evidence",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/afml_evidence.py::maybe_generate_run_afml_evidence",
      "status": "complete",
      "owner_commit": "d6cde0bc4aa8770dab18d38df4dfd80ac852e808",
      "internal_commit": "1664025fd137decf6141bdb609310907edea18e2",
      "migration_pr": "portfolio-backtester PR #79; strategy-pipeline-internal PR #282",
      "test_evidence": "portfolio-backtester tests/test_afml_evidence.py: 3 passed; internal migrated AFML output-hook test passed",
      "doc_evidence": "portfolio-backtester/docs/concepts/afml-sizing-and-risk.md",
      "consumer_switch": "internal pipeline output now passes portfolio-backtester.maybe_generate_run_afml_evidence directly to the public output writer"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_orchestration.py::_promotion_sidecar_config",
      "owner_repo": "portfolio-backtester",
      "target_path": "src/portfolio_backtester/promotion_sidecar.py::promotion_sidecar_config_from_pipeline_config",
      "status": "complete",
      "owner_commit": "48944e721827fb0aa0ae6dbbb65f6ffbba052fe1",
      "internal_commit": "0cb1ea711d79460acbbd2ac01ea775209ddbfaa6",
      "migration_pr": "portfolio-backtester PR #80; strategy-pipeline-internal PR #283",
      "test_evidence": "portfolio-backtester tests/test_promotion_sidecar.py: 2 passed; internal migrated promotion configuration test passed",
      "doc_evidence": "portfolio-backtester/src/portfolio_backtester/promotion_sidecar.py API docstring",
      "consumer_switch": "internal output orchestration now calls portfolio_backtester.promotion_sidecar_config_from_pipeline_config directly"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_orchestration.py::_build_diagnostic_extras",
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/pipeline/output_diagnostics.py::build_output_diagnostic_extras",
      "status": "complete",
      "owner_commit": "442f38d08881d15aac130b5d1de01dc1d5bac9cd",
      "internal_commit": "3f45f8dbb3bb563afd9134be079f14c5665e2b3e",
      "migration_pr": "strategy-app PR #100; strategy-pipeline-internal PR #284",
      "test_evidence": "strategy-app tests/test_output_diagnostics.py passed; internal migrated output-diagnostics test passed with locked dependencies",
      "doc_evidence": "strategy-app/docs/output-diagnostics.md",
      "consumer_switch": "internal output orchestration now delegates cross-owner diagnostic composition to strategy-app"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/export_targets.py::_output_path",
      "owner_repo": "quant-execution-engine",
      "target_path": "src/quant_execution_engine/targets.py::resolve_target_output_path",
      "status": "complete",
      "owner_commit": "316f083f4903f9af7b5e4ff82de5b2f15253271f",
      "internal_commit": "902499d53fa9823db3a407cf2a91409649e47d53",
      "migration_pr": "quant-execution-engine PR #26; strategy-pipeline-internal PR #285",
      "test_evidence": "quant-execution-engine target contract tests; internal tests/test_migrated_target_output_path.py",
      "doc_evidence": "quant-execution-engine target contract documentation",
      "consumer_switch": "internal liveops target export now delegates target and lineage output path resolution to quant-execution-engine"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/export_targets.py::_apply_target_pruning",
      "owner_repo": "quant-execution-engine",
      "target_path": "src/quant_execution_engine/targets.py::prune_target_weights",
      "status": "complete",
      "owner_commit": "37a41b9a800625ef90a8b7866d8843d407b785ec",
      "internal_commit": "d200bfd5e1a1c12a30da0306bcdd88679d3e07ff",
      "migration_pr": "quant-execution-engine PR #27; strategy-pipeline-internal PR #286",
      "test_evidence": "quant-execution-engine tests/unit/test_targets_contract.py: 12 passed; internal tests/test_migrated_target_output_path.py; export-targets integration blocked by historical public pipeline compatibility path",
      "doc_evidence": "quant-execution-engine targets API docstring",
      "consumer_switch": "internal export-targets keeps only the pandas and CLI adapter while execution-target pruning is owned by quant-execution-engine"
    }
  ],
  "partial_code_migrations": [],
  "retired_internal_facades": [
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/stats.py",
      "status": "complete",
      "internal_commit": "3f8e435dbfdf062fe99505173dcaf8e46df55c3b",
      "test_evidence": "internal tests/test_migrated_evaluation_config_normalizers.py; internal final-OOS, pipeline validation, and leakage-warning tests",
      "rationale": "The module only re-exported alpha-research recency diagnostics. Its remaining consumer now imports the owner API directly, while data-field expansion and purge warnings have already moved to their respective owners."
    },
    {
      "source_path": "src/strategy_pipeline_internal/commands/tune/__init__.py",
      "status": "complete",
      "internal_commit": "52ad0e5b7c35b368ac52e2b22b4d245a6f56f508",
      "test_evidence": "internal tests/test_retired_tune_package_facade.py; internal tuning and research CLI tests",
      "rationale": "The package file only re-exported parser, report, and spec helpers. The CLI and runner now import those implementation modules directly, while the tune submodule paths remain available."
    },
    {
      "source_path": "src/strategy_pipeline_internal/__init__.py",
      "status": "complete",
      "internal_commit": "80a53406128b0cf0e817cb7cb43dbee5c88ea199",
      "test_evidence": "internal tests/test_retired_root_liveops_package_facades.py; namespace and import boundary tests",
      "rationale": "The root package file contained only a module docstring. Python namespace-package imports preserve submodule access without package initialization logic."
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops/__init__.py",
      "status": "complete",
      "internal_commit": "80a53406128b0cf0e817cb7cb43dbee5c88ea199",
      "test_evidence": "internal tests/test_retired_root_liveops_package_facades.py; liveops CLI, target export, holdings, and snapshot tests",
      "rationale": "The package file only re-exported liveops submodules. Those submodules remain importable through their original paths without package initialization code."
    },
    {
      "source_path": "src/strategy_pipeline_internal/commands/__init__.py",
      "status": "complete",
      "internal_commit": "4da45c7d64168d1bd51f609592111ab189b17a0a",
      "test_evidence": "internal tests/test_retired_empty_package_facades.py; command and CLI regression tests; import boundary check",
      "rationale": "The package file contained only a comment and no initialization or public implementation. Command submodules remain importable through their original paths."
    },
    {
      "source_path": "src/strategy_pipeline_internal/release_tools/__init__.py",
      "status": "complete",
      "internal_commit": "4da45c7d64168d1bd51f609592111ab189b17a0a",
      "test_evidence": "internal tests/test_retired_empty_package_facades.py; release and CLI regression tests; import boundary check",
      "rationale": "The package file contained only a docstring and __all__. Release submodules remain importable through their original paths without package initialization logic."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/panel_enrichment.py",
      "status": "complete",
      "internal_commit": "2d6d132f0588001dcbd244000af52109603050c8",
      "test_evidence": "internal tests/test_retired_panel_enrichment_facade.py; internal full test suite",
      "rationale": "The six-line aggregation facade had no domain logic. Its consumer now imports the existing fundamentals and industry implementations directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/context_builder.py",
      "status": "complete",
      "internal_commit": "5b51c2059b987869c9d4e876073bcf22288f3a19",
      "test_evidence": "internal tests/test_retired_context_builder_facade.py; internal full test suite",
      "rationale": "The re-export shell had no unique implementation. Runner consumers now import the split API and core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/panel_load_steps.py",
      "status": "complete",
      "internal_commit": "2f9f5c144ee218cc99fbac8fbe973831b3cac2a9",
      "test_evidence": "internal tests/test_retired_panel_load_steps_facade.py; internal full test suite; data operations boundary check",
      "rationale": "The re-export shell had no unique implementation. Panel consumers now import the split API and core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/external_signals.py",
      "status": "complete",
      "internal_commit": "77519f89828a72fc3141e5aacb60bd2f9a06ddc5",
      "test_evidence": "internal tests/test_retired_external_signals_facade.py; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Runner consumers now import the external-signal API and core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/summarize_runs.py",
      "status": "complete",
      "internal_commit": "adf73b0caa93a1ecec6d806ac1079e3fd785ace6",
      "test_evidence": "internal tests/test_retired_summarize_runs_facade.py; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. CLI, tuning, release tooling, and tests now import the split summarize-runs API directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/runner.py",
      "status": "complete",
      "internal_commit": "311592c8a0d12ee586a39ec54800065c0b72ae98",
      "test_evidence": "internal tests/test_retired_runner_facade.py; internal runner tests; import boundary check",
      "rationale": "The runner module was a compatibility shell around the split runner API and core. Package and CLI consumers now use the API module directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/output_summary.py",
      "status": "complete",
      "internal_commit": "1b235b8fa865e2309bd042617a5e43458e2d7d36",
      "test_evidence": "internal tests/test_retired_output_summary_facade.py; pipeline output and summary regression tests; import boundary check",
      "rationale": "The module only re-exported the already split summary sections and metadata implementations. Output consumers now import those modules directly, so the redundant facade was retired."
    },
    {
      "source_path": "src/strategy_pipeline_internal/commands/linear_sweep.py",
      "status": "complete",
      "internal_commit": "18f59c659fbf2500d9d4a9727edaf63e6cef1fab",
      "test_evidence": "internal tests/test_retired_linear_sweep_facade.py; internal linear-sweep tests; import boundary check",
      "rationale": "The command module was a re-export shell. CLI and tests now use the split linear-sweep API directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_freshness.py",
      "status": "complete",
      "internal_commit": "5a7dd5ad594d5defd5c9dbb4e02b5ac858a88986",
      "test_evidence": "internal tests/test_daily_watch20_freshness.py; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. DailyWatch20 consumers now use the freshness API and core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_publication_validation.py",
      "status": "complete",
      "internal_commit": "7b5ef7ba1179910ae017e15e7b0884b6d007f267",
      "test_evidence": "internal tests/test_daily_watch20_publication_edge_guards.py; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Freshness and publication consumers now use the split validation API and core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_publish.py",
      "status": "complete",
      "internal_commit": "5cb4f61bda260a3a31e13908858d7cc5bd52ae2c",
      "test_evidence": "internal DailyWatch20 publication, pipeline, lifecycle, recovery, and safety tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Pipeline and publication consumers now use the split publish API directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_publication_inputs.py",
      "status": "complete",
      "internal_commit": "19e5924b72e7ebd83aa79c6a054c885f9aa3b8ff",
      "test_evidence": "internal tests/test_daily_watch20_minute.py; internal publication safety tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Publication validation and minute evidence consumers now use the split API and core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_deepseek_campaign_support.py",
      "status": "complete",
      "internal_commit": "9c695366023613f2b3544f18b07c6996103f1da9",
      "test_evidence": "internal Hotsector campaign and month tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Hotsector campaign and month consumers now import split core and API modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_deepseek_v4_month_plans.py",
      "status": "complete",
      "internal_commit": "510bd117337919309c565999d1d9260f286988b3",
      "test_evidence": "internal Hotsector month plans and backtest validation tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Month execution support and tests now use the split plans API/core directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_deepseek_v4_month_execution.py",
      "status": "complete",
      "internal_commit": "941ed0eca9b03d5c48991150b3401c1a0dc7e3f0",
      "test_evidence": "internal Hotsector month execution and backtest validation tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Month execution and backtest consumers now use the split execution core/API modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_deepseek_v4_month_backtest.py",
      "status": "complete",
      "internal_commit": "b603ff7a9628dc449d721104816b6062549920dd",
      "test_evidence": "internal Hotsector month backtest and validation tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Backtest validation now uses the split backtest API/core and execution modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/hotsector_deepseek_campaign.py",
      "status": "complete",
      "internal_commit": "f8fffa5172af7640784f5fb8cb6f6a5ba70c88b1",
      "test_evidence": "internal tests/test_hotsector_deepseek_campaign_runner.py; internal documentation entrypoint tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Campaign scripts and tests now use the split campaign API/core modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_ablation.py",
      "status": "complete",
      "internal_commit": "58068cd719022559822d93ba9b105b5c37020bae",
      "test_evidence": "internal tests/test_daily_watch20_ablation.py; internal DailyWatch20 policy and ownership tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. DailyWatch20 callers now use the split ablation API/core and owner modules directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/release_tools/package_runs.py",
      "status": "complete",
      "internal_commit": "b38f69f3168412c1df0aee2abc65568f93a14bf6",
      "test_evidence": "internal tests/test_run_release_scripts.py; internal namespace and data-boundary tests; internal full test suite; import boundary check",
      "rationale": "The re-export shell had no unique implementation. Release packaging and release-run callers now use the split package-runs API directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_slow_minute_campaign.py",
      "status": "complete",
      "internal_commit": "5cf7c2f8731324071ae2ead7bd8ec7825ff27cf1",
      "test_evidence": "strategy-app tests for slow-minute contracts and execution; internal tests/test_daily_watch20_slow_minute_campaign.py; internal full test suite; import boundary check",
      "rationale": "The campaign orchestration was composed entirely from strategy-app contracts, analysis, input, execution, decision, and reporting APIs. It now lives with the strategy-app owner and internal callers use that module directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_minute_campaign.py",
      "status": "complete",
      "internal_commit": "a198c155a5cc59ca04e0d7b1bcfd5f0ba48980d4",
      "test_evidence": "strategy-app tests/test_daily_watch20_minute_campaign_contract.py; internal tests/test_daily_watch20_minute_campaign.py; internal full test suite; import boundary check",
      "rationale": "The D/M/F/H campaign entrypoint only composed strategy-app campaign contracts, metrics, reporting, and input APIs. It now lives with the strategy-app owner."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_minute_campaign_inputs.py",
      "status": "complete",
      "internal_commit": "9c9555de0b1bdff85ebbb0dcc813795d5535f075",
      "test_evidence": "strategy-app tests/test_daily_watch20_minute_campaign_contract.py; strategy-app minute cache and friend-minute tests; internal tests/test_daily_watch20_minute_campaign.py; import boundary check",
      "rationale": "Minute campaign input loading, universe freezing, friend-feature lineage, and Hermite input binding now live in strategy-app alongside the campaign owner."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_market_shadow.py",
      "status": "complete",
      "internal_commit": "8be7c39894bcbb338b981a6868aee97f0d4dbc11",
      "test_evidence": "internal market-shadow, publication, candidate OOS, and full test suites; import boundary check",
      "rationale": "The module was a compatibility re-export of the strategy-app market-shadow API. Internal callers now import the owner module directly."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_ablation_reporting.py",
      "status": "complete",
      "internal_commit": "6c3f709f1131d9459270a8847dc3e0f3a3e8f3ae",
      "test_evidence": "strategy-app tests/test_daily_watch20_ablation_evaluation.py; internal tests/test_daily_watch20_ablation.py; internal import-boundary tests",
      "rationale": "The report builder only assembled the DailyWatch20 research report and now lives with the strategy-app ablation owner."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_topic_summary.py",
      "status": "complete",
      "internal_commit": "a25253244d6a5368d502b8190a7c16d598a86e9d",
      "test_evidence": "strategy-app tests/test_daily_watch20_topic_summary.py; internal DailyWatch20 publication-safety and late-recovery tests; import boundary check",
      "rationale": "The topic summary is presentation-only aggregation logic. It now lives with the strategy-app DailyWatch20 application owner."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_explanations.py",
      "status": "complete",
      "internal_commit": "7184ffdc90cf6554ddaef682bbd8fb72b5cd9867",
      "test_evidence": "strategy-app tests/test_daily_watch20_explanations.py; internal tests/test_daily_watch20_pipeline.py and publication-safety tests; import boundary check",
      "rationale": "Theme grouping, feature labels, candidate explanations, and market-regime summaries are application presentation logic. They now live with the strategy-app DailyWatch20 owner."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_freshness_receipt.py",
      "status": "complete",
      "internal_commit": "7889af04b7aa9115073746fcce284106fc6ac285",
      "test_evidence": "market-data-platform tests/test_daily_watch20_freshness_receipt.py; internal tests/test_daily_watch20_freshness.py and runtime-preflight tests; import boundary check",
      "rationale": "Canonical minute partition, coverage receipt, daily audit, and hash validation belong to the market-data-platform data-quality boundary."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_runtime_preflight.py",
      "status": "complete",
      "internal_commit": "aa648a6c4ca975c4adb9f8593629da3ee76583aa",
      "test_evidence": "market-data-platform tests/test_daily_watch20_runtime_preflight.py; internal freshness tests; import boundary check",
      "rationale": "The preflight only verifies the market-data-platform minute-cache rolling-window contract, so it now lives with that dependency owner."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_publication_policy.py",
      "status": "complete",
      "internal_commit": "c430667f95eb7de6655d0d5ab9d25e8f280e182a",
      "test_evidence": "strategy-pipeline tests/control_plane/test_currentness.py; internal tests/test_daily_watch20_freshness.py and strategy extraction tests; public history audit",
      "rationale": "The policy only applied generic production or research currentness rules. Its domain-neutral implementation now lives in public strategy-pipeline, while internal keeps only the DailyWatch20 result-shape adapter."
    },
    {
      "source_path": "src/strategy_pipeline_internal/daily_watch20_application_policy.py",
      "status": "complete",
      "internal_commit": "e405209db006989bdd7288ebd324e845d822e5b7",
      "test_evidence": "internal tests/test_retired_daily_watch20_application_policy.py; internal tests/test_standalone_strategy_app_extraction.py; import boundary check",
      "rationale": "The module had no active runtime callers. Its research policy and publication currentness inputs already belong to their respective owner packages, so the unused composition facade was retired instead of creating a reverse dependency from strategy-app to strategy-pipeline."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/support.py",
      "status": "complete",
      "internal_commit": "761a4fc725f131f5f4be1c3aa2b28b7faf8e307d",
      "test_evidence": "internal panel-join, symbol-alias, historical-symbol-owner, validation, external-signal, and runtime tests: 53 passed; public support implementation already covered by strategy-pipeline migration tests",
      "rationale": "The internal file duplicated the public support implementation. It is now a compatibility facade that resolves historical helper names from strategy-pipeline.pipeline.support."
    },
    {
      "source_path": "src/strategy_pipeline_internal/cli/evidence.py",
      "status": "complete",
      "internal_commit": "a7927998b0cbef4fc1e00b89038c457195ad0a60",
      "test_evidence": "internal CLI, protocol, namespace, and strategy-pipeline regression tests passed",
      "rationale": "The internal module now re-exports the public AFML evidence command handler and retains the historical import path."
    },
    {
      "source_path": "src/strategy_pipeline_internal/cli/protocol.py",
      "status": "complete",
      "internal_commit": "a7927998b0cbef4fc1e00b89038c457195ad0a60",
      "test_evidence": "internal CLI, protocol, namespace, and strategy-pipeline regression tests passed",
      "rationale": "The internal module now re-exports the public research protocol command handler and retains the historical import path."
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/panel_join_support.py::Parquet and CSV file I/O helpers",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/standardize/parquet.py",
      "status": "complete",
      "owner_commit": "4c6ca92ae656d9e5d649513ef079f926c444bdb9",
      "internal_commit": "dc9cbb6549d24f53a50290147652505c6300ce6f",
      "test_evidence": "market-data-platform tests/test_research_parquet_io.py: 3 passed; internal panel join, file build, file-derived, CLI research, CLI core, impact, and pipeline E2E tests: 58 passed",
      "doc_evidence": "market-data-platform/docs/research-parquet-io.md; market-data-platform PR #116",
      "consumer_switch": "internal panel join loading now delegates schema inspection, column selection, Hive partition handling, and Parquet fallback reads to market-data-platform"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/config_eval.py::_normalize_bucket_ic",
      "owner_repo": "alpha-research",
      "target_path": "src/alpha_research/evaluation_config.py::normalize_bucket_ic",
      "status": "complete",
      "owner_commit": "1a424e513c35cd5c732f1a9f51c67ac2e68e3e2a",
      "internal_commit": "d3d7b82b3f2ad1ded0defc46d737f246c0db5643",
      "migration_pr": "alpha-research PR #72; strategy-pipeline-internal PR #270",
      "test_evidence": "alpha-research tests/test_evaluation_config.py: 9 passed; internal tests/test_migrated_evaluation_config_normalizers.py: 8 passed",
      "doc_evidence": "alpha-research/docs/concepts/feature-research-protocol.md",
      "consumer_switch": "internal evaluation config now delegates bucket IC normalization to alpha-research and no longer owns the implementation"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/eval.py",
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/pipeline/eval.py",
      "status": "complete",
      "owner_commit": "1f602a9",
      "internal_commit": "bc5d809",
      "migration_pr": "strategy-pipeline PR #11; strategy-pipeline-internal PR #253",
      "test_evidence": "strategy-pipeline evaluation orchestration tests; internal tests/test_pipeline_position_postprocess.py and namespace retirement checks",
      "doc_evidence": "strategy-pipeline/docs/pipeline-overview.md",
      "consumer_switch": "internal evaluation callers now import the public strategy-pipeline evaluator, while the historical module retains only compatibility imports"
    }
  ],
  "completed_boundary_cleanups": [
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/__init__.py",
      "status": "complete",
      "internal_commit": "2ba256df7f50f5457a78c8f1d34eb7691cbd122c",
      "test_evidence": "internal tests/test_retired_research_ops_init.py; trial registry and research CLI tests; import boundary check",
      "consumer_switch": "research ops consumers now load trial_registry as a direct submodule without the package facade"
    }
  ]
}
```

## 清单使用规则

- `planned` 表示目标和下一步已确定，迁移证据尚未齐全。
- `private` 表示仍在 internal 中作为当前能力使用，不能直接删除。
- `archive` 表示历史材料，不属于当前运行入口，也不计入 active 迁移完成度。
- `complete` 只允许在代码、测试、配置、文档和 workspace 集成证据全部具备后使用。
- 每个 owner PR 合并后必须更新对应记录和 `source_commit`，并附上迁移 PR 或 commit。
