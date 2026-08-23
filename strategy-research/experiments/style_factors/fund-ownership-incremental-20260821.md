# 公募基金持仓因子信息增量探索（截至 2026-08-21）

## 结论

当前证据不支持把 `fund_breadth`（持有该股票的公募基金数量）作为单独的正向选股因子。更值得继续研究的是披露变化量，尤其是 `fund_breadth_change`。`fund_ownership` 在控制既有机构持仓和市值后也显示出中等程度的增量信息，但还没有达到生产级证据标准。

## 数据与口径

- 原始 `fund_portfolio` 通过 `TUSHARE_TOKEN_2` 与 `https://fast.xiaodefa.cn` 更新至报告期 `2026-06-30`。
- A 股 `daily` / `daily_basic` 更新至最近交易日 `2026-08-21`。
- PIT 派生资产：`/home/richard/data/market-data-platform/assets/tushare/a_share/fund_portfolio_features/a_share_all_fund_portfolio_features_20260821`
- 派生资产校验：660,903 行、5,988 只股票、410 个事件交易日。重复键为 0。可用日期穿越为 0。
- 最新持仓披露事件日为 `2026-07-22`。之后没有新披露，按 PIT 状态继续延续到 `2026-08-21`。

这里使用的是完整 `fund_portfolio` 披露持仓，不是每只基金的 Top10 持仓。因此 `fund_breadth` 表示最新已知披露中持有该股票的基金数量，不能解释成 Top10 公募重仓广度。

## 分析方法

以 PIT 可用日作为信号日，连接未来 20 个交易日的收盘收益。对每个事件日计算：

1. 截面 Spearman Rank IC。
2. 因子最高 20% 与最低 20% 的收益差。
3. 将因子对 `institution_holding` 和 `log(circ_mv)` 做截面残差化后的 Rank IC 和分组收益。

原始事件面板有 640,334 个股票-事件观测、410 个日期。与 `institution_holding` 有效重叠的日期为 325 个。结果是探索性统计，不是 OOS 组合门禁。

## 结果

| 因子 | 原始 IC20 | 原始 Top-Bottom | 控制后 IC20 | 控制后 Top-Bottom |
|---|---:|---:|---:|---:|
| `fund_breadth` | -1.96% | -0.81% | +0.84% | +0.22% |
| `fund_breadth_change` | +0.80% | +0.31% | +1.99% | +0.63% |
| `fund_ownership` | +1.00% | +0.14% | +1.83% | +0.34% |
| `fund_ownership_change` | +0.94% | -0.03% | +1.31% | +0.18% |
| `fund_stk_float_ratio_sum` | +0.08% | -0.08% | +0.95% | +0.12% |
| `fund_hold_amount_to_float_share` | +0.44% | +0.08% | +1.32% | +0.25% |

作为同样本基线，`institution_holding` 的平均 IC20 约为 +1.00%。因此最有希望的增量方向是：

- `fund_breadth_change`：控制后 IC 比基线高约 1 个百分点。
- `fund_ownership`：控制后 IC 比基线高约 0.8 个百分点。
- 绝对 `fund_breadth`：原始关系偏负，可能更像拥挤度/反转信号。

分阶段看，2024–2026 子样本中 `fund_breadth_change` 平均 IC20 约 +4.98%、Top-Bottom 约 +1.65%，但只有 57 个事件日期，存在明显 regime sensitivity，不能直接外推成长期稳定 alpha。

## 下一步

1. 用月末 as-of panel 做固定调仓频率回测，而不是只用披露事件日。
2. 使用复权收益、行业/市值中性和交易成本，重新验证 `fund_breadth_change`。
3. 更新 `institution_holding` 到同一覆盖期，避免基线在 2026-05-06 后变成陈旧状态。
4. 做滚动 OOS、不同披露滞后和不同基金规模加权版本。
5. 在进入标准因子组合前，要求 ICIR、分组单调性、换手和成本后收益同时通过门禁。
