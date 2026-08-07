# 红利 vs 成长 ETF 动量轮动

策略：在每个信号日收盘比较 515180.SH（红利）与 159967.SZ（成长）的跟踪调整收盘收益，
持有较强 ETF，从下一交易日开盘调仓。核心/卫星变体保留 60% 在 512890.SH，轮动其余 40%。

## 定位

- 类型：ETF 动量轮动（跨品种二选一）
- 状态：**长期跟踪**（in-sample research diagnostic）
- 脚本：`dividend_growth_momentum.py`

## 依赖与运行

脚本消费 `strategy_pipeline.dividend_growth_momentum_*`（audit/config/report/reporting）和
`portfolio-backtester` 的公共 API，需在 strategy-pipeline 子模块环境下运行：

```bash
uv run --project strategy-pipeline --extra dev \
  --with matplotlib --with tabulate \
  python strategies/dividend_growth_momentum/dividend_growth_momentum.py --help
```

## 结论占位

_待补充：最近一次运行的收益、Sharpe、回撤等关键指标，以及验证证据文件路径。_
