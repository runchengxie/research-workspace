# 量化平台框架采用评估

> status: reference
> owner: workspace
> last_verified: 2026-07-13
> source_of_truth: no
> decision: [ADR-0001](adr/0001-framework-integration-boundaries.md)

本文记录 `research-workspace` 与五个 submodule 对 Qlib、QuantConnect LEAN 和 vn.py 的
采用判断。评分用于安排迁移优先级，不代表代码质量，也不替代各仓库的测试和能力矩阵。

## 结论

平台应继续自研，但自研范围收敛到领域核心：

- A 股数据融合、PIT 语义、资产版本、lineage 和 promotion；
- CPCV/PBO、泄漏防护、研究 evidence 和 promotion gate；
- A 股可交易性、费用、容量和确定性 position replay；
- artifact contract、审批、policy、幂等、持久 journal、evidence 和 reconciliation。

通用底座停止扩张：

- Qlib 作为可选 Dataset、DataHandler、Model、Recorder 和差分回测后端；
- vn.py 作为可选 Gateway、事件和 OMS transport；
- LEAN 只提供领域模型参照与独立 golden scenario，不进入当前 Python runtime。

这不是整体迁移，也不是继续并行维护三套完整框架。第三方对象只能存在于 adapter 内部，跨仓库
边界仍使用平台自己的 schema、类型和 artifact。

## 模块评价

重复建设风险衡量与成熟开源框架的功能重合，维护风险衡量当前职责数量、状态空间和故障成本。
五分代表最高。

| 模块 | 重复建设风险 | 维护风险 | 判断 |
| --- | ---: | ---: | --- |
| `market-data-platform` | 1.5 | 4.0 | 领域价值明确，保留资产生产权威；通过只读 adapter 服务 Qlib |
| `alpha-research` | 3.5 | 3.5 | 研究治理保留，通用 Dataset、Trainer 和 Recorder 建立 Qlib 后端 |
| `portfolio-backtester` | 3.5 | 4.0 | 保留 A 股确定性回放，通用基线用 Qlib，LEAN 只做文件化对照 |
| `strategy-pipeline` | 4.5 | 4.5 | 重复和职责漂移最明显，应冻结新增算法并收敛到薄编排 |
| `quant-execution-engine` | 3.5 | 4.5 | 控制面价值高，Gateway、事件分发和基础 OMS 优先接 vn.py |
| superproject | 2.5 | 3.0 | 作为 integration BOM 合理，应完成阶段 4 并停止新增 runtime helper |

当前多仓库结构是有明确退出清单的阶段 3 过渡态。三个 Python distribution 已迁到各自的
owner-native namespace，不再共享 `cstree` namespace；`strategy-pipeline` 仅为 1.x 兼容窗口
单独持有 `cstree` facade。编排层 runtime helper 的职责收敛仍未全部完成，但已有 canonical owner、
artifact handoff 和阶段 4 closure checklist，不能简单定性为无意识形成的分布式单体。风险在于
剩余过渡态长期化，而不是物理拆仓本身。

## 值得保留的领域资产

### 数据和市场语义

`market-data-platform` 负责 source planning、fetch、partition validation、source fusion、asset
materialization、promotion receipt、registry 和 current pointer。这些能力解决数据源差异、PIT、
版本发布和恢复问题，Qlib Data Layer 不能替代其 system-of-record 职责。

Qlib adapter 只读取已经发布的 manifest 和资产。它不得写 registry、改变 current pointer、绕过
calendar/PIT 校验或把 Qlib 本地数据目录提升为权威来源。

### 研究可信度

`alpha-research` 的 CPCV、PBO、purging/embargo、时间与截面泄漏检查、feature evidence、
稳健性诊断和 promotion gate 是平台差异化能力。外部框架可以执行模型训练和记录实验，不能替平台
决定哪些 evidence 足以进入 backtest 或 live。

### A 股回放

native replay 继续定义停牌、涨跌停、T+1、最小手数、费用、缺失价格、延迟退出、流动性和容量
语义。Qlib 或 LEAN 结果可以不同，但差异必须归类到明确的日期、持仓、换手、成本或 PnL 语义。

### 执行控制面

qexec 继续拥有目标验证、审批、policy、preflight、kill switch、intent idempotency、持久事件
journal、审计 evidence 和 reconciliation。vn.py 的实时内存状态不是审计权威来源；broker 事实
必须转换成 qexec 自有 `OrderEvent`、`Fill` 和对账证据后持久化。

## 明确的重复建设区域

### 研究生命周期

平台的 raw / infer / learn 数据生命周期与 Qlib 的 `DK_R` / `DK_I` / `DK_L` 语义高度重合。
继续另建通用 Processor、Dataset、Model interface 和 Experiment/Recorder 会扩大重复维护面。
适合采用 backend port，保留平台的 PIT 和 leakage processor 为 canonical owner。

### 通用 Top-K 和回测基线

Top-K、调仓、换手、成本和基础 executor 在 Qlib 与 LEAN 中已有成熟表达。native 代码只有在提供
A 股特定语义或确定性 artifact replay 时才应继续扩张。通用多资产事件驱动引擎和通用订单模拟器
不进入当前路线。

### 编排层内部重算

`strategy-pipeline` 同时出现 panel loading、fundamentals enrichment、evaluation、tuning、
portfolio/live holdings 和 output packaging。这些职责分别已有数据、alpha、portfolio 和 execution
owner。编排层只保留配置合成、owner 调用、run receipt、artifact promotion 和纯 target export。

### Gateway、事件和基础 OMS

连接生命周期、合约查询、broker callback、订单缓存、撤单竞态、断线重连和账户/持仓归一化是
vn.py 的强项，也是实盘中故障成本最高的重复建设。qexec 不再新增通用 Gateway；特定 direct
adapter 只有在 vn.py 不支持目标 broker 或存在可量化能力缺口时保留。

## 框架职责矩阵

| 能力 | 平台 owner | Qlib | LEAN | vn.py |
| --- | --- | --- | --- | --- |
| 原始数据、PIT、资产发布 | `market-data-platform` | 只读消费 | 不采用 | 不采用 |
| Dataset、Processor、Trainer | `alpha-research` contract | 可选后端 | 不采用 | 暂不采用 `vnpy.alpha` |
| CPCV/PBO、promotion | `alpha-research` | 产生输入证据 | 不采用 | 不采用 |
| A 股确定性 replay | `portfolio-backtester` | 差分基线 | golden scenario | 不采用 |
| Portfolio/Risk/Execution 语言 | 平台 contract | 参考 | 主要设计参照 | transport 映射 |
| Gateway、实时事件、基础 OMS | qexec transport port | 不采用 | 不采用 | 可选后端 |
| 审批、幂等、journal、对账 | `quant-execution-engine` | 不采用 | 不采用 | 只提供 broker facts |
| 编排、receipt、target export | `strategy-pipeline` | 通过 owner 调用 | 不采用 | 不直接调用 |

`vnpy.alpha` 当前不作为第二个研究后端。若未来评估，必须证明它能删除现有通用实现，并保持
artifact-first 边界；技术栈统一本身不是采用理由。

## 领域对象边界

跨仓库链路使用以下概念，不复用第三方 runtime type：

```text
SignalArtifact
  -> PortfolioTarget
  -> RiskDecision
  -> ApprovedTarget
  -> OrderIntent
  -> BrokerOrderEvent / Fill
  -> ReconciliationResult
```

研究目标与订单意图是不同契约。研究层表达证券和目标权重或数量；执行层结合账户、现金、现有持仓、
手数、价格、有效期和 policy 生成 `OrderIntent`。target exporter 不连接 broker，也不携带
`order_type` 等 transport 决策。

## 采用和删除门槛

外部 adapter 只有满足以下条件才可替换 native 通用实现：

1. 不安装 optional dependency 时，native 路径仍可导入、测试和运行。
2. 同一 fixture 可生成机器可读差分报告，差异有 owner 和 explanation。
3. PIT、leakage、promotion、审批和 journal 门禁没有被 adapter 绕过。
4. framework object 没有进入公共 result、metadata 或 artifact schema。
5. 已记录版本、输入 hash、配置 hash、回滚方法和故障证据。
6. 删除的通用实现和维护面显著多于新增 adapter；否则只形成额外依赖层。

达到 parity 不代表必须逐行删除 native 实现。A 股 golden semantics、离线恢复路径和小型 deterministic
replay 可以长期保留。删除决定以维护收益、运行证据和 rollback cost 为准。

## 实施顺序

### 第一阶段：固定边界和迁移缝隙

- 接受 ADR、artifact envelope v2 和 framework-neutral ports。
- 保持 native 默认，冻结新的通用 Dataset、Recorder、Gateway、OMS 和 event backtester。
- 把 typed target、intent、event、幂等和 journal 先于 transport 接入。

### 第二阶段：建立真实 parity evidence

- published asset 到 Qlib DataLoader/DataHandler 的只读映射；
- native 与 Qlib 的 Dataset、Trainer、prediction 和 recorder 对照；
- native/Qlib 回测差分与 LEAN 文件化 golden scenario；
- qexec paper transport conformance 和 vn.py shadow mode。

### 第三阶段：迁移 owner 并删除重复实现

- strategy-pipeline 委托 panel、enrichment、training、evaluation 和 portfolio owner；
- transport parity 与故障矩阵通过后，停止扩张并逐步删除重复 Gateway/OMS；
- compatibility facade 在登记的 removal release 到期后删除。

### 第四阶段：集成发布

- 下游 PR 先合并并发布 package version；
- superproject 更新 submodule pins、version matrix 和 compatibility matrix；
- 运行无 Qlib/vn.py 的 native smoke，以及启用 adapter 的 differential/shadow smoke；
- 保存 release evidence 和 rollback receipt。

## 暂不执行的事项

- 不整体迁移到 Qlib、LEAN 或 vn.py。
- 不新建第二套 contracts package；先强化现有 `src/research_contracts` 和
  `artifact-contracts.yml`，达到多仓库稳定复用条件后再评估独立发布。
- 不同时维护 native、Qlib 和 `vnpy.alpha` 三套完整研究框架。
- 不为未确认的全球多资产需求引入完整 LEAN runtime。
- 不在职责清理完成前向 `strategy-pipeline` 增加研究算法或 broker 行为。
- 不在 transport parity 通过前删除 qexec 现有路径或启用真实 vn.py 下单。

## 公开发布注意事项

许可证、公开 clone 策略和 proprietary provider 分层属于项目所有者决策。若目标是对外开源，应另行
完成许可证选择、无私有 submodule 的最小运行路径、sample data、公开 schema 和端到端 smoke。
本次框架采用决策不替项目所有者选择许可证。
