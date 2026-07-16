# 主动收益指标迁移记录

> status: completed
> owner: workspace
> completed_at: 2026-07-14

本页记录 `portfolio-backtester#11` 与 `strategy-pipeline#25` 已完成的职责迁移。当前使用方式以各仓库 README 和公开 API 文档为准。

## 已完成内容

- `portfolio-backtester#11` 增加持仓基准评估，以及 PSR、DSR 和 Expected Max Sharpe 公开统计 API。
- `strategy-pipeline#25` 将重复的主动收益、分期收益和 Sharpe 推断实现改成兼容转发，只保留编排层专属的预测评估指标。
- superproject 已更新子模块指针并完成跨仓库验证。

## 保留的验证约束

- 持仓基准日收益按进场至退出的持有期复合，不能直接按退出日与分期收益做日频合并。
- `run_position_backtest()` 保持与具体基准解耦。
- 策略、基准和主动收益统计分层保存。
- 旧 `strategy_pipeline.return_metrics` 和 `strategy_pipeline.sharpe_stats` 仅作为兼容入口。
- 共享统计函数的权威实现位于 `portfolio_backtester`。
