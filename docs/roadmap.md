# 工作区路线图

> status: active
> owner: workspace
> last_verified: 2026-08-17
> source_of_truth: yes
> superseded_by: n/a

本页是 `research-workspace` 的路线图总账。它聚合数据、策略证据、跨仓库契约、架构边界、
回测会计、执行成熟度、外部框架和维护性工作。专项文档继续保存设计细节和机器可读记录，
工作区级的完成状态、优先级和下一步统一在本页判断。

## 状态口径

| 状态 | 含义 |
| --- | --- |
| `complete` | 验收条件已经满足，并有当前代码、测试或证据支持 |
| `in_progress` | 已有部分实现，仍有明确验收缺口 |
| `planned` | 已登记采用条件，尚未进入当前主线实施 |
| `continuous` | 由预算棘轮持续约束，不以一次性清零作为发布条件 |

发布检查清单和架构复核清单中的空复选框是每次发布都要重新执行的操作，不表示对应功能尚未实现。
归档执行计划中的待办也不进入本页，除非当前代码或机器账本仍能确认缺口存在。

## 当前未完成项目

| 编号 | 优先级 | 状态 | 负责方 | 项目 | 当前缺口 |
| --- | --- | --- | --- | --- | --- |
| D1 | P0 | `in_progress` | `market-data-platform` | A 股完整研究数据 | `normalized_fundamentals` current alias 仍为 `exists: false` |
| E1 | P0 | `in_progress` | `strategy-research`、workspace | 策略生命周期证据 | 五个有强制证据要求的策略尚无可被门禁读取的完整 evidence bundle |
| E2 | P0 | `in_progress` | data、alpha、portfolio、strategy owners | A 股长窗口晋级证据 | 长窗口最终样本外、成本压力和容量证据尚未形成当前可晋级组合 |
| C1 | P1 | `in_progress` | workspace、各产物 owner | Artifact Envelope v2 | 类型和兼容读取已落地，生产方采用仍不完整，共享包目前只在工作区本地使用 |
| B1 | P1 | `in_progress` | `strategy-app`、`strategy-pipeline`、owner repos | 跨仓公开 API 收口 | 依赖方向已经正确，仍有跨仓私有符号调用需要发布公开 owner API 后替换 |
| DOC1 | P1 | `in_progress` | workspace、各仓文档 owner | 说明文档归集 | 路线图总账已建立，架构、数据状态、策略目录、质量计划和契约说明仍需分批去重 |
| X1 | P1 | `in_progress` | `quant-execution-engine` | 执行证据成熟度 | 目标文件和离线计划已验证，模拟盘持续联调、完整报单证据和 A 股真实通道仍有缺口 |
| F1 | P2 | `in_progress` | `market-data-platform`、`alpha-research` | Qlib 条件化适配 | 当前源码已有适配器，标准开发门禁可能跳过真实 Qlib runtime，差分证据仍需补齐 |
| F2 | P2 | `planned` | `portfolio-backtester` | 回测差分后端 | 当前只有原生后端，Qlib 差分和 Backtrader 采用仍处于规划阶段 |
| F3 | P2 | `planned` | `quant-execution-engine` | vn.py 执行传输 | 当前只有框架中立券商边界，没有 vn.py extra、适配器或注册后端 |
| M1 | P2 | `continuous` | 各仓 owner | 维护性预算收敛 | 机器账本仍有 4 条未关闭主记录和 179 条未解决 accepted hotspot，均受棘轮预算约束 |
| R1 | P3 | `planned` | `strategy-research` | 概念级机器学习 Path C | M1 至 M6 尚未开始，先验证 H1 和 H2 再决定是否继续投入 |

## P0 验收顺序

### D1：发布完整研究数据

1. 发布 `normalized_fundamentals` 不可变资产和 latest alias。
2. 在 `a_share_current.json` 中确认该资产存在、清单可读且覆盖范围明确。
3. 复核 PIT 财务、历史行业和股票池的时间点语义，不用最新快照回填历史。

### E1：补齐策略 evidence bundle

当前以下策略有强制证据要求：

- `daily_watch20`
- `hotsector`
- `style_replica_a80_b20`
- `d11_h5_shadow`
- `dividend_growth_momentum`

每个策略需要在 `strategy-research/evidence/` 下提供与生命周期匹配的证据包。完成标准是：

```bash
python scripts/strategy_evidence_gate.py --strict
```

命令通过，`catalog.json` 的生命周期与证据结论一致。达到该条件后，再把严格检查接入发布门禁。

### E2：刷新长窗口晋级证据

按当前 A 股资产重新生成 benchmark matrix、walk-forward、CPCV、最终样本外、成本压力和容量报告。
证据必须引用当前数据清单、代码提交和配置哈希。短窗口基线不能替代长窗口晋级证据。

## P1 收口标准

### C1：统一跨仓库产物 envelope

- `signals`、`positions` 和 `targets` 的生产方可以选择写入 `research.artifact-envelope.v2`。
- 读取方继续兼容现有 v1 fixture。
- 时间戳、配置哈希、内容哈希和 lineage 由契约测试验证。
- 明确 `research-contracts` 的发布方式和消费范围，避免各仓复制 schema 实现。

### B1：只通过公开 owner API 跨仓调用

当前 import direction 和 source layout 门禁已经通过。后续应把跨仓调用的私有符号提升为有测试的公开 API，
再删除调用方对下划线符号的直接依赖。该项属于接口加固，不重新开启已完成的 R0 至 R6 物理拆分。

### X1：补齐执行成熟度证据

- 保存模拟盘提交、查询、成交或撤单、重启恢复和对账的连续证据。
- 对每个券商分别记录能力范围，避免用某个后端的证据推断其他后端。
- A 股真实报单需要独立的券商能力、账户权限、受监督冒烟、对账和 kill-switch 验收。

### DOC1：归集说明文档

文档碎片化清单、权威入口和分批动作见[文档归集与去重清单](documentation-consolidation.md)。
本轮先校正相互冲突的 roadmap 状态和文档导航，后续再处理动态数据、策略目录、质量审计和契约字段的重复说明。

## 已完成的主要里程碑

| 项目 | 状态 | 当前事实 |
| --- | --- | --- |
| ADR-0006 R0 至 R6 | `complete` | 仓库改名、策略目录、owner API 改向、通用能力归位、重复内容清理和控制面收口已经完成 |
| 会计与执行阶段 0 至 6 | `complete` | 框架中立契约、可选统一账本、成本拆分、市场规则、容量校准和复现元数据已经落地 |
| A 股日线、PIT 财务和历史行业 | `complete` | current contract 已发布对应资产，`normalized_fundamentals` 仍由 D1 单独跟踪 |
| 研究到执行文件交接 | `complete` | `strategy export-targets` 与 qexec 本地 dry-run 已通过基础契约验证 |
| 旧 owner facade 和共享命名空间 | `complete` | 旧包名、旧共享命名空间和策略 owner delegating facade 已退出活动运行时 |

会计路线图中仍保留企业行动真实数值、冲击与融资模型、日期生效费率等增强项。这些属于后续模型精度工作，
不改变阶段 0 至 6 核心契约已经完成的判断。

## 专项账本

| 领域 | 详细入口 | 在本页中的作用 |
| --- | --- | --- |
| 策略边界拆分 | [strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md) | R0 至 R6 的实施记录和验收标准 |
| 外部框架 | [framework-integration-ledger.yml](framework-integration-ledger.yml) | 各适配器的机器可读状态和退出条件 |
| 跨仓库产物 | [artifact-contracts.yml](artifact-contracts.yml) | artifact owner、producer、consumer 和 envelope 字段 |
| 维护性 | [maintainability-refactor-roadmap.yml](maintainability-refactor-roadmap.yml) | 大文件、长函数、复杂度热点和预算棘轮 |
| 策略证据 | [strategy-evidence-gate.md](strategy-evidence-gate.md) | 生命周期对应的强制证据集合 |
| A 股数据与研究 | [data-transition-playbook.md](data-transition-playbook.md) | current asset 和长窗口研究入口 |
| 会计与执行模拟 | [accounting_execution_roadmap.md](../portfolio-backtester/docs/accounting_execution_roadmap.md) | 统一账本和后续精度增强项 |
| 概念级机器学习 | [concept-level-ml-exploration.md](../strategy-research/experiments/style_factors/concept-level-ml-exploration.md) | 低优先级研究探索 |
| 文档归集 | [documentation-consolidation.md](documentation-consolidation.md) | 碎片化说明、权威入口和去重顺序 |

## 更新规则

- 工作区级优先级和完成状态只在本页维护。
- 专项机器账本保存字段级事实，本页引用其结论，不复制完整记录。
- 项目标记为 `complete` 时，需要同时写明验收命令、证据路径或当前实现入口。
- 机器账本与本页冲突时，先依据当前代码和测试核对，再在同一变更中修正两处。
- 每次发布只勾选发布检查清单，不把重复执行的检查新增为 roadmap 项目。
