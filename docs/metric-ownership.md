# 指标代码归属

本文说明统计指标的代码归属和迁移后的调用方式。`strategy-pipeline` 负责运行编排、评估流程和产物发布，指标公式由对应的 owner 仓库维护。

## alpha-research

通用研究统计位于 `alpha_research.metrics`，包括：

- `daily_ic_series`
- `summarize_ic`
- `quantile_returns`
- `regression_error_metrics`
- `hit_rate`
- `topk_positive_ratio`
- `assign_daily_quantile_bucket`
- `bucket_ic_summary`
- `summarize_active_returns`

涉及换手率的通用组合统计由 `portfolio-backtester` 维护。`alpha-research` 不再新增同类组合会计实现。

## portfolio-backtester

组合收益、换手和风险统计由 `portfolio-backtester` 提供，相关入口包括：

- `portfolio_backtester.metrics`
- `portfolio_backtester.period_turnover`
- `portfolio_backtester.turnover`
- `portfolio_backtester.sharpe_inference`
- `portfolio_backtester.strategy_risk`

其中，收益周期汇总使用 `summarize_period_returns`，夏普比率推断使用 `sharpe_inference` 中的公开函数，例如 `probabilistic_sharpe_ratio`、`deflated_sharpe_ratio`、`expected_max_sharpe` 和 `sharpe_standard_error`。

## strategy-pipeline

流水线可以调用 owner 仓库的公开 API，也可以暂时保留兼容接线。新代码应直接导入 owner API，兼容层只服务于尚未迁移的外部调用方。

指标实现、统计假设和缺陷修复以 owner 仓库为准。迁移旧调用方时，应同时更新测试、导入路径和相关说明文档。确认没有外部调用方后，才能删除兼容路径。

## 维护要求

新增指标前先确认它属于通用研究统计、组合会计还是流水线控制逻辑，再放入对应仓库。跨仓库变更需要同步更新生产方、消费方和顶层契约测试。
