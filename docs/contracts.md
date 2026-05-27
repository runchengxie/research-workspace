# Workspace Contracts

本文档只记录跨模块交接契约。模块内部格式、业务参数和完整命令说明仍归各子项目维护。

## Boundary

顶层允许依赖两类接口：

- 公开 CLI：例如 `marketdata ...`、`cstree ...`、`rqdata-hk-depth ...`、`qexec ...`。
- 稳定文件契约：例如 current contract、dataset registry、研究输出、canonical `targets.json`。

顶层不应：

- `import` 子模块内部 Python 实现。
- 读取子模块临时工作目录作为正式数据来源。
- 维护一份覆盖所有模块参数的总 YAML。
- 默认触发真实券商交易。

## Source Of Truth

| 契约 | 生产方 | 消费方 | 定位 |
| --- | --- | --- | --- |
| `DATA_PLATFORM_ROOT` | 操作环境 | 数据平台、研究系统 | 共享资产根目录；不由顶层硬编码 |
| `metadata/current_assets/hk_current.json` | `market-data-platform` / transition HK workflow | `cross-sectional-trees` | HK 当前可用资产 contract |
| `metadata/current_assets/cn_current.json` | `market-data-platform` | 下游研究或数据消费者 | CN 当前可用资产 contract |
| `metadata/dataset_registry.csv` | `market-data-platform` | 人工审计、研究系统 | 已发布数据资产索引 |
| versioned asset directories | 数据维护模块 | 研究系统 | 真正的数据资产 |
| `summary.json` | `cross-sectional-trees` | 人工审计、后续导出 | 研究 run 摘要 |
| `positions_current*.csv` | `cross-sectional-trees` | `cstree export-targets` | 已保存的 live 持仓候选 |
| `targets.json` | `cstree export-targets` | `quant-execution-engine` | 标准化执行目标输入 |
| `targets.json.lineage.json` | `cstree export-targets` | 审计、复现 | 执行交接 lineage sidecar |
| order audit / evidence outputs | `quant-execution-engine` | 人工审计 | 执行系统自己的审计证据 |

## Data Contract Rules

数据资产交接通过 current contract 和 versioned asset directories 完成：

```text
$DATA_PLATFORM_ROOT/
  assets/
  metadata/
    current_assets/
      hk_current.json
      cn_current.json
    dataset_registry.csv
  reports/
```

约定：

- `current_assets/*.json` 指向当前推荐消费的数据资产版本。
- `dataset_registry.csv` 用于审计和发现，不替代 current contract。
- 顶层不提交数据本体、缓存、下载中间态或报告产物。
- 子模块工作目录中的临时输出不是跨模块 source of truth。

## Research To Execution Contract

研究系统的正式交接点是 `cstree export-targets` 生成的 canonical `targets.json`：

```text
cross-sectional-trees live run
  -> cstree export-targets
  -> targets.json
  -> quant-execution-engine dry-run / paper / live-gated flow
```

约定：

- `cstree export-targets` 只生成目标文件和 lineage sidecar。
- 导出命令不连接券商、不预演订单、不提交订单。
- `qexec rebalance <targets.json>` 的 broker 连接、preflight、paper / live 门禁属于 `quant-execution-engine`。
- 顶层脚本不得默认追加 `--execute`，也不得绕过 `QEXEC_ENABLE_LIVE=1` 等执行系统门禁。

## Cache And Alias Rules

允许存在但不能作为跨模块真源的内容：

- 子项目内部 `artifacts/`、`outputs/`、`.pytest_cache/`、`.ruff_cache/`。
- 为迁移保留的 alias、symlink、local report。
- 人工临时导出的 CSV / JSON。

如果某份文件需要被其他模块稳定消费，应提升为：

1. 子项目文档化的输出。
2. current contract 或 registry 可发现的资产。
3. 显式版本化的 release / archive artifact。

## Top-Level Checks

顶层检查脚本只验证 workspace 层契约：

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
```

这些脚本不能代替子项目测试，也不能把业务参数搬到顶层。
