# 子模块边界重构清单

> status: active
> owner: workspace
> last_verified: 2026-08-18
> source_of_truth: no
> superseded_by: roadmap.md

本页记录一次对六个子模块与 `strategy-research` 目录的边界盘点结果，以及据此整理的可落地重构项。
优先级与工作区完成状态仍以[工作区路线图](roadmap.md)为准，本页只保存边界问题的具体文件路径和归属判断，
不重复维护完成状态。边界规则见 [ADR-0006](adr/0006-strategy-knowledge-and-runtime-boundaries.md) 与
[../ARCHITECTURE.md](../ARCHITECTURE.md)。

盘点基线：market-data-platform `65e4740`、alpha-research `79cbfd6`、portfolio-backtester `e439be0`、
strategy-app `e81d53a`、strategy-pipeline `933e133`、quant-execution-engine `1f07cf1`（2026-08-18）。

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
