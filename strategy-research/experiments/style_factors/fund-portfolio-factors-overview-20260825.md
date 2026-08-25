# 公募基金持仓因子研究总览

> 截止日期：2026-08-25
> 状态：研究 shadow，不得直接用于生产发布

## 先看结论

基金持仓数据有研究价值，但目前没有证明它是稳定的主选股 alpha。现阶段更合理的定位是：

- `fund_count_holding_stock`：更像拥挤度或关注度变量，方向不稳定；
- `fund_count_holding_stock_qoq_change`：比水平值温和，但当前仍没有证明有稳定增量；
- `fund_breadth_change`、`fund_ownership`：早期探索中出现过较好的控制后结果，但还没有完成同口径的 canonical OOS 晋级验证；
- Top10 基金持仓工程：暂不投入。

当前建议：技术面主模型保持不变，组合优先 Top20，容量优先观察 Top30。基金字段只保留 shadow 观察，不加入主模型，也不做统一负向惩罚。

## 不同名称不是同一个因子

历史文档中出现了多个相近名称，不能直接合并：

| 名称 | 实际含义 | 当前判断 |
|---|---|---|
| `fund_breadth` | 事件面板中最新已知持有该股票的基金数量 | 水平值，原始关系偏负，像拥挤度 |
| `fund_count_holding_stock` | full fund asset 中的股票持仓基金数量水平 | 与上面概念接近，但数据构造和调仓口径不同 |
| `fund_breadth_change` | 早期事件或月末面板中的持仓广度变化 | 探索性结果较好，但阶段敏感，尚未 canonical OOS |
| `fund_count_holding_stock_qoq_change` | full fund asset 按基金持仓状态计算的季度变化字段 | 本次独立 native shadow 未通过增量门槛 |
| `fund_ownership` | 基金持仓金额或持仓比例相关变量 | 有一定探索价值，但尚未完成模型级复核 |

特别是月末持仓水平差分和资产中的 qoq 字段，不应写成同一个变量。它们的事件定义、可用日期和缺失结构不同。

## 最高优先级证据：原生 Pipeline 复核

四条原生运行都使用 26 个 Final OOS 调仓日，日期为 2024-06-28 至 2026-07-30，Top30 分支使用相同的 PIT universe、模型、标签、成本和组合规则。

| 分支 | Rank IC | Q5-Q1 | 信号换手 | 原生累计净收益 @10bp | 原生 Sharpe | 共同日历执行累计收益 |
|---|---:|---:|---:|---:|---:|---:|
| Top20 baseline | 0.1060 | 2.012% | 91.80% | 132.70% | 1.33 | 88.63% |
| Top30 baseline | 0.1060 | 2.012% | 89.87% | 116.56% | 1.31 | 84.40% |
| Top30 + `fund_count_holding_stock` | 0.1026 | 2.162% | 87.20% | 167.75% | 1.52 | 81.46% |
| Top30 + `fund_count_holding_stock_qoq_change` | 0.0996 | 1.945% | 85.60% | 154.30% | 1.73 | 76.87% |

表中的原生累计收益和 Sharpe 不能单独作为晋级依据。水平值分支的原生完整收益期为 19 个，Top30 baseline 为 17 个；qoq 分支虽然也是 17 个收益期，但共同日历执行模拟仍低于 Top30 baseline。因此目前更稳妥的解读是：两个基金字段都改变了持仓路径并降低了换手，但没有证明带来稳定的共同 OOS 增量。

## 基金数量水平值为什么容易误导模型

原生 factor diagnostics 中，`fund_count_holding_stock` 的结果为：

- raw Rank IC：-0.0308；
- 控制相关风格后的 residual IC：-0.0465；
- residual IC IR：-0.48；
- 最终模型 feature importance：2.87%。

加入模型后，整体 Rank IC 从 0.1060 降到 0.1026。最近 6/12 个日期的滚动 Rank IC 和 Q5-Q1 曾略有改善，但共同 OOS 全段执行收益低于 Top30 baseline。

这更像以下几种信息的混合：

1. 基金抱团代表市场关注度，趋势市场中可能有效，拥挤反转时可能失效；
2. 基金数量与规模、流动性、机构关注度和热门行业存在重叠；
3. 基金披露是低频且滞后的，持仓状态可能长期不更新；
4. 技术面模型已有规模、成交量和动量信息，弱基金字段可能只是在少数股票上重新排序。

因此，模型重要性不能解释成增量预测力。它只说明模型使用过这个字段。

## qoq change 的独立 shadow 结果

本次 qoq shadow 只加入 `fund_count_holding_stock_qoq_change`，没有同时加入水平值或其他基金字段。

结果是：

- raw factor IC：-0.0173；
- 控制相关风格后的 residual IC：+0.0057，IR 仅约 0.05；
- 最终模型 feature importance：4.70%；
- Final OOS Rank IC：0.0996，低于 baseline 的 0.1060；
- Q5-Q1：1.945%，低于 baseline 的 2.012%；
- 最近 6/12 个月的模型滚动 IC：0.0949/0.0812，方向上没有明显恶化；
- 共同日历执行累计收益：76.87%，低于 Top30 baseline 的 84.40%。

所以 qoq change 的结论比水平值稍微温和，但仍然是：可以继续低成本 shadow 观察，不能进入主模型。

## 早期探索结果如何理解

2026-08-21 的事件面板探索中，`fund_breadth_change` 控制市值和机构持仓后 IC20 约为 +1.99%，`fund_ownership` 控制后 IC20 约为 +1.83%。这些结果说明基金持仓数据可能包含信息，但它们有三个限制：

- 使用的是披露事件面板，不是固定月频组合 OOS；
- 部分结果只有较少的事件日期，存在明显 regime sensitivity；
- 还没有通过统一标签、成本、组合构造和 placebo 的模型级验证。

因此这些结果只能用来决定“下一步研究什么”，不能用来决定“现在把什么加入主模型”。

## 当前决策

| 项目 | 决策 |
|---|---|
| Top20 / Top30 | Top20 作为默认，Top30 作为容量候选 |
| `fund_count_holding_stock` | 不进入主模型，保留 shadow |
| `fund_count_holding_stock_qoq_change` | 不进入主模型，保留低频 shadow |
| 统一负向惩罚 | 暂不采用 |
| Top10 基金持仓资产 | 暂停工程 |
| 下一轮研究 | 只有在有明确资源时，才对 `fund_breadth_change` 或 `fund_ownership` 做单一、预注册的 canonical OOS 实验 |

## 为什么暂不做 Top10 工程

当前可用基金资产是完整披露持仓的 full asset，不是每只基金的 Top10 持仓。Top10 需要重新定义数据源、冻结口径、披露可用日和覆盖率。

在 full asset 的水平值和 qoq change 都没有通过增量门槛前，投入 Top10 工程的预期信息价值不高。先确认因子定义本身有稳定信息，再扩大数据工程范围。

## 证据、限制与复现入口

主要证据按优先级排列：

1. [原生 Top20、Top30 与 fund_count 复核](fund_count_native_topk_replay_20260825.md)
2. [基金持仓数量与 qoq change Final OOS ablation](fund_count_final_oos_ablation_20260824.md)
3. [Top-K 与拥挤度惩罚诊断](fund_count_topk_crowding_penalty_20260824.md)
4. [公募基金持仓信息增量探索](fund-ownership-incremental-20260821.md)

本次 qoq shadow 配置：

```text
strategy-pipeline/configs/experiments/diagnostics/a_share_native_top30_fund_count_qoq_change_20260825.yml
```

运行标识：`a_share_native_top30_fund_count_qoq_change_20260825_20260825_060928_fe8c55ae`。产物写入本机临时目录，不纳入版本库。

共同限制包括：Final OOS 只有 26 个调仓日，`000300.SH` 没有可用日线，因此没有有效 benchmark/active-return；这不是 CPCV/PBO 通过结论，也不是生产发布授权。
