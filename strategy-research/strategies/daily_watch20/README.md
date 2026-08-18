# DailyWatch20

DailyWatch20 在每个信号日从严格时间点候选池生成完整排名，再构造 20 只目标组合。生产发布使用 `watchlist20` 控制面，候选池、特征身份、组合规则和下一交易日目标日期必须同时通过失败关闭校验。

当前主线使用严格候选池、受控 A4/B16 组合与显式发布等级。F-lite、slow-volume、旧仓再资格、基本面 shadow 和长周期 buffer 都是该策略族的研究变体，不因单次回测收益自动改变生产规则。

- 生命周期：`research_shadow`
- 生产资格：无，仍受每次运行门禁约束
- 策略特有计算：`strategy_app.daily_watch20`
- 通用 alpha：`alpha_research`
- 组合和执行回放：`portfolio_backtester`
- 运行和发布：`strategy watchlist20`、`strategy_pipeline`
- 证据入口：`strategy-app/docs/application-catalog.md` 与冻结研究归档

待抽离项包括 pipeline 中的候选研究 runner、分钟 campaign、模型生命周期计算、研究报告和 owner facade。发布窗口、原子写入、回执与目标交接继续留在 pipeline。
