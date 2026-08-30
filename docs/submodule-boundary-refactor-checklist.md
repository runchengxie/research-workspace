# 子模块边界重构清单

> status: historical
> owner: workspace
> last_verified: 2026-08-25
> source_of_truth: no
> superseded_by: roadmap.md

本页保存 2026-08-18 至 2026-08-20 的历史边界盘点与候选重构项。部分判断随后已被当前代码和门禁纠正，
尤其是 SA-7、SA-12、SA-14 与 SA-15。当前优先级、完成状态和依赖方向统一以
[工作区路线图](roadmap.md)、[ADR-0006](adr/0006-strategy-knowledge-and-runtime-boundaries.md) 与
[ADR-0007](adr/0007-style-replica-ownership.md) 为准。本页不得作为新改动的验收事实来源。

2026-08-31 的新一轮机器可读盘点见
[boundary-refactor-inventory-20260831.json](boundary-refactor-inventory-20260831.json)，
执行计划见 [boundary refactor plan](superpowers/plans/2026-08-31-boundary-refactor.md)。

盘点基线：market-data-platform `65e4740`、alpha-research `79cbfd6`、portfolio-backtester `e439be0`、
strategy-app `e81d53a`、strategy-pipeline `933e133`、quant-execution-engine `1f07cf1`（2026-08-18）。

补充盘点（2026-08-19 复核）：基线仓不变，新增对 `strategy-pipeline` 顶层模块、跨仓工具函数复制与
`.gitmodules` 登记缺口的核查。详见文末"新增边界问题（2026-08-19）"。

目标边界与各仓职责见 [strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md)
与 [../ARCHITECTURE.md](../ARCHITECTURE.md)，本页不再重复。盘点结论：策略专属计算与策略决策参数
不应硬编码在通用能力仓。

## 盘点结论摘要

- 依赖方向整体正确：下游仓只 import 上游 `market-data-platform`，`quant-execution-engine` 完全自洽，
  无任何跨仓 import 且无策略专属代码。
- 主要问题是策略知识碎片化：DailyWatch20 与 StyleReplica 的策略决策参数散落在
  `market-data-platform`、`alpha-research`、`portfolio-backtester` 三个通用仓，只在
  `strategy-app` 组装。
- `strategy-pipeline` 仍残留少量本该归属其他仓的实现（研究消融计算、契约、成本换手、原始数据直读）。
- 存在多组跨仓重复代码与孤儿文件。
- （2026-08-19 新增）依赖方向出现局部倒置：`strategy-pipeline` 有 23 个文件
  直接 `from strategy_app import ...`，把 `strategy-app` 的策略计算又包了一层"发布/报告/ablation/policy"
  外壳，反向地 `strategy-app` 侧经核验 没有任何文件 import `strategy_pipeline`（符合边界）。这违反了
  `strategy-app/README.md` 的"strategy_app 禁止导入 strategy_pipeline，通用能力一旦可被两个策略复用应上移"
  以及 `strategy-pipeline` 的"编排层不持有策略 thesis/研究算法"边界。详见文末 SA-12。
- （2026-08-19 新增）`strategy-pipeline` 顶层策略模块规模远多于此前记录：除 SA-1 列的两个 ablation 文件外，
  顶层还有 39 个 `daily_watch20_*` / `hotsector_*` 模块（报告/政策/端到端 pipeline/影子观察等），
  与 `strategy-app` 顶层的 42 个对称。这说明"编排层 vs 应用层"的物理拆分尚未真正落地，SA-1 的范围需扩大。

## 重构项清单

### SA-1：把 pipeline 的 DailyWatch20 消融研究计算迁入 strategy-app（高价值）

- 文件：`strategy-pipeline/src/strategy_pipeline/_daily_watch20_ablation_api.py`、
  `strategy-pipeline/src/strategy_pipeline/_daily_watch20_ablation_core.py`。
- 问题：完整的滚动样本外消融研究计算（variants、显著性、组合指标报告）属于研究计算，应归
  `strategy-app`。它已 import 同族模块 `strategy_app/daily_watch20/{oos,guard_ablation,source_regimes,windows}`，
  自己留在 pipeline 里是历史残留。
- 归属：`strategy-app`（研究计算），pipeline 只留编排壳。
- 完成标准：pipeline 中不再存在该研究评估实现，调用方改走 `strategy_app` 公开 API。

### SA-2：迁移 pipeline 的策略契约与 portfolio 会计逻辑（中价值）

- 文件：`strategy-pipeline/src/strategy_pipeline/contracts/{strategy,backtest,rebalance}.py`、
  `strategy-pipeline/src/strategy_pipeline/{liquidity_proxy,trade_accounting}.py`。
- 问题：与 `portfolio-backtester` 重复或属于组合构造/成本/换手职责（`StrategySpec`、`GroupCap`、
  `BacktestPricingFrameContract`、换手与漂移权重会计、流动性代理）。
- 归属：`portfolio-backtester`，pipeline 侧改 re-export（参照已有 `return_metrics.py`/`sharpe_stats.py`
  re-export 模式）或直接改向。
- 完成标准：pipeline 不再持有这些契约与会计实现，只通过 `portfolio_backtester` 公开名调用。

### SA-3：迁移 signal artifact 契约并删除 alpha 兼容 shim（中价值）

- 文件：`strategy-pipeline/src/strategy_pipeline/contracts/signals.py`（声明 `alpha_research.signals`）。
- 归属：`alpha-research`。
- 完成后删除仅做 `from alpha_research.X import *` 的 stale shim：
  `strategy-pipeline/src/strategy_pipeline/pipeline/research_ops/{promotion_gate.py,promotion_gate_thresholds.py}`、
  `strategy-pipeline/src/strategy_pipeline/pipeline/{train_eval_request_builder.py,train_eval_result.py,freshness_overlay.py}`。

### SA-4：pipeline 原始数据直读改走数据平台（中价值）

- 文件：`strategy-pipeline/src/strategy_pipeline/_style_replica_pipeline_core.py`。
- 问题：直接读 `daily_clean.parquet`、`daily_basic.parquet`、`instruments.parquet`、`industry.parquet`
  原始文件，绕过 `market-data-platform` 数据 API。
- 归属：`market-data-platform`（通过 `published_assets` / `published_frames` 读取）。

### SA-5：alpha-research 中的完整策略迁入 strategy-app（高价值，跨仓风险高）

- 文件：`alpha-research/src/alpha_research/style_replica/{signal_generator,portfolio,theme_map,score_a,score_b,universe,factors,resvol}.py`。
- 问题：StyleReplica 是一个完整策略（信号生成 + 组合构造 + 暴露计算），整个嵌在通用 alpha 仓。
  其中 `portfolio.py` 的组合构造还跨界到 portfolio-backtester。
- 归属：策略专属计算归 `strategy-app`，通用因子数学留在 alpha，组合构造归 portfolio-backtester。
- 备注：`signal_generator.py` 存在未完成的 `ln` 重命名残留，需一并清理。

### SA-6：alpha-research 的 DailyWatch20 策略参数（中价值）

- 文件：`alpha-research/src/alpha_research/daily_watch20_*.py`（9 个，含 `daily_watch20_policy.py`、
  `daily_watch20_model_lifecycle.py`、`daily_watch20_features.py` 等）。
- 问题：策略专属特征/标签/模型/策略决策参数（如 `train_window_dates=504`、`model_family`）硬编码在通用 alpha 仓。
- 归属：策略专属部分归 `strategy-app`，通用统计（Newey-West、Holm）归 alpha 但改名去掉策略前缀。

### SA-7：market-data-platform 的策略专属 research_views（中价值，需判断）

- 文件：`market-data-platform/src/market_data_platform/research_views/daily_watch20_*.py`（9 个）。
- 问题：策略专属 universe/candidate-pool 政策与 schema id（`daily_watch20.*`）嵌入数据仓，
  与其 AGENTS.md 中"策略研究由其他仓库维护"不一致。
- 归属：优先做成策略无关的 PIT candidate-view 资产 API，策略配置由 `strategy-app` 传入，
  否则迁入 `strategy-app`。
- 备注：该项已有 ownership 文档与测试背书，属判断项而非硬错误。

### SA-8：portfolio-backtester 的策略例外与 vendored 代码（低-中价值）

- 文件：`portfolio-backtester/src/portfolio_backtester/daily_watch20_*.py`（3 个，AGENTS.md 明确为兼容例外）、
  `portfolio-backtester/src/portfolio_backtester/_symbol_utils.py`。
- 问题：`_symbol_utils.py` vendored 了 `market_data_platform` 的符号规范化与数据路径解析
  （`canonicalize_symbol_columns`、`resolve_data_input_path`）。
- 归属：符号与路径解析归 `market-data-platform`，不应复刻。
- 备注：DailyWatch20 兼容例外按既有约定评估是否继续保留。

### SA-9：清理重复代码（低风险，可先做）

| 重复 | 归属 |
| --- | --- |
| `strategy-pipeline/src/strategy_pipeline/campaign_specs/*.json`（3 个孤儿文件，与 strategy-app 字节相同且无人读取） | 删除 pipeline 副本 |
| `strategy-pipeline/src/strategy_pipeline/liquidity_proxy.py` | 归 portfolio-backtester |
| `alpha-research/.../freshness_overlay.py` 与 `portfolio-backtester/.../freshness_overlay.py` | 归 owner 后删除副本 |
| `alpha-research/.../benchmarking.py` 与 `portfolio-backtester/.../benchmarking.py` | 归 owner 后删除副本 |
| alpha `metrics.py` 与 portfolio `_metrics_{ic,turnover,active}.py`、`portfolio_selection.py` 的 IC/换手/选股指标 | 归 owner 后统一入口 |
| `portfolio-backtester/.../_symbol_utils.py` 与 `market-data-platform` 的 `symbols.py`/`artifacts.py` | 归数据仓 |
| qexec `targets.py` 与 pipeline `export_targets.py` 的 market/symbol 归一化 | 上移到 `research_contracts` 共享 |

### SA-10：清理 stale 配置与字节码（低风险，可先做）

- `strategy-pipeline/pyproject.toml` 的 `[tool.maintainability.quality_targets] ruff_staged_paths`
  仍列出已迁移或不存在文件的路径（13 个已迁移到 strategy-app，3 个从未存在，仅 2 个仍在 pipeline）。
- `strategy-pipeline/src/strategy_pipeline/__pycache__/daily_watch20_{candidate_pool,candidate_pool_v2,data}.cpython-312.pyc`
  为已迁移模块的 stale 字节码。

### SA-11：CLI 边界（判断项）

- `strategy` 与 `strategy-pipeline` 是同一命令的两个名字（均指向 `strategy_pipeline.cli:main`），冗余。
- `strategy-app` 是纯 API 仓（无 `[project.scripts]`），其研究 app 只能通过 pipeline 的 mega-CLI 触达。
  若希望"哪个 CLI 做什么"更清晰，应显式文档化 mega-CLI 职责，或为 strategy-app 提供研究 app 入口。

## 建议执行顺序

按风险从低到高推进，与跨仓改动"先子模块后顶层"的约定一致：

1. SA-10、SA-9（清理 stale 配置、孤儿文件与重复代码，低风险）。
2. SA-3、SA-4（pipeline 契约/直读归位，同步调用方）。
3. SA-1、SA-2（pipeline 消融计算与会计迁 owner）。
4. SA-5 至 SA-8（策略知识归位，跨仓且需与 owner 协同，风险最高）。
5. SA-11（CLI 边界，作为判断项单独决策）。

每项改动都要在对应子仓库完成检查、提交、推送并合并 `main`，再回顶层更新 gitlink 与版本记录，
最后按顶层 worktree + PR 流程合入。边界门禁见 `scripts/run_pre_push_checks.py` 与
`src/research_contracts/smoke_contracts.py`。

## 新增边界问题（2026-08-19 补充盘点）

以下为 2026-08-19 对边界的二次盘点结果，证据均来自实际文件路径与 import 关系。完成状态不在此维护，
以[工作区路线图](roadmap.md)的 B2 项为准。

### SA-12：消除 strategy-pipeline → strategy_app 的反向依赖（高价值，原 SA-1 范围扩大）

- 规模：grep `from strategy_app import` / `import strategy_app` 在 `strategy-pipeline/src/strategy_pipeline/`
  命中 31 个文件（2026-08-19 复核，原记 23 为低估）。`strategy-app` 侧经核验 无任何文件 import
  `strategy_pipeline`，依赖方向单向在 app 侧正确，违规只存在于 pipeline 侧。
- 反向依赖按性质分级（所有被引符号在 `strategy_app` 已是公开 API，消除工作的本质是搬编排层而非补 API）：
  - A 类（轻量常量/类型/配置，约 10 个文件）：仅 import `strategy_app` 的契约常量或策略 Policy 类，
    如 `_hotsector_deepseek_v4_month_execution_api.py`（CAMPAIGN_ID、HARD_CALL_CAP）、
    `daily_watch20_application_policy.py`（DailyWatch20ResearchPolicy）、`daily_watch20_minute.py`、
    `daily_watch20_ablation_publish.py` 等。可经 pipeline 配置层注入，不需动 app。
  - B 类（调用公开计算 API，多数）：如 `daily_watch20_ablation.py`、`hotsector_ai_shadow_observation.py`、
    `daily_watch20_minute_campaign.py`，已用公开函数（guard_ablation、oos、build_ablation_decision、
    hotsector_ai_shadow_*），仅需把"调用入口/打包"下沉为 app 的 facade，pipeline 改为薄壳。
  - C 类（整段编排/报告/publish，最重，约 4 个文件）：`hotsector_deepseek_v4_month_backtest.py`、
    `hotsector_challenger_campaign.py`、`daily_watch20_slow_minute_campaign.py`、`daily_watch20_market_shadow.py`，
    多子模块编排加 publish，须将 pipeline 编排逻辑迁移至 `strategy_app` 顶层入口，pipeline 仅留调度。
- 典型证据（B/C 类）：
  - `_hotsector_deepseek_v4_month_backtest_api.py` import `deepseek_v4.run_deepseek_v4_paired_replay`、
    `hotsector_challenger_ranking.build_hotsector_challenger_rankings`、`publish_hotsector_challenger` 等公开符号。
  - `daily_watch20_minute_campaign.py` import `MinuteAlphaCampaignConfig`、`evaluate_minute_alpha_campaign`、
    `publish_minute_alpha_campaign` 等公开符号。
- 勘误（2026-08-19）：原 SA-1 点名的 `daily_watch20_ablation_api.py` / `daily_watch20_ablation_core.py` 仍属
  反向依赖，保留，但原描述称"顶层 39 个策略模块含 `policy_primitives.py` / `policy_validation_model.py` /
  `policy_canonical.py` 与 `daily_watch20_pipeline.py`"不准确，pipeline 内不存在这些 policy_* 文件，
  唯一 policy 引用是来自 app 的公开类 `DailyWatch20ResearchPolicy`，`daily_watch20_pipeline.py` 本身
  不 import strategy_app（仅依赖 alpha_research），不属反向依赖。反向依赖以本段 31 文件清单为准。
- 边界原则：`strategy-app` 禁止 import `strategy_pipeline`，依赖方向必须保持 `strategy_app → strategy_pipeline`
  单向。pipeline 只保留编排壳（`pipeline/`、`commands/`、`liveops/`、`contracts/`、`release_tools/`、
  `data_interface.py`、`dataset.py`），真正属于它的内容。
- 归属：策略计算/报告/政策部分进 `strategy_app.daily_watch20.*` 与 `strategy_app.hotsector.*`。
- 完成标准：pipeline 顶层不再有反向 import `strategy_app` 的策略实现文件，调用方改走 `strategy_app` 公开 API。
  建议按 A → B → C 分级推进，每级独立 PR，先消 A/B 类轻量违规、再搬 C 类整段编排。
- 注意：`return_metrics.py`（`from portfolio_backtester.metrics import ...`）与 `sharpe_stats.py`
  （`from portfolio_backtester.sharpe_inference import ...`）是合理的薄 re-export，属编排层对回测统计的引用，
  不视为越界，保留。

### SA-13：统一 `sha256_file` / `file_sha256` 跨仓重复实现（低风险，可先做）

- 现状：同一文件哈希工具函数在全仓至少 10 处各自定义（签名一致 `def sha256_file(path) -> str`
  或 `file_sha256`）：
  1. `src/research_contracts/file_receipts.py:13`（`file_sha256`，正确雏形，被 alpha/portfolio 部分文件使用）
  2. `portfolio-backtester/src/portfolio_backtester/evidence_receipts.py:22`（`sha256_file`）
  3. `quant-execution-engine/src/quant_execution_engine/handoff_audit.py:42`（`sha256_file`）
  4. `market-data-platform/src/market_data_platform/_tushare_minute_campaign_readiness.py:10`（`file_sha256`）
  5. `market-data-platform/src/market_data_platform/providers/tushare_a_share_fundamentals_support.py:82`
     （`file_sha256`）
  6. `strategy-app/src/strategy_app/daily_watch20/daily_watch20_flite_campaign_reporting.py:34`（`sha256_file`）
  7. `strategy-app/src/strategy_app/daily_watch20/daily_watch20_friend_minute_lineage.py:23`（`sha256_file`）
  8. `strategy-app/src/strategy_app/daily_watch20/daily_watch20_minute_campaign_reporting.py:32`、
     `hotsector/hotsector_ai_shadow_contract.py:45`（`sha256_file`）
  9. `strategy-research/src/style_factors/robustness_sources.py:30`（`sha256_file`）
  10. `strategy-pipeline/src/strategy_pipeline/_daily_watch20_publication_validation_core.py:40`（`sha256_file`，本地又定义一份）
- 问题：这是"纯工具被多仓内联复制"，不是"共享库被内联"。`research_contracts.file_sha256` 已存在，但多数仓
  仍自带副本，导致 hash 语义可能漂移。
- 建议：把与产物契约无关的纯工具（hash、symbol 归一化、文件 receipt、JSON/parquet 读取助手）收口到
  共享实现（扩展 `research_contracts` 或新建共享 submodule），让上述 10 处全部改 import 共享实现。
  注意把"工具"与"契约"分离，避免 `quant-execution-engine` / `portfolio-backtester` 为用一个 hash 函数而
  依赖契约包。

### SA-14：把 `strategy-research` 登记进 `.gitmodules`（或显式标注为非锁定仓）

- 现状：`.gitmodules` 只登记 6 个 submodule（market-data-platform / alpha-research / portfolio-backtester /
  strategy-app / strategy-pipeline / quant-execution-engine），但工作区同时存在 `strategy-research` 目录，
  其 `pyproject.toml` 包名 `strategy-research-style-factors`，依赖 `alpha-research` / `portfolio-backtester` /
  `research-contracts`，是事实上的第 7 个协作仓库，却游离于 superproject 的 submodule 锁定与版本组合治理之外。
- 风险：版本漂移，`strategy-research` 的 commit 不被 gitlink 锁定，顶层 `git submodule status` 不覆盖它。
- 建议：要么 `git submodule add` 纳入 `.gitmodules` 统一管理，要么在 `README.md` / `ARCHITECTURE.md` 显式声明其为
  "非锁定的独立表现层仓库"并说明版本来源，消除登记与实际结构的不一致。

### SA-15：以 `style_factors` 三层分治为模板，重切 DailyWatch20 / hotsector 的"内核 / 表现层"

- 正面范例（模板，已核实）：`style_factors` 是正确的三层分治，非重复代码，
  - 计算内核：`alpha_research.style_factors`（`compute_factors`、`merge_sw_industry_pit`，ADR-0006 归属）。
  - 分位回测内核：`portfolio_backtester.style_factors_backtest`。
  - 表现层：`strategy-research/style_factors`（`robustness.py`、`liquidity_signals.py` 等均
    `from alpha_research.style_factors import ...` 复用内核，不自写因子计算）。
- 已核实边界（2026-08-20 代码核查，非推测）：
  - DailyWatch20 计算内核已归位：特征与排名在 `alpha-research`
    （`daily_watch20.py` / `_daily_watch20_ranker.py` / `daily_watch20_features*.py` / `_daily_watch20_label.py`
    / `daily_watch20_pit_features.py` / `daily_watch20_news_heat.py`），watchlist 装配在 `portfolio-backtester`
    （`_daily_watch20_select.py` / `_daily_watch20_config.py` / `daily_watch20.py`）。结构符合模板。
  - `strategy-pipeline` 无越界持有计算内核：其 `*_pipeline` / `*_publish` / `*_campaign` / `*_freshness` 多为
    re-export 或编排外壳，被误标的 `*_core.py`（如 `_daily_watch20_ablation_core.py`、
    `_hotsector_deepseek_v4_month_backtest_core.py`）实为编排聚合层，直接 `from alpha_research... import`
    调用内核或仅定义配置 dataclass，自身不含因子/排名数值逻辑。
  - 数据层集中正确：候选池 / 分钟源 / universe 策略在 `market-data-platform/research_views/`，
    `strategy-app/daily_watch20_candidate_pool.py` 仅为桥接 re-export。
  - 唯一结构洞：hotsector 计算内核未归位。hotsector 的特征（`deepseek_v4.py` / `hotsector_ai_shadow_frame.py`
    / `_deepseek_stability_metrics.py`）、排名（`hotsector_challenger_ranking.py` / `hotsector_numeric_v2_ranking.py`
    / `hotsector_holdings_overlay_selection.py` / `hotsector_session_challenger.py`）、分析
    （`*_analysis.py` / `_hotsector_three_arm_shadow_core.py`）全部留在 `strategy-app/hotsector/`，
    而 `alpha-research` 完全没有 hotsector 计算层。这与 `style_factors` 模板（计算内核在 alpha_research）相悖。
- hotsector 重切真实候选清单与风险（代码级重切待单独立项，非本次机械搬运）：
  - 候选内核：`strategy-app/hotsector/hotsector_challenger_ranking.py`、
    `hotsector_numeric_v2_ranking.py`、`hotsector_holdings_overlay_selection.py`、
    `hotsector_session_challenger.py`、`hotsector_ai_shadow_frame.py`、`deepseek_v4.py`、
    `_deepseek_stability_metrics.py`、`_hotsector_three_arm_shadow_core.py` 及其 `*_analysis.py`。
  - 阻断点（高风险）：上述模块与同仓 `*_contract.py`（评分权重 / 护栏 / PIT 血缘校验常量）强耦合，AI shadow /
    deepseek 模块与策略层深度交互。整体下沉会撕裂 contract 耦合、跨仓搬移 PIT 校验，需逐模块立项，
    每个模块独立开 worktree / PR 序列，并跑对应仓回归（strategy-app `tests/test_*hotsector*`、
    strategy-pipeline `tests/test_*hotsector*`）。
  - 不建议动作：不要一次性把 hotsector 计算全量搬到 alpha_research，先选一个低耦合模块（如
    `hotsector_challenger_ranking.py` + 配套 contract）做试点，验证 dependency-direction 与回归后再扩展。
- 结论：SA-15 原则与边界已落地（本清单即为边界事实），DailyWatch20 侧无需重切，hotsector 侧代码重切为独立大任务，
  见上方候选清单，逐个立项推进。避免把策略政策（`daily_watch20_policy*.py` 身份类 re-export）误判为越界。

## 执行顺序复核（2026-08-19 更新）

原顺序（SA-10 → SA-9 → SA-3/SA-4 → SA-1/SA-2 → SA-5~SA-8 → SA-11）仍成立，本次新增项插入如下：

1. 先做低风险：SA-10、SA-9、SA-13（清理 stale 配置、孤儿文件、`sha256_file` 复制）。
2. pipeline 归位：SA-3、SA-4、（SA-12 范围扩大后的策略模块下沉）。
3. 契约/会计归位：SA-2、SA-1（并入 SA-12）。
4. 策略知识归位（跨仓高风险）：SA-5 至 SA-8、SA-15（模板化重切）。
5. 登记治理：SA-14（`.gitmodules` 或显式标注）。
6. CLI 边界：SA-11，作为判断项单独决策。
