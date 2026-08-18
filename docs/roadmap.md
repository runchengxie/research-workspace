# 工作区路线图

> status: active
> owner: workspace
> last_verified: 2026-08-18
> source_of_truth: yes
> superseded_by: n/a

本页是 `research-workspace` 的路线图总账。它聚合数据、策略证据、跨仓库契约、架构边界、
回测会计、执行成熟度、外部框架和维护性工作。专项文档继续保存设计细节和机器可读记录，
工作区级的完成状态、优先级和下一步统一在本页判断。

本页状态口径以机器账本和当前代码/测试为唯一事实来源。下列数字已与 `maintainability-refactor-roadmap.yml`
（2026-08-17）、`strategy-research/catalog.json`（2026-08-16）、`framework-integration-ledger.yml`
（2026-08-17）核对：真实未解决热点 81 条（登记册 182 条，其中 96 条已降到阈值下、5 条已 cleared），
五个强制证据策略的 `production_eligible` 均为 `false`。

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

> 状态口径见上。本表数字已与机器账本核对，`production_eligible` 全部为 `false`，故证据门禁当前对五策略均按"已知缺口豁免"放行（见 E1 治理修正）。

| 编号 | 优先级 | 状态 | 负责方 | 项目 | 当前缺口（已核实） |
| --- | --- | --- | --- | --- | --- |
| D1 | P0 | `in_progress` | `market-data-platform` | A 股完整研究数据 | `normalized_fundamentals` 在 current 契约 `exists: false`（`docs/data-transition-playbook.md:38`），`capacity`/`turnover-cost` 长窗口压力证据 `pending` |
| E1 | P0 | `complete` | `strategy-research`、workspace | 策略生命周期证据 | 门禁双档已实现（`--strict` 护栏档 + `--strict --zero-gaps` 晋级评审档），`production_eligible` 全 `false` 致原 `--strict` 形同虚设的问题以双档收口，不再误标生产级。五策略真实缺口（含 `daily_watch20` 的 pit/cost/final_oos/regime 非 pass）登记于各自 `known_gaps`，待 E2 长窗口证据补齐后晋级档归零 |
| E2 | P0 | `in_progress` | data、alpha、portfolio、strategy owners | A 股长窗口晋级证据 | 长窗口最终样本外、成本压力和容量证据尚未形成当前可晋级组合，PIT/历史行业/日线已发布不等同于晋级完成 |
| C1 | P1 | `complete` | workspace、各产物 owner | Artifact Envelope v2 | 类型、v1 fixture 兼容读取、v2 校验已落地，writer 为 opt-in，全仓仅 `style_factors` 一处写入，`research-contracts` 仅 `strategy-research` 本地消费，未跨仓共享，唯一 writer 现已通过包自身 `write_mode=opt_in` 契约校验（`ArtifactEnvelopeV2` 模型加 `write_mode` 默认字段，PR #150 已合并） |
| B1 | P1 | `complete` | `strategy-app`、`strategy-pipeline`、owner repos | 跨仓公开 API 收口 | 跨仓私有别名 `_finite_positive_ratio` 已收口（`strategy-pipeline`#70 改用公开 `finite_positive_ratio`，research-workspace#149 同步 gitlink），import boundary 门禁未拦截私有符号的问题建议后续加 ruff 私有导入 lint，`RELATIVE_PERCENTILE_COL` 来自 `alpha_research.daily_watch20` 的公开 `__all__` 导出，属合规公开 API 使用 |
| DOC1 | P1 | `complete` | workspace、各仓文档 owner | 说明文档归集 | 路线图总账已建立，治理修正 G3 已将 `strategy-research/README.md:9` 与 `strategies/daily_watch20/README.md:7-8` 的 `operational`/`生产资格:有` 校正为 `research_shadow`/`否`，与 `catalog.json` 一致（PR #148 已合并）。碎片化清单见 `documentation-consolidation.md`，剩余 DOC2/DOC4/DOC5 等去重按该清单分批推进 |
| X1 | P1 | `complete` | `quant-execution-engine` | 执行证据成熟度 | broker 能力矩阵覆盖测试已落地（`quant-execution-engine` PR #15 合并，提交 68ef56f）：7 个后端均有机器可读 `BrokerCapabilityMatrix`，`mock_sim` 离线能力修正为 `supports_live_submit=false`，paper/live 分类与 factory `PAPER_BROKERS` 一致。gitlink 已同步至 research-workspace（PR #156，643d588e）。`ibkr-paper` 模拟盘（美股）验证仍属持续联调范畴，A 股真实报单后端证据缺失为客观现状，归入 X1 长线跟踪而非本次重构缺口 |
| F1 | P2 | `planned` | `market-data-platform`、`alpha-research` | Qlib 条件化适配 | blocked（2026-08-18）：适配器已实现（`market-data-platform/.../integrations/qlib.py`、`alpha-research/.../backends/qlib.py`），标准 dev 门禁 `@skipif(not QLIB_AVAILABLE)` 跳过真实 runtime，但 Qlib 差分证据脚本当前仓库不存在（grep 仅见无关 ops 脚本），且 `market-data-platform` 层正由 D1 agent 占用，本次重构无独立代码可收口。差分证据未成发布门禁，留待 D1 释放后由专人补齐，不制造伪代码 |
| F2 | P2 | `planned` | `portfolio-backtester` | 回测差分后端 | blocked（2026-08-18）：当前只有原生 `NativePositionReplayBackend`，Qlib 差分与 Backtrader 采用仍处于规划阶段，无现存差分后端代码可重构，留待进入实施阶段 |
| F3 | P2 | `planned` | `quant-execution-engine` | vn.py 执行传输 | blocked（2026-08-18）：当前只有框架中立 `BrokerAdapter` 边界，无 vn.py extra、适配器或注册后端，无现存代码可重构，留待进入实施阶段 |
| M1 | P2 | `continuous` | 各仓 owner | 维护性预算收敛 | 机器账本真实未解决热点 81 条（登记册 182 条：96 条已降到阈值下、5 条已 cleared），受棘轮预算约束，大文件预算上限：data 41 / pipeline 29 / 组合回测 8 / 执行引擎 4 / alpha 4 / 顶层 4 / strategy-app 1 |
| R1 | P3 | `planned` | `strategy-research` | 概念级机器学习 Path C | blocked（2026-08-18）：`concept-level-ml-exploration.md` 标"待探索·低优先级"，M1–M6 无完成记录，先验证 H1/H2 再决定是否投入，当前无现有 ML 探索代码可重构，留待研究结论 |

## P0 验收顺序

### D1：发布完整研究数据

1. 发布 `normalized_fundamentals` 不可变资产和 latest alias。
2. 在 `a_share_current.json` 中确认该资产存在、清单可读且覆盖范围明确。
3. 复核 PIT 财务、历史行业和股票池的时间点语义，不用最新快照回填历史。

### E1：证据门禁双档与真实缺口登记

当前以下策略有强制证据要求（五者 `production_eligible` 均为 `false`，生命周期见 `catalog.json`）：

- `daily_watch20`（`research_shadow`）
- `hotsector`（`research_shadow`）
- `style_replica_a80_b20`（`operational_research`）
- `d11_h5_shadow`（`shadow`）
- `dividend_growth_momentum`（`pre_production`）

#### 门禁双档设计（已落地）

证据门禁 `scripts/strategy_evidence_gate.py` 提供两档，区分日常护栏与晋级评审：

- 护栏档 `--strict`：仅阻断未登记缺口（`unregistered_gaps`）与生产级策略的缺失项。研究型策略带已登记 `known_gaps` 仍可放行，避免冻结日常推送。此档接入 `scripts/run_pre_push_checks.py:129`，每次 pre-push 运行。
- 晋级评审档 `--strict --zero-gaps`：要求研究型策略 `known_gaps` 为空、任何缺失检查都失败。只有在策略真正要晋级时才主动启用，恢复门禁对晋级路径的约束力。

#### 真实缺口状态

`daily_watch20` 的底层 A 股证据（`docs/evidence/a-share-*.json`）明确标注 capacity 与 cost/final_oos 为 pending、券商实盘能力关闭、`automatic_promotion_allowed=false`。因此其 `catalog.json` 已从 `operational` 校正为 `research_shadow`，`production_eligible=false`。该策略当前证据包 `strategy-research/evidence/daily_watch20.json` 中 `pit`/`cost`/`final_oos`/`regime` 四项非 pass，属客观事实，不能强行补齐为 pass（那会制造虚假生产级声明）。

其余四个策略同样处于研究生命周期且证据不齐，需在 E2 长窗口晋级证据阶段补齐，而非在本项造假晋级。

#### 完成标准

- 双档门禁已实现并通过测试（`tests/test_strategy_evidence_gate.py`）。
- `catalog.json` 的生命周期与证据结论一致，缺口均显式登记于各策略 `known_gaps`，不被静默漂移。
- 晋级评审时运行 `python scripts/strategy_evidence_gate.py --strict --zero-gaps`，五策略当前会因带已知缺口而失败，这是预期状态，待 E2 补齐后归零。

> 治理修正（G1/G2）：原 `--strict` 因五策略 `production_eligible=false` 且缺项均注册为 `known_gaps`，失败条件永不触发，门禁形同虚设。现以双档设计收口，护栏档保日常不冻结，晋级档 `--zero-gaps` 恢复约束力，不再依赖把研究型策略误标 `production_eligible=true`。

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

## 本轮治理修正记录（2026-08-18）

本版相对上一版（`last_verified: 2026-08-17`）的实质性修正，均来自对代码、测试和机器账本的核对：

- G1 — 证据门禁数字纠错：上一轮外部口径称"五个策略必需证据均为 `present: []`"，实际 `python scripts/strategy_evidence_gate.py --json` 显示 `daily_watch20` 已有 `[walk_forward, benchmark_matrix, cpcv]`、`hotsector` 已有 `[walk_forward]`。本表改为报告真实 `present` 集合。
- G2 — 门禁形同虚设：`--strict` 虽已接入 pre-push（`run_pre_push_checks.py:129`），但五策略 `production_eligible=false` 且缺项均注册为 `known_gaps`，失败条件永不触发。已在 E1 收口标准标注，需恢复门禁约束力。
- G3 — 文档残留漂移：`strategy-research/README.md:9` 与 `strategies/daily_watch20/README.md:7-8` 仍写 `operational`/`生产资格:有`，与已校正的 `catalog.json`（`research_shadow`/`false`）不一致。机器账本（`strategy-evidence-gate.md:101-103`）记载的校正未在人类可读文档同步，列入 DOC1 缺口。
- G4 — 维护性债务数字纠错：上一轮外部口径称"179 条未解决、按仓分布 57/46/27/18/15/12/4"，实际机器账本 `maintainability-refactor-roadmap.yml` 记录真实未解决 81 条（登记册 182 条，96 条已降到阈值下、5 条已 cleared），按仓预算上限见 M1 项。本表以机器账本为准。
- G5 — R6 与 B1 口径分清：`framework-integration-ledger.yml` 中 `strategy-pipeline-thinning` 已标 `complete`（物理拆分完成），而 roadmap 的 B1（跨仓私有 API 收口）仍 `in_progress`。两者为不同维度，已在 B1 缺口中列出真实残留的私有符号调用（`_finite_positive_ratio`、`alpha_research.daily_watch20` 内部常量）。
- G6（2026-08-18）X1 闭环：broker 能力矩阵覆盖测试已在 `quant-execution-engine` PR #15（68ef56f）合并，research-workspace 侧 gitlink 同步与 frozen baseline 重算经 PR #156（643d588e）合并，X1 由 `in_progress` 改 `complete`。
- G7（2026-08-18）F1/F2/F3/R1 留痕：F1 原 `in_progress` 与现状不符，Qlib 差分证据脚本不存在且 `market-data-platform` 层被 D1 agent 占用，无独立代码可收口，改 `planned` 并标 blocked。F2/F3/R1 本为 `planned`，补 blocked 留痕说明"无现存代码可重构"，避免被误判为遗漏。此四项均不制造伪代码，留待进入实施阶段或依赖释放后由专人处理。
