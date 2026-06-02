# 港股 legacy surface inventory

本页记录中国香港市场相关代码在 A 股主线迁移期间的保留边界。批量迁出港股实现前，
必须先完成远端 freeze release 下载、校验和 restore drill。

可执行 split / cleanup 决策见
[`hk-public-split-manifest.yml`](hk-public-split-manifest.yml)。本页给维护者读边界和背景；
manifest 记录 repo-local surface、public safety、consumer audit、replacement path 和
removal condition。

## 分类

| 分类 | 含义 | 处理方式 |
| --- | --- | --- |
| `shared_active` | 多市场 contract、执行或恢复能力仍需要 | 保留并继续跑 focused tests |
| `frozen_compatibility` | 港股复现或明确跟踪需求仍可能调用 | 保留入口，标记 deprecated，不扩展 A 股主线 |
| `archived_provenance` | 只用于解释历史研究和 release | restore drill 后迁入归档或 public demo |
| `retire_after_audit` | 已有替代入口，但仍需下游使用审计 | 审计和回滚证据完成后删除 |

## 数据平台

| Surface | 分类 | Owner | 活跃消费者 | 测试 | 回滚证据 |
| --- | --- | --- | --- | --- | --- |
| `metadata/frozen_markets/hk.json`、`marketdata migration freeze-hk`、`hydrate-hk` | `shared_active` | `market-data-platform` | 顶层 doctor、冷存储恢复、历史复现 | `tests/test_cold_storage.py`、顶层 doctor tests | `evidence/hk-restore-drill-20260601.json` |
| `src/market_data_platform/hk_assets/`、`hk_depth/`、release tools | `frozen_compatibility` | `market-data-platform` | restore-critical release 与专项排障 | `tests/test_hk_asset_workflow.py`、`tests/test_hk_depth.py` | freeze release manifest 与 restore drill |
| `src/hk_data_platform/`、`hkdata`、`rqdata-hk-*` 兼容入口 | `retire_after_audit` | `market-data-platform` | 旧脚本调用方 | compatibility governance tests | 新调用方改用 `marketdata` 后按 release tag 回滚 |
| 历史港股 release preset、handoff 和 manifest | `archived_provenance` | `market-data-platform` | 人工审计 | checksum 与 restore drill | freeze release manifest |

## 策略研究

| Surface | 分类 | Owner | 活跃消费者 | 测试 | 回滚证据 |
| --- | --- | --- | --- | --- | --- |
| 通用 pipeline、回测、`targets.json` 导出 | `shared_active` | `cross-sectional-trees` | A 股与显式港股复现 | fast tests、`tests/test_export_targets.py` | A 股与港股版本化 preset |
| `configs/presets/hk.yml` | `frozen_compatibility` | `cross-sectional-trees` | 显式 `--config hk` 历史复现 | config 与 minimal HK smoke | `default` 回滚时显式继承 `hk.yml` |
| `cstree alloc-hk` 与 `src/cstree/liveops/alloc_hk*` | `frozen_compatibility` | `cross-sectional-trees` | CLI、文档、专项报告 | `tests/test_alloc_hk.py`、`tests/test_cli_liveops.py` | 保留 deprecated compatibility command |
| `configs/experiments/*hk*`、`docs/research/notes/hk-*` | `archived_provenance` | `cross-sectional-trees` | 人工复现与审计 | docs contract tests | `evidence/hk-research-archive-manifest-20260601.json` |
| 研究仓库中的旧数据生产 wrapper | `retire_after_audit` | `cross-sectional-trees` | 无新增调用方 | data-ops boundary tests | 新资产生产固定归 `market-data-platform` |

## 交易执行

| Surface | 分类 | Owner | 活跃消费者 | 测试 | 回滚证据 |
| --- | --- | --- | --- | --- | --- |
| 标准 `targets.json`、HK/CN/US/SG 解析、FX、dry-run、风控和审计 | `shared_active` | `quant-execution-engine` | 多市场执行文件契约 | default pytest、targets contract tests | 标准 targets schema 与审计日志 |
| 长桥 HK symbol、HKD FX 和 broker adapter | `shared_active` | `quant-execution-engine` | 港股模拟盘与实盘人工流程 | retained HK execution tests | broker evidence bundle 与人工 smoke 记录 |

## 决策

1. 港股数据资产和研究输出继续使用现有 freeze release；恢复时先下载并校验 SHA-256。
2. `alloc-hk` 暂不拆包，保留为 deprecated compatibility command。新增 A 股流程使用
   `cstree alloc`、`cstree export-targets` 和执行引擎 dry-run。
3. 港股实验、历史笔记和 research-only provenance 在 restore drill、source tag 和 archive
   manifest 完成后再迁出，避免破坏可复现性。
4. 公开展示库使用 clean-room export，不复制 Git 历史，不成为 workspace submodule。
5. 研究仓库默认 CI 只保留 A 股、共享 pipeline、target export 和最小港股兼容 smoke；
   较重的港股 optional-extra 与 legacy matrix 改为手动触发。
6. restore-sensitive 港股实现的删除或迁出，需要先完成 source tag、archive manifest、
   restore drill 和消费者审计；公开 demo 只能作为展示面证据。

## Cleanup gate

当前没有 restore-sensitive 或 compatibility surface 在本轮直接删除。后续若删除
`hkdata`、`hk_data_platform.*`、`rqdata-hk-*`、`cstree alloc-hk` 或港股历史配置，需要先在
`hk-public-split-manifest.yml` 中把对应记录推进到 deletion gate `ready`，并补齐：

- restore evidence；
- downstream consumer audit；
- replacement docs；
- rollback notes；
- owning repo focused tests；
- 需要公开 demo 承接时的 public split evidence。

## 本机外部状态复核

2026-06-01 本轮复核确认以下冷存储目录在当前机器上均不存在：

```text
/home/richard/data/market-data-platform-cold/hk-freeze-20260526
/home/richard/data/cross-sectional-trees-cold/hk-research-freeze-20260601
```

`metadata/frozen_markets/hk.json` 已明确写入 `local_snapshot_available: false` 和 release 下载
前置条件。历史 restore drill 仍能说明远端归档曾通过校验，但不能证明当前机器可以立即
hydrate。数据平台兼容治理复核还显示 `hkdata`、`hk_data_platform.*` 和 `rqdata-hk-*` 仍有
repo-local 调用或文档引用。因此本轮不删除 restore-sensitive 或兼容入口代码；后续迁出前
必须先恢复两个外部归档，并重新执行消费者审计和 restore drill。

## 回滚顺序

1. A 股证据回归时，显式评估将研究仓库 `default` 回滚到 `hk.yml` 兼容入口或上一版 tag；
   不把这种回滚当作港股恢复已经自动完成。
2. 需要复现港股时，先下载 freeze release、校验 SHA-256，再运行
   `marketdata migration hydrate-hk --apply`。
3. `hydrate-hk` 拒绝覆盖活跃路径；恢复前先检查计划，不在活跃根目录创建指向冷存储的软链接。
4. 港股历史实验迁出活跃 lane 前，必须记录 source tag、archive manifest 和 restore drill 证据。

最终演练证据见
[`evidence/hk-restore-drill-20260601.json`](evidence/hk-restore-drill-20260601.json)：
两个远端 freeze release 已下载并通过 SHA-256 与 zstd 校验，数据平台资产和研究产物都已
在隔离根完成 hydrate apply。研究侧 archive manifest 见
[`evidence/hk-research-archive-manifest-20260601.json`](evidence/hk-research-archive-manifest-20260601.json)。
港股 run / sweep / report / live / benchmark / export 产物已经迁出活跃研究 lane；仓库中
仍保留的港股配置、历史笔记和工具入口只作为 `archived_provenance` 或
`frozen_compatibility` 兼容面存在。
