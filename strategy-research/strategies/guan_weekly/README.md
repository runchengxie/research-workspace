# Guan 周度多因子策略

Guan 周度策略主要由外部 `guan-factor-research-framework` 维护。工作区只通过明确的权重文件或 `strategy_app.weekly_backtest_bridge` 把周度权重转换为 `portfolio_backtester` 的公开组合合同。

- 生命周期：`external_research`
- 生产资格：无
- 策略实现：外部 `guan-factor-research-framework`
- 工作区接缝：`strategy_app.weekly_backtest_bridge`
- 回测：`portfolio_backtester`

外部仓库不通过 `PYTHONPATH` 拼接进本工作区。若策略进入长期 shadow 或生产评审，先冻结输入输出合同和证据，再决定策略特有适配是否进入 `strategy-app`。
