# 平台工作流与集成边界

本页说明 `research-workspace` 中三个模块怎样衔接，以及哪些步骤已经验证。顶层仓库负责锁定一组可以一起使用的版本，并说明模块之间的文件交接方式。

## 当前工作流

截至 2026-06-01，工作区已经锁定并验证到研究结果交给执行引擎生成离线计划这一段：

```text
数据维护和盘口加工
  -> 发布共享数据资产
  -> 策略研究、模型评估和回测
  -> 导出 targets.json
  -> 执行引擎解析文件并生成离线调仓计划
```

券商执行属于后续可选流程：

```text
targets.json
  -> 执行前检查
  -> 模拟盘验证
  -> 显式开启实盘门禁
  -> 券商执行
```

当前 `cross-sectional-trees` 已经可以导出标准格式的 `targets.json` 和对应审计文件；`quant-execution-engine` 已经固定为工作区子模块，用于复现文件交接和离线计划验证。模拟盘、实盘和运行门禁仍由执行引擎自己负责。

A 股就绪度分成 `baseline_reproducible`、`complete_pit_research_data`、
`production_strategy_evidence` 和 `broker_trading_enabled` 四档。当前只确认第一档；完整 PIT、
长窗口策略证据和真实券商能力必须独立验收。

## 六段式研究地图

| 阶段 | 所有者 | 稳定对象 / 文件 |
| --- | --- | --- |
| 数据文件约定 | `market-data-platform` | `metadata/current_assets/a_share_current.json`、manifest、registry |
| 研究数据集 | `cross-sectional-trees` | `ResearchDataset`：`raw_panel -> infer_frame -> learn_frame` |
| 模型 | `cross-sectional-trees` | `CSTreeModel.detail()`、`feature_importance.csv`、`model_detail` summary |
| 信号 | `cross-sectional-trees` | `signals.parquet` |
| 组合 | `cross-sectional-trees` | named `StrategySpec`、`positions_current*.csv` |
| 执行交接 | `cross-sectional-trees` -> `quant-execution-engine` | `targets.json`、`targets.json.lineage.json`、`qexec rebalance` |

## 模块分工

| 层级 | 模块 | 职责 | 当前接口 |
| --- | --- | --- | --- |
| 数据平台入口 | `market-data-platform` | 维护共享路径、当前数据清单和资产索引；承载中国大陆市场数据入口、A 股资产发布和港股归档 freeze / hydrate 恢复控制面 | `marketdata tushare ...`、`marketdata migration hydrate-hk` |
| 策略研究 | `cross-sectional-trees` | 只读消费发布数据，完成特征、模型、评估、回测、持仓分配和执行目标导出；港股只作为历史归档复现入口 | `summary.json`、`positions_current*.csv`、`targets.json` |
| 交易执行（可选） | `quant-execution-engine` | 读取目标持仓文件，连接券商执行调仓、对账和异常恢复 | `qexec rebalance <targets.json>` |

## 研究主线

当前工作区政策是：A 股作为后续研究主线迁移方向；中国香港市场数据资产整体移入独立冷存储，以冻结维护和可复现归档为主；港股策略研究从默认入口降级为历史研究线，并通过 [`hk-research-lane-inventory.json`](hk-research-lane-inventory.json) 记录独立研究线候选、迁出动作和保留边界。具体 default 切换、港股 frozen-active / sunset 条件以 `cross-sectional-trees/docs/market-lifecycle.md` 为准。

当前执行顺序见 [data-transition-playbook.md](data-transition-playbook.md)：活跃 `DATA_PLATFORM_ROOT` 保留 A 股 contract、资产和 registry；港股需要复现或明确跟踪时先 hydrate；A 股继续用 `daily_clean` / `default_next` 做 staged baseline。切换 `default` 到 A 股前，先满足验收条件。

### 1. 发布数据资产

共享数据放在版本化资产目录中，并由当前数据清单指向推荐版本：

```text
<artifacts_root>/
  assets/
  metadata/
    current_assets/
      a_share_current.json
    frozen_markets/
      hk.json
    dataset_registry.csv
  reports/
```

`market-data-platform` 已经提供中国大陆市场数据入口、统一维护命令、A 股资产发布和港股冷存储 freeze / hydrate 恢复控制面。A 股主线迁移应优先读取 `metadata/current_assets/a_share_current.json` 指向的 TuShare 平台资产；港股长期不使用时由 `metadata/frozen_markets/hk.json` 记录冷存储位置，需要复现时再恢复。港股 provider 生产模块和 `rqdata-hk-depth-snapshots` 均不作为活跃工作区入口。

共享数据运维的新入口必须进入 `market-data-platform`。`cross-sectional-trees` 仅保留只读消费逻辑和少量兼容 wrapper；其边界清单由 `cross-sectional-trees/docs/internal/data-ops-boundary-inventory.md` 维护，下载、健康检查、current refresh、registry 或资产发布实现不应回流到研究仓库。

### 2. 读取数据并完成研究

`cross-sectional-trees` 从当前数据清单解析已发布数据资产，再完成研究流程。A 股迁移候选入口是 `cstree run --config default_next`；港股只用于 restore-only 历史复现，不作为新增研究默认入口。

- 特征工程、训练与评估。
- 历史回测、基准对比和研究证据管理。
- 当前持仓、快照和执行前资金 / 手数分配输出。
- 使用 `cstree export-targets` 导出执行引擎可读取的 `targets.json`，并保留审计附属文件。

### 3. 锁定可复现组合

当数据约定、盘口工具、策略版本和执行接口共同验证后，顶层仓库通过子模块提交指针锁定这组组合。数据本体仍保存在发布目录、归档介质或发布资产中，不写入顶层 Git 历史。

## 可选执行链路

### 当前接入程度

研究侧可以通过 `cstree export-targets` 将 `positions_current*.csv` 或已保存持仓导出为标准 `targets.json`。导出器会拒绝空头持仓、非法权重和隐式杠杆，并把运行编号、输入文件、时间口径和质量检查信息写入审计附属文件。

执行引擎已经作为固定子模块纳入工作区。当前已用真实研究导出文件验证了执行引擎的解析逻辑和离线调仓计划路径，包括目标列表以外持仓的清仓处理。港股等非 USD 报价需要先配置汇率并换算至 USD 估值；A 股目标解析和基础 dry-run 仍应显式配置 CNY 汇率。

仍需补齐的证据：

- 使用真实模拟盘凭证形成的端到端持续联调记录。
- 任何实盘自动化下单记录。

当前约束：

- README 和子模块指针只表达已验证的研究到执行文件交接。
- `export-targets` 只导出文件；顶层脚本不得把研究结果直接提交给真实券商。
- 模拟盘或实盘路径的放行状态以执行仓库的券商证据和操作员记录为准。

### 执行放行门槛

| 门槛 | 当前状态 |
| --- | --- |
| 目标持仓文件 | 已落地：研究侧输出 `quant-execution-engine.targets/v2` 格式的 `targets.json` |
| 导出能力 | 已落地：`cstree export-targets` 输出目标文件和审计附属文件 |
| 输入验证 | 已落地：执行侧可读取真实导出文件；港股和 A 股目标可生成基础计划；缺少汇率时会阻断非 USD 调仓 |
| 联调证据 | 部分落地：已具备解析和离线计划验证；仍需模拟盘端到端验证记录 |
| 实盘门禁 | 实盘下单仍要求执行引擎独立启用、执行前检查和人工监督 |

## 调度原则

当前阶段先稳定模块间文件约定和执行顺序。未来如果跨模块流程已经稳定，并且需要经常统一执行，顶层编排层应保持很薄：

1. 只调用各模块公开命令行。
2. 每一步检查版本化输入、当前数据清单和输出状态。
3. 将运行编号、输入资产版本、子模块提交和质量检查结论写入审计记录。
4. 数据维护与研究可以被编排；真实券商执行必须由执行系统自己的门禁和人工确认控制。

## 推荐阅读

| 主题 | 文档 |
| --- | --- |
| 数据控制面与迁移顺序 | [`market-data-platform/docs/README.md`](../market-data-platform/docs/README.md) |
| 策略研究主流程 | [`cross-sectional-trees/docs/pipeline-overview.md`](../cross-sectional-trees/docs/pipeline-overview.md)、[`cross-sectional-trees/docs/market-lifecycle.md`](../cross-sectional-trees/docs/market-lifecycle.md) |
| A 股迁移候选 | [`cross-sectional-trees/docs/playbooks/a-share-baseline.md`](../cross-sectional-trees/docs/playbooks/a-share-baseline.md) |
| 共享中国香港市场数据边界 | [`cross-sectional-trees/docs/concepts/shared-hk-data-platform.md`](../cross-sectional-trees/docs/concepts/shared-hk-data-platform.md) |
| 盘口资产处理工作流 | [`market-data-platform/README.md`](../market-data-platform/README.md) |
| 可选交易执行系统 | [`quant-execution-engine`](../quant-execution-engine/README.md) |
| 顶层初始化与检查 | [`bootstrap.md`](bootstrap.md)、[`contracts.md`](contracts.md)、[`release-checklist.md`](release-checklist.md)、[`version-matrix.md`](version-matrix.md) |
