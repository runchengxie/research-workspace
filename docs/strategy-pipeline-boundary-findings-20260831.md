# strategy-pipeline 边界审计（2026-08-31）

本轮审计只记录可复核的结构事实，不把所有跨仓 import 都判定为错误。
编排层调用 owner-native API 是允许的，真正需要迁移的是 pipeline 自己持有的研究算法、
组合会计和原始数据读取实现。

## 当前规模

- `src` 共有 187 个 Python 文件，约 43,204 行。
- 直接引用 `strategy_app` 的文件有 28 个。
- 直接引用 `portfolio_backtester` 的文件有 30 个。
- 直接引用 `alpha_research` 的文件有 43 个。
- 直接引用 `market_data_platform` 的文件有 60 个。

这些数量是 import 面积，不等于全部都是边界错误。后续要按模块职责和调用方向逐项收口。

## 已复核的原 P0 候选

### DailyWatch20 ablation：已确认是 owner API 编排

- `_daily_watch20_ablation_api.py` 和 `_daily_watch20_ablation_core.py` 保留配置接线、数据加载、
  执行编排和结果落盘。
- 研究统计、样本外决策、source regime 和 variant 元数据由 `strategy_app.daily_watch20`
  的公开 API 提供，pipeline 没有再维护一套 owner kernel。
- pipeline 的跨包调用属于控制面编排，符合 `docs/roadmap.md` 对 B2/SA-12 的现行定义。

处置结论：保留薄的 CLI/orchestration entry，并由 owner API 测试锁定输入输出契约和报告字段。
不再进行没有明确收益的整目录搬迁。

### Hotsector / DeepSeek campaign：已确认是 campaign 编排

`hotsector_deepseek_*`、`hotsector_challenger_*` 和相关 campaign 模块调用
`strategy_app.hotsector` 的公开 ranking、analysis、contract、reporting API。
pipeline 保留一次性 campaign runner、运行目录、receipt 和发布调用，未形成第二套研究算法。

处置结论：campaign 入口继续作为薄壳保留。可复用研究计算已经由 strategy-app owner API
承载，不再将一次性入口强行迁入 strategy-research。

## P1：兼容 facade 已验证

- `liquidity_proxy.py` 只有约 16 行，当前已经从 `portfolio_backtester.liquidity_proxy` 转出。
- `trade_accounting.py` 只有约 16 行，当前已经从 `portfolio_backtester.trade_accounting` 转出。
- `sharpe_stats.py`、`return_metrics.py` 也采用类似 facade 方式。

这些文件是短兼容 facade。pipeline 内部测试和文档已改用 owner-native import，
外部调用仍可通过 facade 迁移。当前保留它们是为了避免未经公告的 API 破坏，后续可按弃用周期删除。

## P1：pipeline 原始数据读取已关闭

`_style_replica_pipeline_core.py` 约 105 行，使用 `market_data_platform.research_views`。
当前扫描未发现绕过 published/research view 的原始文件直读。

处置结论：现有 research view 即稳定消费边界，pipeline 只保留参数编排和结果落盘，
无需再次搬运代码。

## 已确认的保留范围

- `pipeline/panel_load_steps.py`、`pipeline/runner.py`、CLI、运行目录和发布 receipt 属于
  strategy-pipeline 的编排职责。
- 通过 `portfolio_backtester` 的公开回测、成本、换手和执行 API 不属于 pipeline 越界。
- 通过 `alpha_research` 的公开模型、样本切分和信号契约 API 不等于 pipeline 拥有这些实现。
- 通过 `market_data_platform` 的 published asset、路径和数据契约 API 属于合法消费方向。

## 验收结果

1. DailyWatch20 ablation 已通过 owner API 和返回字段测试。
2. Hotsector campaign 已通过 runner、receipt 和生命周期测试。
3. `_style_replica_pipeline_core.py` 已通过原始文件直读边界扫描。
4. portfolio/backtest 兼容 facade 已通过 owner-native 调用迁移测试，暂不删除以保留兼容性。
