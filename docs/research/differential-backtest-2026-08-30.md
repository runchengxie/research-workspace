# 差异回测 smoke 检查

## Scope

这是针对 `alpha-research` 与 `portfolio-backtester` 连接关系的小型 CPU-only 契约检查。它不代表生产表现结果，也不进行模型训练。

## Test

同一个由四个日期、三个股票组成的合成评分和收盘价数据框，以两种方式运行：

1. 直接调用 `portfolio_backtester.engine.backtest_topk`。
2. 通过 `alpha_research.walk_forward._evaluate_injected_walk_forward_backtest`，并通过 research service hook 注入同一个 `backtest_topk` 函数。

The configuration used top-1 selection, same-day execution, 10 bps cost, and 52 periods per year.

## Result

两条路径的结果完全一致：

- net returns: `0.099, 0.000, 0.018408163265306143`
- gross returns: `0.100, 0.000, 0.020408163265306145`
- turnover: `1.0, 0.0, 1.0`

结果记录在 `/tmp/differential-backtest-20260830.json`。

## 解释

当前 `alpha-research` 没有第二套独立的组合回测器。它生成研究信号，并将 portfolio backtester 作为服务注入。因此，本检查验证的是集成契约和参数传递。未来如果要比较两套独立引擎，需要专门实现独立的参考计算器，当前架构暂不需要这样做。

## 下一步

在使用该适配器进行更大规模研究前，再增加一个包含延迟执行、费用和缺失价格的 fixture。
