# StyleReplica A80/B20

StyleReplica 用风格因子构造 A80/B20 风格复制组合。因子语义与组合语义分别由 alpha 和 portfolio 职责维护，`strategy style-replica run` 只提供稳定研究运行入口。

- 生命周期：`operational_research`
- 生产资格：无
- 因子研究与报告薄包：顶层 `src/style_factors`
- 组合回测：`portfolio_backtester`
- 运行入口：`strategy style-replica run`

顶层 `src/style_factors` 当前被视为工作区薄包。若它继续增长或被多个外部消费者复用，应单独评审 owner，而不是把实现移入 pipeline。
