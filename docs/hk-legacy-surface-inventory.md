# 港股 legacy surface inventory

本页记录中国香港市场相关代码在 A 股主线迁移期间的保留边界。它不是删除清单；在远端
freeze release 完成下载、校验和 restore drill 前，不应批量迁出港股实现。

## 分类

| 分类 | 含义 | 处理方式 |
| --- | --- | --- |
| `shared_active` | 多市场 contract、执行或恢复能力仍需要 | 保留并继续跑 focused tests |
| `frozen_compatibility` | 港股复现或明确跟踪需求仍可能调用 | 保留入口，标记 deprecated，不扩展 A 股主线 |
| `archived_provenance` | 只用于解释历史研究和 release | restore drill 后迁入归档或 public demo |
| `retire_after_audit` | 已有替代入口，但仍需下游使用审计 | 审计和回滚证据完成后删除 |

## 数据平台

| Surface | 分类 | 依赖与决定 |
| --- | --- | --- |
| `metadata/frozen_markets/hk.json`、`marketdata migration freeze-hk`、`hydrate-hk` | `shared_active` | 顶层 doctor、冷存储恢复和历史复现需要 |
| `src/market_data_platform/hk_assets/`、`hk_depth/`、release tools | `frozen_compatibility` | 港股数据 release 与 restore-critical 支持；停止新增研究需求 |
| `src/hk_data_platform/`、`hkdata`、`rqdata-hk-*` 兼容入口 | `retire_after_audit` | 新调用方使用 `marketdata`；删除前运行 compatibility governance |
| 历史港股 release preset、handoff 和 manifest | `archived_provenance` | 保留用于 checksum、restore drill 和审计 |

## 策略研究

| Surface | 分类 | 依赖与决定 |
| --- | --- | --- |
| 通用 pipeline、回测、`targets.json` 导出 | `shared_active` | A 股继续复用，不按市场拆分 |
| `configs/presets/hk.yml`、`default` 当前兼容 alias | `frozen_compatibility` | A 股 promotion gate 通过前保留 |
| `cstree alloc-hk` 与 `src/cstree/liveops/alloc_hk*` | `frozen_compatibility` | repo-local consumer 为 CLI、文档和测试；保留 deprecated compatibility command |
| `configs/experiments/*hk*`、`docs/research/notes/hk-*` | `archived_provenance` | 只保留解释和复现入口，不再作为活跃研究默认预算入口 |
| 研究仓库中的旧数据生产 wrapper | `retire_after_audit` | 新资产生产归 `market-data-platform`；按 data-ops boundary 审计删除 |

## 交易执行

| Surface | 分类 | 依赖与决定 |
| --- | --- | --- |
| 标准 `targets.json`、HK/CN/US/SG 解析、FX、dry-run、风控和审计 | `shared_active` | 执行层保持多市场，不因港股研究冻结而删除 |
| 长桥 HK symbol、HKD FX 和 broker adapter | `shared_active` | 仍属于 broker 能力矩阵，继续保留 focused tests |

## 决策

1. 港股数据资产和研究输出继续使用现有 freeze release；恢复时先下载并校验 SHA-256。
2. `alloc-hk` 暂不拆包，保留为 deprecated compatibility command。新增 A 股流程使用
   `cstree alloc`、`cstree export-targets` 和执行引擎 dry-run。
3. 港股实验、历史笔记和 research-only provenance 在 restore drill、source tag 和 archive
   manifest 完成后再迁出，避免破坏可复现性。
4. 公开展示库使用 clean-room export，不复制 Git 历史，不成为 workspace submodule。

## 回滚顺序

1. A 股候选未通过 promotion gate 时，保持研究仓库 `default` 指向港股兼容 starter。
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
