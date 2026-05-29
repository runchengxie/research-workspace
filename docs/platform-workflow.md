# 平台工作流与集成边界

本页说明 `research-workspace` 中四个模块怎样衔接，以及哪些步骤已经验证。顶层仓库负责锁定一组可以一起使用的版本，并说明模块之间的交接方式。

## 当前工作流

截至 2026-05-27，工作区已经锁定并验证到“研究结果交给执行引擎生成离线计划”这一段：

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

## 模块分工

| 层级 | 模块 | 职责 | 当前接口 |
| --- | --- | --- | --- |
| 数据平台入口 | `market-data-platform` | 维护共享路径、当前数据清单和资产索引；承载 CN 数据入口、HK tick-depth、HK RQData assets、健康检查、current refresh 和发布工作流 | `marketdata tushare ...`、`marketdata rqdata hk-{depth,assets} -- ...` |
| 策略研究 | `cross-sectional-trees` | 只读消费发布数据，完成特征、模型、评估、回测、持仓分配和执行目标导出；不再内置 HK 数据资产生产检查入口 | `summary.json`、`positions_current*.csv`、`targets.json` |
| 交易执行（可选） | `quant-execution-engine` | 读取目标持仓文件，连接券商执行调仓、对账和异常恢复 | `qexec rebalance <targets.json>` |

## 研究主线

### 1. 发布数据资产

共享数据放在版本化资产目录中，并由当前数据清单指向推荐版本：

```text
<artifacts_root>/
  assets/
  metadata/
    current_assets/
      hk_current.json
      cn_current.json
    dataset_registry.csv
  reports/
```

`market-data-platform` 已经提供 CN 数据入口、统一维护命令、HK tick-depth 原生实现，以及 HK 日线、PIT、估值、行业、intraday、current contract 检查和资产发布实现。港股盘口原始数据、健康检查、日频聚合、对账和打包由 `market_data_platform.hk_depth` 承载；HK RQData assets 由 `market_data_platform.hk_assets` 和 `market_data_platform.release_tools` 承载。`rqdata-hk-depth-snapshots` 已从本工作区 sunset，不再作为子模块追踪。

共享数据运维的新入口必须进入 `market-data-platform`。`cross-sectional-trees` 仅保留只读消费逻辑和少量兼容 wrapper；其边界清单由 `cross-sectional-trees/docs/internal/data-ops-boundary-inventory.md` 维护，避免下载、健康检查、current refresh、registry 或资产发布实现回流到研究仓库。

### 2. 读取数据并完成研究

`cross-sectional-trees` 从当前数据清单解析出已发布数据资产，然后完成：

- 特征工程、训练与评估。
- 历史回测、基准对比和研究证据管理。
- 当前持仓、快照和执行前资金 / 手数分配输出。
- 使用 `cstree export-targets` 导出执行引擎可读取的 `targets.json`，并保留审计附属文件。

### 3. 锁定可复现组合

当数据约定、盘口工具、策略版本和执行接口共同验证后，顶层仓库通过子模块提交指针锁定这组组合。数据本体仍保存在发布目录、归档介质或发布资产中，不写入顶层 Git 历史。

## 可选执行链路

### 当前接入程度

研究侧可以通过 `cstree export-targets` 将 `positions_current*.csv` 或已保存持仓导出为标准 `targets.json`。导出器会拒绝空头持仓、非法权重和隐式杠杆，并把运行编号、输入文件、时间口径和质量检查信息写入审计附属文件。

执行引擎已经作为固定子模块纳入工作区。当前已用真实研究导出文件验证了执行引擎的解析逻辑和离线调仓计划路径，包括目标列表以外持仓的清仓处理。港股等非 USD 报价需要先配置汇率并换算至 USD 估值。

仍需补齐的证据：

- 使用真实模拟盘凭证形成的端到端持续联调记录。
- 任何实盘自动化下单记录。

当前约束：

- README 和子模块指针只表达已验证的研究到执行文件交接。
- `export-targets` 只导出文件；顶层脚本不得把研究结果直接提交给真实券商。
- 执行引擎接入工作区，不代表模拟盘或实盘路径已经放行。

### 执行放行门槛

| 门槛 | 当前状态 |
| --- | --- |
| 目标持仓文件 | 已落地：研究侧输出 `quant-execution-engine.targets/v2` 格式的 `targets.json` |
| 导出能力 | 已落地：`cstree export-targets` 输出目标文件和审计附属文件 |
| 输入验证 | 已落地：执行侧可读取真实导出文件；港股目标可生成计划；缺少汇率时会阻断非 USD 调仓 |
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
| 策略研究主流程 | [`cross-sectional-trees/docs/pipeline-overview.md`](../cross-sectional-trees/docs/pipeline-overview.md) |
| 共享 HK 数据边界 | [`cross-sectional-trees/docs/concepts/shared-hk-data-platform.md`](../cross-sectional-trees/docs/concepts/shared-hk-data-platform.md) |
| 盘口资产处理工作流 | [`market-data-platform/README.md`](../market-data-platform/README.md) |
| 可选交易执行系统 | [`quant-execution-engine`](../quant-execution-engine/README.md) |
| 顶层初始化与检查 | [`bootstrap.md`](bootstrap.md)、[`contracts.md`](contracts.md)、[`release-checklist.md`](release-checklist.md)、[`version-matrix.md`](version-matrix.md) |
