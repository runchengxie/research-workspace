# 每日飞书 10 股：三策略合成理论回测

运行日期：2026-09-09  
结果目录：`/home/richard/data/quant/daily_feishu10_theoretical_composite/20260909`  
证据等级：`message_derived_composite_proxy`，不是生产组合回测

## 已确认的真实框架

代码和测试确认当前 `Weekly Client Basket 10` 的默认配额是：

- DailyWatch family：4 只；历史上用 DailyWatch20 补位，因为没有足够的历史 D11-H5 family artifact。
- Cashflow：3 只；从当时最近有效的 PIT selection 取 rank 前3。
- Microcap：3 只；使用已存在的历史 `weekly3_proxy_targets`，保持 research-shadow 属性。

三部分合计10只，按 sleeve 优先级去重。本次没有把 DailyWatch20 前10代理当成最终结果。

## 模拟口径

- DailyWatch：取飞书正式 DailyWatch20 消息的前4只。
- Cashflow：取信号日之前最近有效的 Cashflow monthly selection 前3，保留其历史 signal vintage。
- Microcap：取信号日之前最近有效的历史 weekly3 proxy；该数据最后形成日为 2026-07-31，因此在本窗口内冻结。
- 执行：下一交易日开盘；价格来自 A 股 daily 分区数据。
- 成本：10 bps × 换手 proxy。
- 基准：000300.SH 日收益，连续数据到 2026-08-21。

## 每日刷新理论版本

样本为 2026-08-03 至 2026-08-14，共10个信号日、每个信号日4/3/3、100个股票观测。这里假设 DailyWatch 每日刷新，同时 Cashflow 和 Microcap 沿用最近有效选择；这是为了贴近“每日飞书10股”的记忆，不是当前周度 snapshot contract 的严格复现。

| 持有期 | 样本日 | 平均净收益 | 平均基准收益 | 平均超额 | 命中率 | 可用权重 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1日 | 10 | 0.738% | 0.430% | 0.343% | 80% | 100% |
| 3日 | 10 | 0.719% | 0.552% | 0.201% | 70% | 100% |
| 5日 | 10 | 0.208% | 0.268% | -0.025% | 60% | 100% |
| 10日 | 5 | 0.428% | 0.542% | -0.079% | 40% | 50% |

1日净收益连续复利约 **+7.52%**，同期基准约 **+4.36%**，最大回撤约 **-3.38%**；总换手 proxy **3.5**，总成本拖累约 **35 bps**。

## 严格按当前周度 snapshot 的参考结果

只取 2026-08-03 和 2026-08-10 两个周度信号日，仍按4/3/3合成并周内冻结。样本只有2个信号日，不能用于稳定性判断：

- 1日平均净收益：+1.443%，平均超额：+1.259%；
- 3日平均净收益：+2.486%，平均超额：+1.745%；
- 5日平均净收益：+3.616%，平均超额：+1.497%；
- 10日只剩50%窗口覆盖，不能作为正式结论。

## 结论和边界

这版比“DailyWatch20 前10”更接近你记忆中的真实三策略合成框架，但仍是理论 proxy：没有使用最终飞书 `basket.json`、receipt 或 delivery receipt，也没有历史 D11-H5、历史 microcap 正式 shadow artifact 的完整逐周链路。因此结果只能用来判断回测方法和量级，不能证明当前灰度组合 alpha，也不能改变 live eligibility。

补充：过去三年跨度的长期代理结果见 [daily-feishu10-theoretical-3y-composite-20260910.md](daily-feishu10-theoretical-3y-composite-20260910.md)。长期结果同样只有9个季度 DailyWatch 研究快照，不能替代真正的日频历史回放。

下一步应优先把每日/周度最终组合输出保存为 canonical artifact；一旦有多个真实组合样本，可直接用同一套 T 日收盘、T+1 开盘回放替换本 proxy 输入。
