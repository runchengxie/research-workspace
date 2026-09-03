# strategy-pipeline-internal 迁移清单

> status: active
> owner: workspace
> source_of_truth: yes
> source_commit: `fa0e2aae6273c78331da19888b95070254d490c3`
> last_verified: 2026-09-03

这份清单记录 internal 当前 main 的迁移起点。模块记录按职责分组，文件数量来自 Git tree。文档记录保留逐文件的迁移判断，后续每个切片合并后更新 `status`、目标路径和证据字段。

```json
{
  "schema_version": "strategy_pipeline_internal_migration.v1",
  "source_repository": "runchengxie/strategy-pipeline-internal",
  "source_commit": "fa0e2aae6273c78331da19888b95070254d490c3",
  "inventory": {
    "python_source_files": 194,
    "test_files": 180,
    "script_files": 34,
    "config_files": 21,
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
      "source_path": "src/strategy_pipeline_internal/adapters",
      "file_count": 2,
      "owner_repo": "market-data-platform",
      "target_path": "src/market_data_platform/providers",
      "status": "planned",
      "test_evidence": "tests to be migrated with data/provider slice",
      "doc_evidence": "docs/concepts/data-sources.md; docs/providers.md",
      "removal_condition": "provider consumer search is clear and owner smoke passes"
    },
    {
      "source_path": "src/strategy_pipeline_internal/campaign_specs",
      "file_count": 1,
      "owner_repo": "strategy-app",
      "target_path": "src/strategy_app/campaigns",
      "status": "planned",
      "test_evidence": "tests to be migrated with strategy application slice",
      "doc_evidence": "docs/research/README.md",
      "removal_condition": "strategy-app owns campaign loading and validation"
    },
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
      "file_count": 12,
      "owner_repo": "research-workspace",
      "target_path": "scripts and workspace entrypoints",
      "status": "private",
      "test_evidence": "workspace command and pre-push smoke tests",
      "doc_evidence": "workspace maintenance and bootstrap docs",
      "removal_condition": "all commands have owner-native replacements"
    },
    {
      "source_path": "src/strategy_pipeline_internal/contracts",
      "file_count": 4,
      "owner_repo": "research-workspace",
      "target_path": "docs/contracts and src/research_contracts",
      "status": "planned",
      "test_evidence": "artifact contract and lineage tests",
      "doc_evidence": "docs/contracts.md and docs/artifact-contracts.yml",
      "removal_condition": "workspace contract is the only cross-repository schema entry"
    },
    {
      "source_path": "src/strategy_pipeline_internal/liveops",
      "file_count": 10,
      "owner_repo": "quant-execution-engine",
      "target_path": "src/quant_execution_engine/liveops",
      "status": "planned",
      "test_evidence": "execution audit and run smoke tests",
      "doc_evidence": "execution and operational runbook",
      "removal_condition": "execution engine owns liveops and audit entrypoints"
    },
    {
      "source_path": "src/strategy_pipeline_internal/pipeline",
      "file_count": 60,
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
      "file_count": 91,
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
  ]
}
```

## 清单使用规则

- `planned` 表示目标和下一步已确定，迁移证据尚未齐全。
- `private` 表示仍在 internal 中作为当前能力使用，不能直接删除。
- `archive` 表示历史材料，不属于当前运行入口，也不计入 active 迁移完成度。
- `complete` 只允许在代码、测试、配置、文档和 workspace 集成证据全部具备后使用。
- 每个 owner PR 合并后必须更新对应记录和 `source_commit`，并附上迁移 PR 或 commit。
