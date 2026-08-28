# deep-learning 集成边界

## 定位

`deep-learning-tick-data-prediction` 是一个独立的研究卫星仓库，负责：

- L2 事件流数据的清洁检查和时间对齐审计。
- event-stream 模型训练、验证和预测。
- 输出带有样本日期、标签日期、可交易标记和模型身份的预测 artifact。

它不负责工作区级版本编排、通用 alpha 证据管理或最终组合执行。

## 三方分工

```text
deep-learning-tick-data-prediction
  事件级数据正确性、模型和预测 artifact
        |
        v
alpha-research
  IC、滚动验证、CPCV/PBO 和候选晋升证据
        |
        v
portfolio-backtester
  组合构造、成本、换手、容量、暴露和执行语义
```

`research-workspace` 只锁定三个仓库的版本组合，并负责跨仓库文档和轻量检查，不复制任何一个仓库的源码、数据、checkpoint 或运行产物。

## 交接方式

第一阶段使用文件 artifact 交接。deep-learning 的 formal prediction artifact 至少应能表达：

- `symbol`
- `trading_date`
- `label_date`
- `return_end_date`
- `target_return`
- `score`
- `can_buy`
- `can_sell`
- `in_universe`

后续适配时，将其转换为 `alpha-research` 的 signal artifact，再由 `portfolio-backtester` 的公开 `BacktestSpec` / `run_backtest` 接收组合输入。跨仓库不传递第三方框架对象，也不直接导入子仓库内部模块。

## 验收顺序

1. 先用 deep-learning 自带的事件级回测确认 L2 语义、开盘成交和标签边界正确。
2. 再用 alpha-research 复核预测质量和时间序列证据。
3. 最后用 portfolio-backtester 做成本、换手、容量和执行差分回测。
4. 只有当关键指标和逐日持仓差异均在预先约定的容差内，才把组合回测结果作为统一结果发布。

因此，统一回测框架是协同消费层，不会取代 deep-learning 对 L2 事件语义的本地正确性验证。
