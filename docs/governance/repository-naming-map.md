# 仓库命名迁移字典

> status: active
> owner: workspace
> audience: human and agent
> last_verified: 2026-09-06
> source_of_truth: yes
> superseded_by: n/a

本页冻结工作区仓库名的候选迁移关系。候选名只用于规划和后续协调，当前不改远端仓库名、
本地目录、GitHub URL、gitlink、Python namespace、CLI、生产配置或历史事实。

## Target decision

The target is not a one-for-one rename of every current submodule. The repository boundary is
being consolidated around visibility, IP, and runtime ownership:

| Current component | Target location | Target decision |
| --- | --- | --- |
| `market-data-platform` | `quant-platform/data` plus private provider/runtime configuration | Consolidate the reusable data surface; keep real providers and credentials private |
| `deep-learning-tick-data-prediction` | `quant-platform/microstructure` plus `quant-research/microstructure/experiments` | Split generic model/data abstractions from proprietary labels, configs, and results |
| `alpha-research` | `quant-platform/alpha` | Consolidate reusable research mechanisms; keep proprietary feature selections private |
| `portfolio-backtester` | `quant-platform/portfolio` | Consolidate as a package while preserving its installable public API where useful |
| `strategy-research` | `quant-research/registry` and `quant-research/research` | Rename conceptually to `quant-research`; it is broader than a registry |
| `strategy-app` | `quant-research/strategies` | Absorb into the private strategy monorepo; retain `strategy_app` namespace initially |
| `strategy-pipeline` | `quant-platform/orchestration` | Consolidate the reusable control plane and artifact publication surface |
| `quant-execution-engine` | `quant-platform/execution` public interfaces plus private runtime adapters | Keep live broker, credentials, and audit runtime private during the public audit |
| `market-intel` | `market-intel` | Remain an independent private application |
| `research-workspace` | `research-workspace` | Remain a thin integration/release layer; do not become a second business owner |

This target mapping is a migration decision, not permission to rename all remote repositories in one
change. Remote names, URLs, Python namespaces, CLIs, and artifact schemas remain compatibility
surfaces and are migrated independently.

## Transitional candidate names

| 当前仓库名 | 候选新名 | 当前决定 | 说明 |
| --- | --- | --- | --- |
| `strategy-research` | `strategy-registry` | 仅登记候选 | 远端名和所有现有路径继续有效 |
| `strategy-app` | `strategy-logic` | 仅登记候选 | `strategy_app` namespace 不随仓库名变化 |
| `strategy-pipeline` | `strategy-orchestrator` | 仅登记候选 | `strategy_pipeline` namespace 与 CLI 继续保留 |
| `deep-learning-tick-data-prediction` | `microstructure-models` | 仅登记候选 | `ticknet` namespace 继续保留 |

以下仓库当前不改名：`alpha-research`、`portfolio-backtester`、
`quant-execution-engine`、`market-intel`。

## 不同时迁移的名称

仓库名、Python namespace 和 CLI 是三个独立兼容面。本任务不改变：

- `strategy_pipeline`、`strategy_app`、`ticknet` 及其导入路径；
- `strategy`、`strategy-pipeline` 及其他现有 CLI 名称；
- `.gitmodules`、gitlink、远端 URL、生产目录和部署配置。

namespace 或 CLI 的迁移必须另建任务，包含兼容期、消费者清单和回滚证据。

## 当前引用分类

以下分类来自本任务要求的精确搜索命令：

```bash
rg -n "strategy-research|strategy-app|strategy-pipeline|deep-learning-tick-data-prediction" .
```

搜索结果中的现有引用按用途处理如下。引用继续保留，分类用于未来迁移时逐项审核：

| 分类 | 典型位置或形式 | 本任务处理 |
| --- | --- | --- |
| URL | GitHub 链接、文档链接、远端仓库地址 | 保留真实地址，不把候选名写入 URL |
| 路径 | 子模块目录、源码路径、数据路径、运行目录 | 保留当前路径，避免破坏 gitlink 和生产读取 |
| 文档 | README、ARCHITECTURE、治理、ADR、计划和归档 | 当前页增加迁移说明；其他事实不改写 |
| import | `strategy_pipeline`、`strategy_app`、`ticknet` 等 Python 引用 | 保留 namespace，另建迁移任务 |
| CLI | `strategy`、`strategy-pipeline` 等命令及帮助文本 | 保留命令名和调用方式 |
| 生产配置 | YAML、JSON、TOML、shell 脚本及发布/检查配置 | 保留配置键、路径和项目标识 |
| 历史记录 | 版本矩阵、归档、审计、提交或迁移记录 | 只增加本迁移说明，不修改历史事实 |

搜索同时会命中跨仓契约、测试、脚本和治理基线。这些属于当前系统的有效引用，不因候选
仓库名而自动改写。迁移开始前，应先建立影响清单并分别验证远端、路径、namespace、CLI、
配置、gitlink 和历史记录。

## 使用规则

候选名不是当前别名，也不是可直接使用的替换字符串。任何后续仓库改名任务都必须：

1. 更新本页的决定和迁移状态；
2. 明确远端仓库、工作区目录、URL、gitlink、namespace、CLI 和生产配置的独立变更；
3. 保留历史名称的可追溯说明，并运行工作区治理、doctor 和相关消费者检查。
