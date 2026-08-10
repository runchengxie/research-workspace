# R3 调用方改向：facade 分批删除计划

> 本文档是 ADR-0006 策略边界拆分 R3 阶段的执行蓝图，由 `feat/r3-callgraph-analysis` worktree 产出。
> 它只做规划与调用图分析，不删除任何代码。后续每一批删除应在独立 worktree 中按本文分批进行。

## 背景

`docs/compatibility-facades.yml` 的 `strategy-owner-delegating-public-facades` 组登记 46 个策略 owner facade。
R3 目标：将 `strategy-pipeline` 内对这些 facade 的调用改向 owner API，并同批删除对应 facade。

- 46 个 facade 中，31 个无冻结哈希约束（可清零），15 个被 `hotsector_numeric_v2_provenance.py` 的 SHA256 字节钉死（需先更新 provenance 契约再删）。
- 调用方高度集中在 `tests/`（约 45 处）与 `scripts/research/`（约 9 处），生产 `src/` 仅 `daily_watch20_market_shadow_publish.py` 1 处。

## 冻结者识别（字节级契约，不可直接删）

来源：`strategy-pipeline/src/strategy_pipeline/hotsector_numeric_v2_provenance.py` 的 `IMPLEMENTATION_SOURCE_FILES`（25 条，其中 15 条属于本 facade 组）。

冻结 facade 清单（删除前必须先更新 provenance 契约并重算 bundle_sha256）：

1. hotsector_numeric_v2_analysis
2. hotsector_numeric_v2_contract
3. hotsector_numeric_v2_ranking
4. hotsector_numeric_v2_reporting
5. daily_watch20_flite_campaign_reporting
6. daily_watch20_flite_contract
7. daily_watch20_slow_minute_execution
8. daily_watch20_statistics
9. hotsector_ai_shadow_contract
10. hotsector_challenger_analysis
11. hotsector_challenger_contract
12. hotsector_challenger_inputs
13. staggered_cohort_execution
14. staggered_cohort_execution_records
15. staggered_cohort_execution_reporting
16. staggered_cohort_execution_state
17. staggered_cohort_inputs

（实际 15 条属 facade 组，IMPLEMENTATION_SOURCE_FILES 中 `hotsector_numeric_v2_inputs` 等条目亦在其中，删除前以 provenance 文件为准逐条核对。）

## 分批计划

### 第一批（零引用，最低风险）
以下 facade 经精确 import 分析已无任何真实调用方，可直接删除并更新 `compatibility-facades.yml`：

- daily_watch20_flite_base_scores
- daily_watch20_slow_minute_campaign_inputs
- staggered_cohort_execution_records
- staggered_cohort_execution_reporting
- staggered_cohort_execution_state
- staggered_cohort_inputs

> 注意：`staggered_cohort_execution_records/reporting/state` 与 `staggered_cohort_inputs` 虽在 provenance 25 条列表中，但属"冻结者"子集，删除前仍需先更新 provenance 契约（见下）。

### 第二批（非冻结 + 仅 tests/scripts 引用，低风险改调用方）
40 个有真实调用方且无生产 src 调用方的 facade。删除前需将其 tests/scripts 引用改向 owner API。按调用方数量升序推进（callers=1 优先）：

- callers=1：daily_watch20_candidate_pool_v2, daily_watch20_flite_factors, daily_watch20_flite_metrics, daily_watch20_guard_ablation, daily_watch20_slow_minute_campaign_analysis, daily_watch20_slow_minute_campaign_contract, daily_watch20_slow_minute_campaign_reporting, daily_watch20_statistics, hotsector_ai_shadow_frame, hotsector_ai_shadow_receipts, hotsector_ai_shadow_selection, hotsector_challenger_reporting, hotsector_numeric_v2_analysis, hotsector_numeric_v2_reporting, hotsector_session_challenger_response_contract
- callers=2~3：见分析脚本输出（daily_watch20_candidate_oos, daily_watch20_flite_contract, daily_watch20_fundamental_shadow, daily_watch20_source_regimes, daily_watch20_windows, hotsector_ai_shadow_contract, hotsector_ai_shadow_v2_evaluation, hotsector_ai_shadow_v2_evaluation_contract, hotsector_challenger_analysis, hotsector_challenger_ranking, hotsector_low_turnover_contract, hotsector_numeric_v2_contract, hotsector_numeric_v2_ranking, staggered_cohort_execution, daily_watch20_flite_campaign_reporting, daily_watch20_model_lifecycle, daily_watch20_slow_minute, hotsector_low_turnover_experiment, hotsector_session_challenger_contract）
- callers=4~11（高引用，留待第二批末尾）：daily_watch20_news_heat, hotsector_challenger_contract, hotsector_deepseek_stability, daily_watch20_oos, daily_watch20_data, daily_watch20_candidate_pool

### 第三批（冻结者，需 provenance 契约更新）
15 个冻结 facade：先在 `hotsector_numeric_v2_provenance.py` 中将其从 `IMPLEMENTATION_SOURCE_FILES` 移除并重算 `bundle_sha256`，再删 facade 文件。此批风险最高，应独立 worktree + 独立 PR，且需字节级治理审批。

## 执行纪律

- 每一批在独立 worktree 中进行（新建 → PR → 合并 main → 删分支 → 删 worktree → 开新 worktree）。
- 删除 facade 文件的同时，必须从 `compatibility-facades.yml` 的 `strategy-owner-delegating-public-facades.paths` 移除对应条目，并更新 `current_consumers` / `status`。
- 每批删除后运行 `tests/` 与 `scripts/research/` 验证无悬挂引用。
- 冻结者批次不得与其他批次混合在同一 PR。

## 分析方法

调用图通过扫描 `strategy-pipeline/{src,tests,scripts}` 下所有 `.py` 的 `from strategy_pipeline.X import` / `import strategy_pipeline.X` 语句生成，已排除 facade 定义文件自身，避免自引用误报。
