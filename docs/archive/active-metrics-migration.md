# 主动收益指标迁移记录

> status：completed
> owner：workspace
> completed_at：2026-07-14

本页记录 `portfolio-backtester#11` 与 `strategy-pipeline#25` 已经完成的职责划分调整。当前用法以各仓库 README 和公开的应用程序接口（API，即程序之间互相请求数据的标准方式）文档为准。

## 已完成内容

- `portfolio-backtester#11` 增加持仓基准评估，以及 `PSR`（概率夏普比率）、`DSR`（缩水夏普比率）和 `Expected Max Sharpe`（期望最大夏普比率）的公开统计接口（API）。
- `strategy-pipeline#25` 把重复的主动收益、分段收益和 `Sharpe`（夏普比率）推断实现改造为兼容旧接口的转发层，仅保留编排层专用的预测评估指标。
- superproject 已更新子模块指针并完成跨仓库验证。

## 保留的验证约束

- 持仓基准的日收益按从买入到卖出的整个持有期复利计算，不能简单地用卖出当天的收益和分段收益逐日相加。
- `run_position_backtest()` 不与某一种具体基准绑定。
- 策略、基准和主动收益统计分层保存。
- 旧 `strategy_pipeline.return_metrics` 和 `strategy_pipeline.sharpe_stats` 仅作为兼容入口。
- 共享统计函数的权威实现位于 `portfolio_backtester`。
