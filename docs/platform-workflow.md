# 平台工作流与集成边界

本页说明 `research-workspace` 中活跃模块怎样衔接，以及哪些步骤已经验证。顶层仓库负责锁定一组可以一起使用的版本，并说明模块之间的文件交接方式。

## 当前工作流

截至 2026-07-19，工作区已经锁定并验证到研究结果交给执行引擎生成离线计划这一段：

```text
策略身份、投资假设和生命周期
  -> 数据维护和盘口加工
  -> 发布共享数据资产
  -> alpha 研究、模型评估和信号产物
  -> 组合构造、回测和持仓候选
  -> 研究应用组合 owner API 并返回 frames/report
  -> 策略编排和目标文件导出
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

当前 `strategy-pipeline` 可以导出标准格式的 `targets.json` 和对应审计文件。
`quant-execution-engine` 已固定为工作区子模块，用于复现文件交接和离线计划验证。
模拟盘、实盘和运行门禁仍由执行引擎负责。

A 股就绪度分成 `baseline_reproducible`、`complete_pit_research_data`、
`production_strategy_evidence` 和 `broker_trading_enabled` 四档。当前只确认第一档。完整时间点（PIT）、
长窗口策略证据和真实券商能力必须独立验收。

## 八段式研究地图

| 阶段 | 所有者 | 稳定对象 / 文件 |
| --- | --- | --- |
| 策略知识 | `strategy-research` | `catalog.json`、策略说明、生命周期与证据导航 |
| 数据文件约定 | `market-data-platform` | `metadata/current_assets/a_share_current.json`、清单、registry |
| 研究数据集 | `market-data-platform` / `alpha-research` | 已发布资产、`ResearchDataset`：`raw_panel -> infer_frame -> learn_frame` |
| L2 深度学习研究 | `deep-learning-tick-data-prediction` | 清洁审计、事件流模型和 formal prediction artifact |
| 模型 | `alpha-research` | `ResearchModel.detail()`、`feature_importance.csv`、`model_detail` summary |
| 信号 | `alpha-research` | `signals.parquet` |
| 组合 | `portfolio-backtester` | 组合规格、`positions_by_rebalance.csv`、`positions_current*.csv` |
| 策略应用 | `strategy-app` | 策略特有纯计算、冻结合同与普通 frames/report |
| 执行交接 | `strategy-pipeline` -> `quant-execution-engine` | `targets.json`、`targets.json.lineage.json`、`qexec rebalance` |

## 模块分工

| 层级 | 模块 | 职责 | 当前接口 |
| --- | --- | --- | --- |
| 策略知识 | `strategy-research` | 维护策略身份、假设、生命周期、评审结论和证据导航 | `strategy-research/catalog.json`、策略 README |
| 数据平台入口 | `market-data-platform` | 维护共享路径、当前数据清单和资产索引，承载中国大陆市场数据入口、A 股资产发布和港股归档恢复控制面 | `marketdata tushare ...`、`marketdata migration hydrate-hk` |
| Alpha 研究 | `alpha-research` | 承载特征、模型、CPCV/PBO、feature evidence、signal artifact 和 alpha 诊断 | `alpha_research.*`、`signals.parquet` |
| L2 深度学习研究 | `deep-learning-tick-data-prediction` | 承载 L2 清洁、事件级标签、模型训练和预测 artifact | `ticknet.research.prediction_contract`、版本化 prediction artifact |
| 组合回测 | `portfolio-backtester` | 承载组合构造、回测、执行模拟、容量、暴露、turnover 和报告 | `portfolio_backtester.*`、`positions_by_rebalance.csv`、`positions_current*.csv` |
| 策略应用 | `strategy-app` | 把人类可读策略规格翻译为策略特有纯计算，组合 owner API，不负责最终发布 | `strategy_app.*`、普通 frames/report |
| 运行控制面 | `strategy-pipeline` | 负责命令行（CLI）、外部调用、运行目录、操作控制、原子发布、门禁和执行目标导出 | `strategy ...`、`summary.json`、`targets.json` |
| 交易执行（可选） | `quant-execution-engine` | 读取目标持仓文件，连接券商执行调仓、对账和异常恢复 | `qexec rebalance <targets.json>` |

## 研究完整性和防过拟合边界

活跃子模块共同覆盖研究完整性，但职责不同：

| 层级 | 仓库 | 负责的防线 | 文档入口 |
| --- | --- | --- | --- |
| 数据防泄漏 | `market-data-platform` | current 契约、清单、PIT universe、PIT fundamentals、历史行业、research validation、current health 和 release evidence | [`market-data-platform/docs/research-integrity.md`](../market-data-platform/docs/research-integrity.md) |
| Alpha 防过拟合 | `alpha-research` | time-series CV、rolling / walk-forward、final 样本外（OOS）、组合对称交叉验证（CPCV）、数据剔除（purging）/隔离窗口（embargo）、feature evidence、DSR、promotion gate 和候选晋升证据 | [`alpha-research/README.md`](../alpha-research/README.md) |
| 回测稳健性 | `portfolio-backtester` | turnover/cost、capacity、benchmark ladder、execution simulation、exposure 和报告复核 | [`portfolio-backtester/README.md`](../portfolio-backtester/README.md) |
| 策略知识边界 | `strategy-research` | 生命周期与证据导航不成为运行时依赖 | [`strategy-research/README.md`](../strategy-research/README.md) |
| 应用组合边界 | `strategy-app` | 只承载策略特有计算并组合 owner API，不进行最终发布 | [`strategy-app/README.md`](../strategy-app/README.md) |
| 执行隔离和审计 | `quant-execution-engine` | 标准 `targets.json` 输入、dry-run / paper / live 分层、风控预检、订单审计、对账和 evidence bundle | [`quant-execution-engine/docs/research-handoff-governance.md`](../quant-execution-engine/docs/research-handoff-governance.md) |

数据平台不读取研究运行指标。研究仓库不生产市场数据资产，也不提交券商订单。
执行引擎不重新评估模型，也不把 lineage sidecar 作为下单参数。这些边界用于隔离
数据发布、模型选择和真实执行。

## 研究主线

当前研究主线是 A 股。中国香港市场数据资产放在独立冷存储中，主要用于历史恢复和
复现。工作区内的公开港股演示路线和独立港股研究线已经退役。保留边界见
[`hk-public-split-manifest.yml`](hk-public-split-manifest.yml) 和
[`archive/hk/README.md`](archive/hk/README.md)。市场生命周期以
`strategy-pipeline/docs/market-lifecycle.md` 为准。

当前执行顺序见 [data-transition-playbook.md](data-transition-playbook.md)。活跃
`DATA_PLATFORM_ROOT` 保留 A 股 current 契约、资产和 registry。港股需要复现时先
执行 hydrate。A 股主线使用 `default`，`default_next` 只保留迁移兼容用途。完整 PIT、
长窗口证据和券商能力继续按就绪度分层验收。

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

`market-data-platform` 已提供中国大陆市场数据入口、统一维护命令、A 股资产发布和
港股冷存储恢复控制面。A 股研究优先读取
`metadata/current_assets/a_share_current.json` 指向的已发布资产。分钟资产还要携带
供应商、来源层级和 bar coverage，用于区分 Guan 与 TuShare 数据阶段。港股冷存储位置
由 `metadata/frozen_markets/hk.json` 记录，需要复现时再恢复。

共享数据运维的新入口进入 `market-data-platform`。`strategy-pipeline` 只保留只读消费
逻辑和少量兼容包装。边界清单见
`strategy-pipeline/docs/internal/data-ops-boundary-inventory.md`。

### 2. 读取数据并完成研究

`strategy-research` 先给出策略身份和证据边界。运行时通过 `market-data-platform`、
`alpha-research`、`portfolio-backtester` 和 `strategy-app` 完成纯计算。`strategy-pipeline`
负责数据提供方（provider）调用、操作员控制、运行目录、原子发布和 target 交接。A 股主入口是 `strategy run --config default`。
`default_next` 是同一 A 股 preset 的迁移兼容别名。分钟因子、DailyWatch20、
错峰（staggered）队列和热点 AI shadow 目前属于 research-only campaign，不能直接修改
线上模型或执行目标。港股只用于历史恢复。

- 特征工程、训练与评估。
- 历史回测、基准对比和研究证据管理。
- 当前持仓、快照和执行前资金 / 手数分配输出。
- 使用 `strategy-pipeline export-targets` 导出执行引擎可读取的 `targets.json`，并保留审计附属文件。

### 3. 锁定可复现组合

当数据约定、盘口工具、策略版本和执行接口共同验证后，顶层仓库通过子模块提交指针锁定这组组合。数据本体仍保存在发布目录、归档介质或发布资产中，不写入顶层 Git 历史。

## 可选执行链路

### 当前接入程度

研究侧先由 owner adapter 生成通用 `holdings.json`，再通过 `strategy-pipeline export-targets` 导出标准 `targets.json`。导出器会拒绝空头持仓、非法权重和隐式杠杆，并把运行编号、输入文件和目标哈希写入审计附属文件。

执行引擎已经作为固定子模块纳入工作区。当前已用真实研究导出文件验证了解析逻辑、
离线调仓计划和目标列表以外持仓的清仓处理。非 USD 报价资产需要先配置汇率并换算至
USD 估值。A 股基础 dry-run 仍需显式配置 CNY 汇率。

仍需补齐的证据：

- 使用真实模拟盘凭证形成的端到端持续联调记录。
- 任何实盘自动化下单记录。

当前约束：

- README 和子模块指针只表达已验证的研究到执行文件交接。
- `export-targets` 只导出文件。顶层脚本不得把研究结果直接提交给真实券商。
- 模拟盘或实盘路径的放行状态以执行仓库的券商证据和操作员记录为准。

### 执行放行门槛

| 门槛 | 当前状态 |
| --- | --- |
| 目标持仓文件 | 已落地：研究侧输出 `quant-execution-engine.targets/v2` 格式的 `targets.json` |
| 导出能力 | 已落地：`strategy-pipeline export-targets` 输出目标文件和审计附属文件 |
| 输入验证 | 已落地：执行侧可读取真实导出文件，港股和 A 股目标可生成基础计划，缺少汇率时会阻断非 USD 调仓 |
| 联调证据 | 部分落地：已具备解析和离线计划验证，仍需模拟盘端到端验证记录 |
| 实盘门禁 | 实盘下单仍要求执行引擎独立启用、执行前检查和人工监督 |

## 调度原则

当前阶段先稳定模块间文件约定和执行顺序。未来如果跨模块流程已经稳定，并且需要经常统一执行，顶层编排层应保持很薄：

1. 只调用各模块公开命令行。
2. 每一步检查版本化输入、当前数据清单和输出状态。
3. 将运行编号、输入资产版本、子模块提交和质量检查结论写入审计记录。
4. 数据维护与研究可以被编排。真实券商执行必须由执行系统自己的门禁和人工确认控制。

## 推荐阅读

| 主题 | 文档 |
| --- | --- |
| 数据控制面与迁移顺序 | [`market-data-platform/docs/README.md`](../market-data-platform/docs/README.md) |
| 策略研究主流程 | [`strategy-research/README.md`](../strategy-research/README.md)、[`strategy-app/docs/research/README.md`](../strategy-app/docs/research/README.md)、[`strategy-pipeline/docs/control-plane.md`](../strategy-pipeline/docs/control-plane.md) |
| A 股研究基线 | [`strategy-app/docs/playbooks/a-share-baseline.md`](../strategy-app/docs/playbooks/a-share-baseline.md) |
| 共享中国香港市场数据边界 | [`market-data-platform/docs/operations/hk-archive-restore.md`](../market-data-platform/docs/operations/hk-archive-restore.md) |
| 盘口资产处理工作流 | [`market-data-platform/README.md`](../market-data-platform/README.md) |
| 独立研究应用 | [`strategy-app/README.md`](../strategy-app/README.md) |
| 策略身份与生命周期 | [`strategy-research/README.md`](../strategy-research/README.md) |
| 可选交易执行系统 | [`quant-execution-engine`](../quant-execution-engine/README.md) |
| 顶层初始化与检查 | [`bootstrap.md`](bootstrap.md)、[`contracts.md`](contracts.md)、[`release-checklist.md`](release-checklist.md)、[`version-matrix.md`](version-matrix.md) |
