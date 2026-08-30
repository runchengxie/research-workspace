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

## P0 候选：pipeline 持有研究算法

### DailyWatch20 ablation

- `_daily_watch20_ablation_api.py` 约 373 行。
- `_daily_watch20_ablation_core.py` 约 126 行。
- 两者直接组合 `alpha_research`、`strategy_app` 和 `market_data_platform` 的研究 API。
- 研究统计、样本外决策、source regime 和报告构造不应继续在 pipeline 形成第二套实现。

处置方向：保留一个薄的 CLI/orchestration entry，将研究计算移动或委托给
`strategy_app.daily_watch20` 的公开 API。迁移前需要先冻结当前输入输出契约和报告字段。

### Hotsector / DeepSeek campaign

`hotsector_deepseek_*`、`hotsector_challenger_*` 和相关 campaign 模块大量调用
`strategy_app.hotsector`。这些模块当前承担的工作更接近研究 campaign runner，通用 pipeline
编排只占其中一部分。

处置方向：把可复用的研究计算放入 `strategy-app` 或 `strategy-research`，pipeline 只保留
运行目录、参数解析、receipt 和发布调用。一次性 campaign 入口可以留在实验目录或保留薄壳。

## P1 候选：已存在 owner facade，可先验证再删旧实现

- `liquidity_proxy.py` 只有约 16 行，当前已经从 `portfolio_backtester.liquidity_proxy` 转出。
- `trade_accounting.py` 只有约 16 行，当前已经从 `portfolio_backtester.trade_accounting` 转出。
- `sharpe_stats.py`、`return_metrics.py` 也采用类似 facade 方式。

这些文件不应直接删除。下一步应检查外部调用方是否已经改用 owner-native import，
再为 facade 增加弃用周期和 import 迁移测试。它们属于低风险收口项，不是当前最大体积来源。

## P1 候选：pipeline 原始数据读取

`_style_replica_pipeline_core.py` 约 105 行，并直接使用
`market_data_platform.research_views`。需要继续确认它是否只消费 published/research view，
还是自行解析 `daily_clean`、`daily_basic`、`instruments`、`industry` 等原始文件。

处置方向：由 `market-data-platform` 提供稳定的 published frame 或 receipt API，pipeline
只保留参数编排和结果落盘。若现有 research view 已经是稳定 API，则只需补边界测试和文档，
不必再次搬运代码。

## 已确认的保留范围

- `pipeline/panel_load_steps.py`、`pipeline/runner.py`、CLI、运行目录和发布 receipt 属于
  strategy-pipeline 的编排职责。
- 通过 `portfolio_backtester` 的公开回测、成本、换手和执行 API 不属于 pipeline 越界。
- 通过 `alpha_research` 的公开模型、样本切分和信号契约 API 不等于 pipeline 拥有这些实现。
- 通过 `market_data_platform` 的 published asset、路径和数据契约 API 属于合法消费方向。

## 下一步验收标准

1. 为 DailyWatch20 ablation 固定一个公开 owner API 和返回字段测试。
2. 为 Hotsector campaign 固定 runner 输入、输出 receipt 和生命周期测试。
3. 对 `_style_replica_pipeline_core.py` 增加原始文件直读扫描，确认是否存在绕过 published API 的路径。
4. 在 owner API 可用且调用方测试通过后，再删除重复实现或把旧模块降级为短期兼容 facade。
