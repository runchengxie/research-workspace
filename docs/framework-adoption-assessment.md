# 量化平台框架采用评估

> status: reference
> owner: workspace
> last_verified: 2026-07-19
> source_of_truth: no
> decision: [ADR-0001](adr/0001-framework-integration-boundaries.md)
> current_status: [外部框架支持矩阵](framework-support-matrix.md)

本文记录 `research-workspace` 与六个子模块对 Qlib、QuantConnect LEAN、vn.py 和 Backtrader 的采用取舍。当前实现状态以支持矩阵为准。

## 结论

平台继续维护 A 股领域核心，并通过窄适配器使用成熟框架。当前边界如下：

- `market-data-platform` 维护数据资产、PIT 语义、版本和来源链路
- `alpha-research` 维护防泄漏、研究证据、晋级规则和标准信号产物
- `portfolio-backtester` 维护 A 股可交易性、费用、容量和确定性回放
- `research-apps` 组合职责仓接口并运行策略专用研究应用
- `strategy-pipeline` 维护配置、调用顺序、运行回执和目标导出
- `quant-execution-engine` 维护审批、风控、幂等、持久日志和对账

Qlib 适合数据读取、研究生命周期和差分回测。vn.py 适合执行传输层。LEAN 适合领域模型和独立对照场景。Backtrader 暂时只保留评估入口。

截至 2026-07-19，只有数据平台的 Qlib `DataLoader` 适配器进入当前 `main`。alpha、回测和执行仓库已经有框架中立接口，外部适配器仍需按各职责仓的当前命名空间重新落地。LEAN 与 Backtrader 当前没有可运行集成。

## 采用范围

| 能力 | 平台职责仓 | 外部框架的角色 |
| --- | --- | --- |
| 原始数据、时间点（PIT）和资产发布 | `market-data-platform` | Qlib 只读消费已发布资产 |
| Dataset、Trainer 和 Recorder | `alpha-research` | Qlib 可作为后续可选后端 |
| 组合对称交叉验证（CPCV）、回测过拟合概率（PBO）和晋级证据 | `alpha-research` | 保留平台规则 |
| A 股确定性回放 | `portfolio-backtester` | Qlib 可做差分基线，LEAN 可做独立场景 |
| 通用事件回测 | 暂无职责仓扩张计划 | Backtrader 只在证明维护收益后评估 |
| Gateway、实时事件和基础 订单管理系统（OMS） | `quant-execution-engine` 传输层边界 | vn.py 可作为后续可选传输层 |
| 审批、幂等、日志和对账 | `quant-execution-engine` | 保留平台控制面 |
| 研究应用组合 | `research-apps` | 只通过职责仓接口间接使用后端 |
| 编排、回执和目标导出 | `strategy-pipeline` | 不直接加载框架运行时 |

## 值得保留的领域能力

### 数据和市场语义

数据平台负责数据源规划、分区检查、资产生成、发布回执、资产登记表和当前指针。这些能力决定 PIT 语义、版本身份和恢复路径。Qlib 适配器只读取已经发布的资产，不能写资产登记表或改变当前指针。

### 研究可信度

alpha 层的 CPCV、PBO、数据剔除（purging）、隔离窗口（embargo）、时间与截面泄漏检查、特征证据和晋级门禁属于平台规则。外部框架可以完成训练和实验记录，晋级结论仍由平台证据决定。

### A 股回放

原生回放继续定义停牌、涨跌停、T+1、整手、费用、缺失价格、延迟退出、流动性和容量语义。差分报告需要把差异定位到日期、持仓、换手、成本或损益。

### 执行控制面

执行引擎继续拥有目标校验、审批、下单前检查、紧急停止、幂等、持久事件日志、审计证据和对账。vn.py 后续可以提供 Gateway 生命周期和券商回报。券商事实需要转换成平台自己的事件和成交类型后再持久化。

## 停止扩张的通用能力

- 通用 Dataset、Trainer 和 Recorder
- 市场无关的 Top-K、事件回测和订单模拟器
- 通用 Gateway 和 OMS
- 在编排层重复实现数据、模型、组合或券商逻辑

新增这类能力前，应先评估职责仓接口或成熟框架能否承担，并说明新增代码会替换哪些维护面。

## 框架采用条件

外部适配器需要同时满足以下条件：

1. 未安装可选依赖时，原生路径仍可导入、测试和运行。
2. 同一固定样例能生成机器可读差分报告。
3. PIT、泄漏、晋级、审批和日志门禁不会被绕过。
4. 第三方类型不会进入公开结果、元数据或跨仓库产物。
5. 已记录框架版本、输入哈希、配置哈希、故障证据和回滚方法。
6. 标准门禁明确区分真实运行时测试和跳过的条件化测试。
7. 新适配器带来的维护成本低于被替换的通用实现。

## 后续顺序

1. 为数据平台增加显式 Qlib 验证档位，安装 `qlib` extra 并禁止真实运行时测试静默跳过。
2. 评估是否按当前 `alpha_research` 命名空间重新实现 Qlib `Dataset`、`Trainer` 和 `Recorder` 适配器。
3. 补齐 portfolio 原生 A 股规则和容量场景，再决定 Qlib 差分与 LEAN 文件化对照是否值得恢复。
4. 根据目标券商能力缺口决定是否按当前 qexec 边界恢复 vn.py 影子模式和模拟传输层。
5. Backtrader 在出现明确用例前保持规划状态。
6. `strategy-pipeline` 和 `research-apps` 继续只消费职责仓接口。

## 暂缓事项

- 整体迁移到 Qlib、LEAN、vn.py 或 Backtrader
- 同时维护多套完整研究框架
- 为尚未确认的全球多资产需求引入完整 LEAN 运行时
- 在职责清理完成前向编排层增加研究算法或券商行为
- 在真实运行时差分和恢复测试通过前删除原生路径

当前状态和证据路径见 [外部框架支持矩阵](framework-support-matrix.md)。长期约束见 [ADR-0001](adr/0001-framework-integration-boundaries.md)。历史候选批次见 [外部框架适配器候选发布](framework-adapter-release.md)。
