# 工作区路线图

> status: active
> owner: workspace
> last_verified: 2026-08-23
> source_of_truth: yes
> superseded_by: n/a

本页是 `research-workspace` 的路线图总账。它聚合数据、策略证据、跨仓库契约、架构边界、
回测会计、执行成熟度、外部框架和维护性工作。专项文档继续保存设计细节和机器可读记录，
工作区级的完成状态、优先级和下一步统一在本页判断。

本页状态口径以机器账本和当前代码/测试为唯一事实来源。下列数字已与 `maintainability-refactor-roadmap.yml`
（2026-08-17）、`strategy-research/catalog.json`（2026-08-16）、`framework-integration-ledger.yml`
（2026-08-17）核对：真实未解决热点 80 条（登记册 182 条，其中 97 条已降到阈值下、5 条已 cleared），
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
| D1 | P0 | `complete` | `market-data-platform` | A 股完整研究数据 | `normalized_fundamentals` 已发布（mdp PR #46 多 dataset 发布工具 + 真实发布，2026-08-18）：current 契约 `exists: true`、`is_symlink: true`，latest alias 解析到 `a_share_all_normalized_fundamentals_20260814`，`as_of=20260817`，manifest `schema_version=normalized.v2`，覆盖 20150101–20260815，911,680 行，7,620 只证券，合并快照经 `validate_normalized_fundamentals` 校验 `status passed`。`pit_fundamentals` 同步升级到 v2 PIT（911,669 行）。`capacity`/`turnover-cost` 长窗口压力证据仍 `pending`，属 E2 范围 |
| E1 | P0 | `complete` | `strategy-research`、workspace | 策略生命周期证据 | 门禁双档已实现（`--strict` 护栏档 + `--strict --zero-gaps` 晋级评审档），`production_eligible` 全 `false` 致原 `--strict` 形同虚设的问题以双档收口，不再误标生产级。五策略真实缺口（含 `daily_watch20` 的 pit/cost/final_oos/regime 非 pass）登记于各自 `known_gaps`，待 E2 长窗口证据补齐后晋级档归零 |
| E2 | P0 | `in_progress` | data、alpha、portfolio、strategy owners | A 股长窗口晋级证据 | 长窗口最终样本外、成本压力和容量证据尚未形成当前可晋级组合，PIT/历史行业/日线已发布不等同于晋级完成。生成 runbook 与 `configs/experiments/variants/a_share_long_window.yml` 已落地。2026-08-23 strategy-pipeline PR #74 已合并（`1d0fd1b`），指数/PIT Top800 benchmark 日收益构建与 turnover-cost evidence 生成已从手工步骤工具化；research-workspace PR #189 同步对应 pipeline gitlink。真实 2015→latest 长窗口计算、历史行情覆盖核实和 canonical promotion evidence 仍未生成，因此 E2 保持 `in_progress` |
| C1 | P1 | `complete` | workspace、各产物 owner | Artifact Envelope v2 | 类型、v1 fixture 兼容读取、v2 校验已落地，writer 为 opt-in。生产方已全部采用：`alpha-research` signals 写入方（`signal_artifact.py`/`StyleReplicaSignalGenerator.write`，alpha-research PR #26）、`portfolio-backtester` positions 写入方（`positions_artifact.py`，PR #36）、`strategy-pipeline` targets 写入方（`export_targets.py`，在 `targets.json.lineage.json` sidecar 写 `artifact_envelope` v2，配置/内容/上游文件哈希与 producer 身份由契约测试验证）均已写入 `artifact_envelope` 键并经契约测试。`research-contracts` 作为 git 子目录由各生产方按不可变 commit 安装 |
| B1 | P1 | `complete` | `strategy-app`、`strategy-pipeline`、owner repos | 跨仓公开 API 收口 | 核心跨仓私有符号已收口：`alpha-research` 发布 `prepare_feature_dataset`（PR #25）、`portfolio-backtester` 发布 `evaluate_walk_forward_backtest`（#35）与 `portfolio_daily_rows`、`market-data-platform` 发布 `sql_literal`/`duckdb`（#44）、`strategy-app` 发布 guard_ablation 全家公开名与 `build_or_load_model_frame`/`merge_frozen_model_frame`/`factor_frame_for_d_sample`（#30/#31/#32）、`strategy-pipeline` 调用方全部改向公开名并升级交叉依赖 pin（#70/#71）。外围研究影子符号（`d11_h5_shadow_artifact`/`contract`、`daily_watch20_market_shadow`、`period_evaluation`/`period_outputs` 的 import-as 私有名）仍留待后续收口，import boundary 门禁未拦截私有符号的问题建议后续加 ruff 私有导入 lint |
| DOC1 | P1 | `complete` | workspace、各仓文档 owner | 说明文档归集 | 路线图总账已建立，治理修正 G3 已将 `strategy-research/README.md:9` 与 `strategies/daily_watch20/README.md:7-8` 的 `operational`/`生产资格:有` 校正为 `research_shadow`/`否`，与 `catalog.json` 一致（PR #148 已合并）。碎片化清单见 `documentation-consolidation.md`，剩余 DOC2/DOC4/DOC5 等去重按该清单分批推进 |
| B2 | P1 | `in_progress` | `strategy-pipeline`、`strategy-app`、`market-data-platform`、`research-contracts` owner | 子模块边界重构（收口策略层与共享工具） | 2026-08-24 复核后，SA-12 的合法公开编排方向保持不变。SA-13 仍需定义级审计，SA-14 已完成。SA-15 的 Numeric v2、DeepSeek V4 ranking/stability 和 fixed-slot holdings overlay 已分别归位到 `alpha-research` 与 `portfolio-backtester`，strategy-app 只保留适配壳与产品控制逻辑。剩余 deepseek legacy stability、session challenger、three-arm 等强 contract 模块暂留 app，待 typed contract 冻结后再评估。B2 保持 `in_progress`，后续重点是 ownership budget ratchet 与 workspace gitlink 收口 |
| X1 | P1 | `complete` | `quant-execution-engine` | 执行证据成熟度 | broker 能力矩阵覆盖测试已落地（`quant-execution-engine` PR #15 合并，提交 68ef56f）：7 个后端均有机器可读 `BrokerCapabilityMatrix`，`mock_sim` 离线能力修正为 `supports_live_submit=false`，paper/live 分类与 factory `PAPER_BROKERS` 一致。gitlink 已同步至 research-workspace（PR #156，643d588e）。`ibkr-paper` 模拟盘（美股）验证仍属持续联调范畴，A 股真实报单后端证据缺失为客观现状，归入 X1 长线跟踪而非本次重构缺口 |
| F1 | P2 | `planned` | `market-data-platform`、`alpha-research` | Qlib 条件化适配 | blocked（2026-08-18）：适配器已实现（`market-data-platform/.../integrations/qlib.py`、`alpha-research/.../backends/qlib.py`），标准 dev 门禁 `@skipif(not QLIB_AVAILABLE)` 跳过真实 runtime。差分脚本 `strategy-research/experiments/qlib_pilot/diff_native_vs_qlib.py`（ADR-0005 验收证据，Native 与 Qlib 后端对比）已存在，但未接入发布门禁，真实 runtime 差分证据未成发布门槛，留待进入实施阶段补齐 |
| F2 | P2 | `planned` | `portfolio-backtester` | 回测差分后端 | blocked（2026-08-18）：当前只有原生 `NativePositionReplayBackend`，Qlib 差分与 Backtrader 采用仍处于规划阶段，无现存差分后端代码可重构，留待进入实施阶段 |
| F3 | P2 | `planned` | `quant-execution-engine` | vn.py 执行传输 | blocked（2026-08-18）：当前只有框架中立 `BrokerAdapter` 边界，无 vn.py extra、适配器或注册后端，无现存代码可重构，留待进入实施阶段 |
| M1 | P2 | `continuous` | 各仓 owner | 维护性预算收敛 | 机器账本真实未解决热点 80 条（登记册 182 条：97 条已降到阈值下、5 条已 cleared），受棘轮预算约束，大文件预算上限：data 41 / pipeline 29 / 组合回测 8 / 执行引擎 4 / alpha 5 / 顶层 3 / strategy-app 2。2026-08-18 顶层 `workspace_governance.py` 抽出 `workspace_governance_facades.py`，顶层大文件 5→4 下调，2026-08-19 将 `tests/test_next_open_to_high_research.py`(738) 拆为 `tests/_next_open_shared.py` 加 `tests/test_next_open_to_high_research_part2.py`（两文件均低于 500 行），顶层大文件 4→3 下调（PR #170 合并） |
| R1 | P3 | `planned` | `strategy-research` | 概念级机器学习 Path C | blocked（2026-08-18）：`concept-level-ml-exploration.md` 标"待探索·低优先级"，M1–M6 无完成记录，先验证 H1/H2 再决定是否投入，当前无现有 ML 探索代码可重构，留待研究结论 |
| DG1 | P0 | `complete` | `strategy-research`、workspace | 判断账本 schema | 把策略投资判断提升为机器可检查对象：`claim_id`、`statement`、`supports`、`contradicts`、`critical_assumptions`、`invalidation_conditions`、`abstain_conditions`、`status`、`last_reviewed`。设计细节见 [research-decision-governance.md](research-decision-governance.md)。schema 已落地（`strategy-research/schemas/claim.v1.schema.json`）并配套校验脚本 `scripts/decision_governance_check.py` 与测试 `tests/test_decision_governance_check.py`。判断账本目录 `strategy-research/judgment-ledger/` 已填入六个真实 claim（覆盖五个策略），`python scripts/decision_governance_check.py` 全部通过。DG1 采用条件（schema+校验+测试+真实内容）满足 |
| DG2 | P0 | `complete` | `strategy-research`、workspace | 研究案例与决策记录 | 补齐决策线索：`strategy-research/cases/<案例id>/` 下 `case.json`、`decision.md` 与 `reviews/logic.json`、`reviews/evidence.json`。`decision.status` 取值 `no_view`、`provisional`、`accepted`、`rejected`。schema 已落地（`strategy-research/schemas/research_case.v1.schema.json`），同一校验脚本与测试覆盖案例引用路径与目录一致性。`strategy-research/cases/` 已填入三个真实案例（daily-watch20-promotion-readiness、hotsector-pit-discipline、style-replica-evidence-gap），均按真实证据登记 `no_view` 与 abstain，`python scripts/decision_governance_check.py` 全部通过。DG2 采用条件满足 |
| DG3 | P0 | `complete` | `market-intel`、`strategy-research` | 定性来源溯源 | 外部研究素材增加来源 schema（`strategy-research/schemas/source.v1.schema.json`），四个时间点（published、effective、observed、ingested）分开记录，来源可信度按直接性、可验证性、独立性、时间有效性多维拆分，不采用单一来源等级。校验脚本 `scripts/decision_governance_check.py` 增加 `--source` 模式与 `_check_source`，配套测试 `tests/test_decision_governance_check.py` 覆盖未知 claim_type 与 schema 存在性（PR #168 合并，2026-08-18）。DG3 采用条件满足 |
| DG4 | P1 | `complete` | `strategy-research`、workspace | 缺数据即放弃判断 | `no_view` 与 `abstain` 成为决策记录一等状态，报告生成器遵守"可用证据到支持结论、缺失证据到 no_view"，禁止证据缺失时填补叙事。`decision_governance_check.py` 的 `_check_dg4` 强制无视图需登记弃权、已知缺口阻断 accepted（PR #167 合并，2026-08-18）。DG4 采用条件满足 |
| DG5 | P1 | `complete` | `strategy-research`、workspace | 逻辑与证据双评审 | 每个案例拆独立逻辑评审与证据评审，机器可读输出，交集与分歧交由人类裁决。独立性要求见设计文档，禁止同模型相似输出冒充独立证据。`decision_governance_check.py` 的 `_check_dg5_reviews` 要求两类评审齐备（PR #167 合并，2026-08-18）。DG5 采用条件满足 |
| DG6 | P2 | `complete` | `strategy-research`、workspace | 证据完备度卡片 | 拆分 `evidence_readiness` 与 `investment_conviction`，不合成单一置信度总分，先按维度展示证据覆盖、来源可靠性、稳健性、未解决矛盾和时效性。`research_case.v1.schema.json` 的 `decision` 对象新增 `evidence_readiness`（维度数组）与 `investment_conviction`（字符串），description 明确禁止合成单一总分（PR #167 合并，2026-08-18）。DG6 采用条件满足 |
| DG7 | P2 | `complete` | `market-intel` | 产业链显式关系 | 为热点类研究维护实体关系层，放在外部 `market-intel`，`research-workspace` 只引用稳定实体标识，不把关系图塞入本仓。`strategy-research/strategies/hotsector/README.md` 已声明产业链关系由 market-intel 维护、本仓仅引用稳定 entity_id，并新增 `strategy-research/references/market_intel_entity_ids.md` 指向权威实体来源、约定禁止在本仓伪造或推测 entity_id 归属（PR #171 合并，2026-08-19）。DG7 采用条件满足 |

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

### DG1 至 DG3：研究判断层采用顺序

判断治理的采用顺序为 DG1、DG2、DG3，设计细节见 [research-decision-governance.md](research-decision-governance.md)。

1. DG1 先落地判断账本 schema，让 claim 成为机器可检查对象，引用路径必须存在。当前 schema 与校验脚本已落地，判断账本已填入六个真实 claim，见上表 DG1。
2. DG2 再引入研究案例与决策记录，补齐决策线索到生命周期。当前 schema 与校验脚本已落地，cases 已填入三个真实案例，见上表 DG2。
3. DG3 随后为外部素材引入来源溯源，四个时间点分开记录。
4. DG4 至 DG6 在判断账本稳定后推进，DG7 由外部 `market-intel` 承接。

每项落地必须配套 schema 校验脚本和测试，不改变现有证据门禁的强制证据集合。
校验入口：`python scripts/decision_governance_check.py`，schema 文件在
`strategy-research/schemas/claim.v1.schema.json` 与 `strategy-research/schemas/research_case.v1.schema.json`。

## P1 收口标准

### C1：统一跨仓库产物 envelope

- `signals`、`positions` 和 `targets` 的生产方可以选择写入 `research.artifact-envelope.v2`。
- 读取方继续兼容现有 v1 fixture。
- 时间戳、配置哈希、内容哈希和 lineage 由契约测试验证。
- 明确 `research-contracts` 的发布方式和消费范围，避免各仓复制 schema 实现。

当前三个生产方均已采用（见上表 C1）。`targets.json` 的 envelope 由
`strategy-pipeline` 的 `export_targets.py` 写入 `targets.json.lineage.json` sidecar，
`content_sha256` 哈希 targets.json 本体，配置哈希覆盖 target source、gross exposure、
positions source、as-of 与 pruning 参数，lineage 覆盖 run 目录中的 summary、config 与
持仓文件。验证入口：`strategy-pipeline/tests/test_export_targets.py` 的
`test_export_targets_writes_artifact_envelope_v2` 与顶层
`tests/test_artifact_contract_manifest.py` 的采用清单断言。

### B1：只通过公开 owner API 跨仓调用

当前 import direction 和 source layout 门禁已经通过。后续应把跨仓调用的私有符号提升为有测试的公开 API，
再删除调用方对下划线符号的直接依赖。该项属于接口加固，不重新开启已完成的 R0 至 R6 物理拆分。

### B2：子模块边界重构（收口策略层与共享工具）

边界盘点与历史候选重构项见 [submodule-boundary-refactor-checklist.md](submodule-boundary-refactor-checklist.md)。
本项以当前 AGENTS、import boundary 门禁和代码事实为准：

- 原则一：控制平面可以调用应用层公开 API。`strategy-pipeline` 负责 CLI、编排、外部调用、生产发布和
  `targets.json` 交接，因此允许 `strategy_pipeline → strategy_app` 的公开 API 调用。完成指标是 pipeline
  不复制策略计算内核，而不是把合法 import 计数归零。
- 原则二：应用层不得反向依赖控制平面。`strategy-app/AGENTS.md` 与
  `scripts/import_boundary_rules.yml` 的 `strategy-app:no-control-plane-imports` 均要求
  `strategy_app` 不导入 `strategy_pipeline`。当前门禁预算为 0，继续作为依赖方向事实来源。
- 原则三：共享工具不复制。SA-13 在 `strategy-pipeline` 内已改用
  `research_contracts.file_receipts.file_sha256`；其他仓的同类函数需重新按“函数定义”而非搜索命中数审计，
  再决定 owner 和迁移批次。
- SA-7 原“把候选池从数据层迁入 strategy-app”的建议撤销。2026-08-20 复核确认 PIT candidate/universe
  数据资产集中在 `market-data-platform/research_views` 符合数据 owner 边界，策略层只保留配置或桥接。
- SA-14 已完成：`strategy-research` 明确是 superproject tracked 目录，不加入 `.gitmodules`。
- SA-15 已完成三批低耦合归位：Numeric v2 ranking 进入 `alpha-research`，DeepSeek V4 ranking/stability kernel 进入 `alpha-research`，fixed-slot holdings overlay kernel 进入 `portfolio-backtester`。strategy-app 保留 campaign identity、PIT/producer validation、session/evidence 和组合编排适配。剩余 legacy stability、session challenger、three-arm 等强 contract 耦合模块后置，先冻结 typed contract。

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
| A 股日线、PIT 财务和历史行业 | `complete` | current contract 已发布对应资产，`normalized_fundamentals` 已随 D1 发布 |
| 研究到执行文件交接 | `complete` | `strategy export-targets` 与 qexec 本地 dry-run 已通过基础契约验证 |
| 旧 owner facade 和共享命名空间 | `complete` | 旧包名、旧共享命名空间和策略 owner delegating facade 已退出活动运行时 |

会计路线图中仍保留企业行动真实数值、冲击与融资模型、日期生效费率等增强项。这些属于后续模型精度工作，
不改变阶段 0 至 6 核心契约已经完成的判断。

## 专项账本

| 领域 | 详细入口 | 在本页中的作用 |
| --- | --- | --- |
| 策略边界拆分 | [strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md) | R0 至 R6 的实施记录和验收标准 |
| 子模块边界重构项 | [submodule-boundary-refactor-checklist.md](submodule-boundary-refactor-checklist.md) | SA-1 至 SA-15 的历史盘点；SA-12 依赖方向与 SA-7/13/14/15 当前结论以本页 2026-08-23 复核为准 |
| 外部框架 | [framework-integration-ledger.yml](framework-integration-ledger.yml) | 各适配器的机器可读状态和退出条件 |
| 跨仓库产物 | [artifact-contracts.yml](artifact-contracts.yml) | artifact owner、producer、consumer 和 envelope 字段 |
| 维护性 | [maintainability-refactor-roadmap.yml](maintainability-refactor-roadmap.yml) | 大文件、长函数、复杂度热点和预算棘轮 |
| 维护性审计（strategy-pipeline） | [maintenance-audit-20260719.md](../strategy-pipeline/docs/internal/maintenance-audit-20260719.md) | 编排仓审计快照和后续优先级 |
| 维护性审计（market-data-platform） | [maintenance-audit.md](../market-data-platform/docs/maintenance-audit.md) | 数据平台审计快照和下一轮优先级 |
| 策略证据 | [strategy-evidence-gate.md](strategy-evidence-gate.md) | 生命周期对应的强制证据集合 |
| A 股数据与研究 | [data-transition-playbook.md](data-transition-playbook.md) | current asset 和长窗口研究入口 |
| 会计与执行模拟 | [accounting_execution_roadmap.md](../portfolio-backtester/docs/accounting_execution_roadmap.md) | 统一账本和后续精度增强项 |
| 概念级机器学习 | [concept-level-ml-exploration.md](../strategy-research/experiments/style_factors/concept-level-ml-exploration.md) | 低优先级研究探索 |
| 研究判断治理 | [research-decision-governance.md](research-decision-governance.md) | 判断账本、决策记录、来源溯源的采用顺序 |
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
- G7（2026-08-18）F1/F2/F3/R1 留痕：F1 原 `in_progress` 与现状不符，改 `planned` 并标 blocked，留待进入实施阶段补齐差分门禁。F2/F3/R1 本为 `planned`，补 blocked 留痕说明"无现存代码可重构"，避免被误判为遗漏。此四项均不制造伪代码，留待进入实施阶段或依赖释放后由专人处理。
- G8（2026-08-18）D1 核实与悬空分支清理：停摆 agent 的 D1 分支（feat/a-share-normalized-publish）基于旧 main（f28e9700），其唯一提交把 `normalized_fundamentals` 在 playbook 中单边标为已发布，并倒退 qexec gitlink（68ef56f→3dfcb5f）与 E1 代码。当时核实数据根无该资产、仓库内无 current 契约条目，发布宣告暂记虚假，拒绝接管其内容，仅清理该悬空 worktree 与分支。更正（2026-08-18 当日稍后）：mdp 侧实际发布已通过 PR #46 完成，数据根 `/home/richard/data/market-data-platform/assets/tushare/a_share/normalized_fundamentals/` 存在 `a_share_all_normalized_fundamentals_20260814` 与 latest alias，current 契约 `exists: true`。D1 现为 `complete`，以第 36 行核实结论为准。
- G9（2026-08-18）F1 差分证据事实纠错：上一轮称"Qlib 差分证据脚本当前仓库不存在（grep 仅见无关 ops 脚本）"，实际 `strategy-research/experiments/qlib_pilot/diff_native_vs_qlib.py` 存在，是 ADR-0005 的 Native 与 Qlib 后端差分验证脚本。F1 未推进的真实原因是差分未接入发布门禁，而非脚本缺失。本表第 43 行已改为按现状表述，F1 仍 `planned` 并标 blocked。
- G10（2026-08-18）研究判断治理立项：新增 DG1 至 DG7，补齐从实验到判断的决策线索。现有体系已覆盖实验与证据的工程治理，判断层尚缺机器可检查对象，本立项不改证据门禁，只增 schema 与校验脚本。
- G11（2026-08-18）C1 闭环：`strategy-pipeline` targets 写入方已在 `export_targets.py` 采用 Artifact Envelope v2，`targets.json.lineage.json` sidecar 写入 `artifact_envelope` 键，配置/内容/上游文件哈希与 producer 身份经契约测试验证。`docs/artifact-contracts.yml` 采用清单把 `targets.json` 从 `adoption_pending` 移到 `adopted_by`，顶层 `tests/test_artifact_contract_manifest.py` 同步断言。C1 由 `in_progress` 改 `complete`。
- G12（2026-08-18）DG1/DG2 schema 落地：`claim.v1` 与 `research_case.v1` 的 JSON schema 落入 `strategy-research/schemas/`，配套 stdlib-only 校验脚本 `scripts/decision_governance_check.py` 与测试 `tests/test_decision_governance_check.py`。校验覆盖字段枚举、嵌套对象必填、引用路径存在性与 case 目录一致性。判断账本与案例目录尚待填入真实内容，DG1/DG2 由 `planned` 改 `in_progress`。
- G13（2026-08-18）DG1/DG2 填入真实内容：判断账本 `strategy-research/judgment-ledger/` 填入六个真实 claim（覆盖五个策略：daily_watch20×2、hotsector、style_replica、d11_h5、dividend_growth_momentum），均以 `strategy-research/evidence/*.json` 与策略 README 为依据，缺证据维度如实登记 `abstain_conditions`。cases 填入三个真实案例（daily-watch20-promotion-readiness、hotsector-pit-discipline、style-replica-evidence-gap），`decision.status` 均按真实证据取 `no_view`，不伪造 pass。`python scripts/decision_governance_check.py` 九项全部通过。DG1/DG2 由 `in_progress` 改 `complete`。
- G14（2026-08-19）边界重构正式立项：新增 P1 项 B2（子模块边界重构），把跨仓边界优化从 checklist 提升到工作区主账本。`submodule-boundary-refactor-checklist.md` 二次盘点新增 SA-12（当时误把 `strategy-pipeline → strategy_app` 公开 API 调用定义为反向依赖）、SA-13（`sha256_file` / `file_sha256` 重复）、SA-14（`strategy-research` 登记问题）、SA-15（三层分治）。B2 不重新开启已完成的 R0-R6 物理拆分。
- G15（2026-08-23）B2 方向纠错：对照 `strategy-app/AGENTS.md` 与 `scripts/import_boundary_rules.yml` 后确认，禁止方向是 `strategy_app → strategy_pipeline`；pipeline 作为控制平面调用 app 公开 API 属正常编排。SA-12 不再以 31 个合法 import 的清零为目标。SA-7 的数据层候选池归属同时撤销误判，SA-14 记为完成。
- G16（2026-08-23）B2 进度同步：strategy-pipeline c97deb2 已收口其跨仓 SHA256 调用；hotsector challenger ranking/contract 已经 alpha-research PR #29 与 strategy-app PR #34 试点归位。SA-13 其余重复需重新定义级审计，SA-15 继续按低耦合模块逐步迁移，避免一次性搬迁 deepseek/three-arm 强耦合代码。
- G17（2026-08-23）E2 工具状态同步：strategy-pipeline PR #74 已合并并提供 benchmark 日收益构建与 turnover-cost evidence 工具，research-workspace PR #189 同步对应 gitlink。该同步只解除工具缺口，真实 2015→latest 长窗口运行、历史行情覆盖与 canonical promotion evidence 仍未完成。
- G18（2026-08-24）B2 ownership closure：portfolio-backtester PR #39、alpha-research PR #33、strategy-app PR #35/#36/#37 已合并。Numeric v2 与 DeepSeek V4 ranking/stability 归 alpha-research，fixed-slot holdings overlay 归 portfolio-backtester，strategy-app 保留产品控制与适配层。后续以 workspace gitlink closure 和剩余强 contract 模块的 typed contract 为验收边界。
