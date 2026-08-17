# StyleReplica A80/B20

StyleReplica 用风格因子构造 A80/B20 风格复制组合。因子语义与组合语义分别由 alpha 和 portfolio 职责维护，`strategy style-replica run` 只提供稳定研究运行入口。

- 生命周期：`operational_research`
- 生产资格：无
- 因子计算内核：`alpha_research.style_factors`（alpha-research）
- 分位回测内核：`portfolio_backtester.style_factors_backtest`（portfolio-backtester）
- 表现层（归因、报告、图表）：`strategy-research/style_factors`（`python -m style_factors`）
- 组合回测：`portfolio_backtester`
- 运行入口：`strategy style-replica run`

`strategy-research/style_factors` 表现层与两个内核 owner 解耦。若表现层继续增长或被多个外部消费者复用，应单独评审 owner，而不是把实现移入 pipeline。
