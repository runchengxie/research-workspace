# 原生 Pipeline：Top20 / Top30 与 fund_count 复核

## 一句话结论

这次原生复核没有证明 `fund_count_holding_stock` 有稳定的增量 alpha。

Top30 + `fund_count_holding_stock` 在原生回测摘要中的 Sharpe 和总收益高于 Top30 baseline，但它的 Final OOS 信号 Rank IC 下降，且原生回测的完整收益期数量不同。用同一日历的执行模拟对齐后，基金分支在整个共同 OOS 窗口反而略低于 Top30 baseline，最近 6/12 个月只出现很小的改善。

因此建议保持：

1. 默认组合优先 Top20；容量优先时观察 Top30。
2. 不把基金持仓数量统一改成负向惩罚。
3. Top30 + `fund_count` 只保留为 shadow candidate，不进入主模型。
4. 暂停 Top10 基金数据工程；如果还要继续，只做一个独立的 `fund_count_holding_stock_qoq_change` 小实验。

## 实验口径

三条分支均使用原生 `strategy run`：

- 同一 PIT universe、月频标签、XGBoost 模型和 20% Final OOS 切分；
- 同一 Final OOS 日期：26 个调仓日，2024-06-28 至 2026-07-30；
- 同一 10bp 交易成本、等权 long-only 组合和原生延迟退出规则；
- 只改变 `top_k`，或在 Top30 baseline 上额外加入一个 `fund_count_holding_stock`；
- 基金分支保留了 baseline 的 `pe_ttm`、`pb`、`ps_ttm`、`turnover_rate` 和 `total_mv` provider overlay。

基金数据使用的是最新 full asset，而不是旧的 `latest` 快照：

```text
`$DATA_PLATFORM_ROOT/assets/tushare/a_share/fund_portfolio_features/a_share_all_fund_portfolio_features_20260821/data`
```

该 manifest 标记为 PIT 数据，生成于 2026-08-23，查询覆盖至 2026-07-22，共 660,903 行、5,988 个股票代码。原生 pipeline 日志确认实际合并了 660,903 行基金数据；基金字段只有 1 个缺失填补指标，之后进入模型的数据没有剩余 NaN。

## 原生 Final OOS 结果

| 分支 | Rank IC | Q5-Q1 | Top-K 信号换手 | 原生完整收益期 | 原生累计净收益 @10bp | Sharpe | 最大回撤 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Top20 baseline | 0.1060 | 2.012% | 91.80% | 18 | 132.70% | 1.33 | -19.71% |
| Top30 baseline | 0.1060 | 2.012% | 89.87% | 17 | 116.56% | 1.31 | -21.88% |
| Top30 + fund_count | 0.1026 | 2.162% | 87.20% | 19 | 167.75% | 1.52 | -19.35% |

这里最容易误读的是最后一行：基金分支确实提高了原生摘要里的收益和 Sharpe，但它形成了 19 个完整收益期，Top30 baseline 只有 17 个。原因是不同持仓路径触发了不同的延迟退出数量；因此不能直接把 `167.75% - 116.56%` 当成基金因子的贡献。

更公平的检查是读取三个分支的执行模拟，并只在同一个日历上比较。共同 OOS 日历上的执行模拟净值结果为：

| 分支 | 共同 OOS 累计净收益 | 最近 6 个月 | 最近 12 个月 |
|---|---:|---:|---:|
| Top20 baseline | 88.63% | -38.53% | -45.32% |
| Top30 baseline | 84.40% | -37.38% | -42.61% |
| Top30 + fund_count | 81.46% | -36.85% | -42.43% |

基金分支最近阶段只比 Top30 baseline 高约 0.5 个百分点（6 个月）和 0.2 个百分点（12 个月），但整个共同 OOS 窗口低约 2.9 个百分点。这是“最近没有明显恶化，但也没有稳定增量”的证据，而不是晋级证据。

## 基金字段本身说明了什么

原生 factor diagnostics 中，`fund_count_holding_stock` 的结果为：

- 全 OOS 平均 raw Rank IC：-0.0308；
- 控制相关风格后的 residual IC：-0.0465；
- residual IC IR：-0.48；
- 最终模型 feature importance：2.87%。

这说明基金持仓数量整体更像一个方向不稳定的拥挤度/风格变量，而不是稳定的正向选股信号。它并非每个阶段都负：最近 6 个 OOS 日期的 raw IC 均值约为 0.0149，最近 12 个约为 0.0100，因此更像市场阶段变化下的辅助变量。

加入模型后，整体 Rank IC 从 0.1060 降到 0.1026，下降约 3.1%；但最近 6/12 个日期的滚动 Rank IC 从 Top30 baseline 的 0.0821/0.0815 提高到 0.0957/0.0870。与此同时，最近 6/12 个日期的 Q5-Q1 从 1.360%/0.987% 提高到 1.864%/1.352%。

所以它的行为可以简单概括为：

> 基金数量改变了少数 Top30 成分的选择，最近阶段有一点帮助；但它没有改善全市场排序质量，也没有在整个共同 OOS 窗口带来稳定的组合增量。

## 组合选择建议

Top20 和 Top30 的信号质量完全相同，因为 `top_k` 只影响组合构造，不影响模型打分。Top30 的信号换手略低、持仓更分散，但在这次共同日历执行模拟中 Top20 的累计结果更高。因此：

- 把 Top20 作为当前默认口径更合适；
- 把 Top30 作为容量优先的候选口径；
- 不要因为 Top30 + fund_count 的原生摘要总收益较高，就把基金字段并入主模型。

## 限制

- Final OOS 只有 26 个调仓日，样本仍然偏小；
- 原生日志显示 `000300.SH` 没有可用日线数据，因此本次没有有效 benchmark/active-return 结果；
- 原生回测的完整收益期数量受延迟退出影响，不同分支分别为 18、17、19，比较总收益时必须使用共同日历的执行模拟作为辅助；
- 本次没有改生产配置，也没有启动 Top10 数据工程；
- 这不是 CPCV/PBO 通过结论，只是对候选分支的口径和方向复核。

## 产物

诊断配置：

- `strategy-pipeline/configs/experiments/diagnostics/a_share_native_top20_baseline_20260825.yml`
- `strategy-pipeline/configs/experiments/diagnostics/a_share_native_top30_baseline_20260825.yml`
- `strategy-pipeline/configs/experiments/diagnostics/a_share_native_top30_fund_count_20260825.yml`

原生运行产物写入本机临时目录 `fund_count_native_topk_replay_20260825/runs/`，不纳入版本库。
