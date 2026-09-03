# strategy-pipeline-internal 迁移清单

> status: active
> owner: workspace
> source_of_truth: yes
> source_commit: `b603ff7a9628dc449d721104816b6062549920dd`
> last_verified: 2026-09-03

这份清单记录 internal 当前 main 的迁移起点。模块记录按职责分组，文件数量来自 Git tree。文档记录保留逐文件的迁移判断，后续每个切片合并后更新 `status`、目标路径和证据字段。

```json
{
  "schema_version": "strategy_pipeline_internal_migration.v1",
  "source_repository": "runchengxie/strategy-pipeline-internal",
  "source_commit": "b603ff7a9628dc449d721104816b6062549920dd",
  "inventory": {
    "python_source_files": 143,
    "test_files": 201,
    "script_files": 34,
    "config_files": 18,
    "ownership_document_files": 114,
    "ownership_document_status_counts": {
      "complete": 8,
      "private": 58,
      "planned": 16,
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
      "file_count": 11,
      "owner_repo": "research-workspace",
      "target_path": "scripts and workspace entrypoints",
      "status": "private",
      "test_evidence": "workspace command and pre-push smoke tests",
      "doc_evidence": "workspace maintenance and bootstrap docs",
      "removal_condition": "all commands have owner-native replacements"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops",
      "file_count": 9,
      "owner_repo": "quant-execution-engine",
      "target_path": "src/quant_execution_engine/liveops",
      "status": "planned",
      "test_evidence": "execution audit and run smoke tests",
      "doc_evidence": "execution and operational runbook",
      "removal_condition": "execution engine owns liveops and audit entrypoints"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline",
      "file_count": 45,
      "owner_repo": "strategy-pipeline",
      "target_path": "src/strategy_pipeline/control_plane",
      "status": "planned",
      "test_evidence": "public clean-room control-plane tests",
      "doc_evidence": "strategy-pipeline public API docs",
      "removal_condition": "remaining pipeline modules contain no domain knowledge"
    },
    {
      "source_path": "src/strategy_pipeline_internal/release_tools",
      "file_count": 7,
      "owner_repo": "research-workspace",
      "target_path": "scripts and release governance",
      "status": "private",
      "test_evidence": "release gate and version matrix tests",
      "doc_evidence": "release checklist and version matrix",
      "removal_condition": "workspace release tooling no longer imports internal"
    },
    {
      "source_path": "src/strategy_pipeline_internal/root_modules",
      "file_count": 64,
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
    {"source_path": "docs/concepts/metric-ownership.md", "owner_repo": "research-workspace", "target_path": "docs/metric-ownership.md", "status": "planned"},
    {"source_path": "docs/concepts/pit-coverage.md", "owner_repo": "market-data-platform", "target_path": "docs/a-share-fundamentals.md; docs/contracts.md", "status": "complete", "test_evidence": "tests/test_tushare_a_share_fundamentals.py; tests/test_current_path_audit.py"},
    {"source_path": "docs/concepts/research-protocols.md", "owner_repo": "alpha-research", "target_path": "docs/concepts/feature-research-protocol.md; docs/concepts/overfitting-controls.md", "status": "complete", "test_evidence": "tests/test_feature_evidence.py; tests/test_promotion_gate.py"},
    {"source_path": "docs/concepts/shared-hk-data-platform.md", "owner_repo": "market-data-platform", "target_path": "docs/operations/hk-archive-restore.md; docs/contracts.md", "status": "complete", "test_evidence": "tests/test_quality_governance.py; tests/test_dataset_contracts.py"},
    {"source_path": "docs/playbooks/a-share-baseline.md", "owner_repo": "strategy-app", "target_path": "docs/playbooks/a-share-baseline.md", "status": "planned"},
    {"source_path": "docs/playbooks/hk-selected.md", "owner_repo": "strategy-app", "target_path": "docs/playbooks/hk-selected.md", "status": "planned"},
    {"source_path": "docs/providers.md", "owner_repo": "market-data-platform", "target_path": "docs/integrations.md; docs/operations/credentials.md", "status": "complete", "test_evidence": "tests/test_data_providers_cache.py; tests/test_cli_dependency_boundaries.py"},
    {"source_path": "docs/reference/outputs/full-reference.md", "owner_repo": "research-workspace", "target_path": "docs/reference/outputs/full-reference.md", "status": "planned"},
    {"source_path": "docs/reference/outputs/platform-assets.md", "owner_repo": "market-data-platform", "target_path": "docs/contracts.md; docs/data-warehouse.md", "status": "complete", "test_evidence": "tests/test_paths.py; tests/test_data_warehouse.py"},
    {"source_path": "docs/research/README.md", "owner_repo": "strategy-app", "target_path": "docs/research/README.md", "status": "planned"},
    {"source_path": "docs/research/daily-watch20-live-readiness-20260714.md", "owner_repo": "strategy-app", "target_path": "docs/research/daily-watch20-live-readiness-20260714.md", "status": "planned"},
    {"source_path": "docs/research/incumbent-challenger-evidence-v2.md", "owner_repo": "strategy-app", "target_path": "docs/research/incumbent-challenger-evidence-v2.md", "status": "planned"},
    {"source_path": "docs/research/next-open-to-high-audit.md", "owner_repo": "strategy-app", "target_path": "docs/research/next-open-to-high-audit.md", "status": "planned"},
    {"source_path": "docs/strategy-catalog.md", "owner_repo": "strategy-app", "target_path": "docs/strategy-catalog.md", "status": "planned"}
  ],
  "completed_code_migrations": [
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
    }
  ],
  "partial_code_migrations": [
    {
      "source_path": "src/strategy_pipeline_internal/legacy_rqdata_runtime.py::normalize_legacy_symbol_for_market",
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/symbols.py::normalize_historical_hk_symbol",
      "status": "complete",
      "owner_commit": "f8506e996a9076e14d3031a378554e0ea262581e",
      "internal_commit": "8dcf457f9bb442c2b517effbcedbcd35f7143bff",
      "test_evidence": "market-data-platform tests/test_market_specs.py; internal tests/test_historical_hk_symbol_owner.py",
      "remains_active": "legacy_rqdata_runtime.py was deleted in internal PR #143 after its remaining callers were removed"
    }
  ],
  "retired_internal_facades": [
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
    }
  ],
  "completed_boundary_cleanups": [
    {
      "source_path": "src/strategy_pipeline_internal/pipeline/research_ops/__init__.py",
      "status": "complete",
      "internal_commit": "cd5d9e0411a97242d71eabc971824d79024cbdd9",
      "test_evidence": "internal tests/test_retired_promotion_gate_facades.py; internal full test suite; import boundary check",
      "consumer_switch": "promotion-gate config and CLI tests now import alpha_research.promotion_gate directly"
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
