# A 股风格因子 2008–2026 全历史约束稳健性附录

> 状态：screen-grade constrained sensitivity。晋级结论：hold。只有 promotion gate 全部通过才允许更新三份主报告和正式 latest。

## 研究问题

在相同样本窗口内，对照 raw/gross、daily_clean 约束后 gross、以及加入换手成本后的 constrained/net，检查主要风格结论是否依赖股票池、上市天数、ST、涨跌停、停牌和退市处理。

## 数据覆盖

- daily_clean：2008-01-02 ~ 2026-07-31，14,942,791 行，5,816 只证券。
- 2008–2014 联结完整率：daily_basic 99.9875%、adj_factor 100.0000%、limit_status 99.9387%。
- 2014/2015 复权桥：按 raw close × adj_factor 统一尺度，P99 绝对收益误差 0.0050 个百分点，>0.10 个百分点 1 只。
- PIT 形成日股票池：2008-02-29 ~ 2026-07-31，223 个形成日，与日行情联结率 99.0444%。
- 涨跌停：2008–2014 使用已验 hash 的 stk_limit bridge，2015+ 使用 daily_clean 内的 limit flags。
- 历史 ST：namechange 区间重建后只在形成日展开，共 28,602 行。该数据属于 reconstructed PIT，不是 revision-safe 历史。
- PIT v2：vintage=20260802，历史形成日仅可称 reconstructed PIT，revision-safe 起点为 20260802。
- 融券资格：2015-01-30 ~ 2026-07-31，仅作为做空资格上界。

## 数据质量门槛

| check | observed | threshold | passed |
| --- | --- | --- | --- |
| daily_key_duplicates | 0.000000 | = 0 | 1.000000 |
| universe_key_duplicates | 0.000000 | = 0 | 1.000000 |
| margin_key_duplicates | 0.000000 | = 0 | 1.000000 |
| pit_panel_key_duplicates | 0.000000 | = 0 | 1.000000 |
| early_daily_basic_join_rate | 0.999875 | >= 99% | 1.000000 |
| early_adj_factor_join_rate | 1.000000 | = 100% | 1.000000 |
| early_limit_status_join_rate | 0.999387 | >= 99% | 1.000000 |
| universe_daily_join_rate | 0.990444 | >= 99% (formation-date suspensions retained) | 1.000000 |
| adjustment_bridge_p99_abs_error_pct | 0.004965 | <= 0.10 percentage point | 1.000000 |
| st_reconstruction_precision | 1.000000 | >= 99% | 1.000000 |
| st_reconstruction_recall | 0.999976 | >= 99% | 1.000000 |

## 核心对照

| 因子 | 共同观察日 | raw/gross 年化% | constrained/gross 年化% | constrained/net 年化% | net-raw 百分点 | net 最大回撤% |
| --- | --- | --- | --- | --- | --- | --- |
| Size 大市值 | 4475.00 | -17.98 | -18.66 | -19.13 | -1.15 | -97.95 |
| Value 低估值 | 4475.00 | 11.15 | 7.60 | 6.83 | -4.32 | -21.48 |
| Momentum 动量 | 4475.00 | -14.58 | -18.43 | -21.53 | -6.95 | -98.73 |
| Quality 复合质量 | 3618.00 | 1.24 | 0.23 | -0.65 | -1.89 | -36.01 |
| Earnings Yield 盈利估值 | 4475.00 | 3.72 | 1.09 | 0.29 | -3.43 | -37.75 |
| LowVol 低波动 | 4475.00 | 8.60 | 5.77 | 2.85 | -5.75 | -44.49 |
| Growth 成长 | 3462.00 | 7.61 | 3.58 | 2.64 | -4.97 | -26.50 |
| Leverage 低杠杆 | 3462.00 | 1.19 | 0.27 | -0.25 | -1.44 | -42.04 |
| Beta 低贝塔 | 4370.00 | -7.02 | -7.16 | -8.01 | -0.99 | -82.64 |
| Liquidity 低换手 | 4475.00 | 18.48 | 14.06 | 11.29 | -7.19 | -19.69 |
| LiquidityFlow 大单资金流 | 96.00 | -1.57 | -0.76 | -4.55 | -2.98 | -3.86 |
| ChipConcentration 筹码集中度 | 854.00 | -1.54 | 8.53 | 5.38 | 6.92 | -15.25 |
| InstitutionHolding 机构持仓 | 833.00 | -4.91 | 7.91 | 4.83 | 9.74 | -14.62 |
| DividendYield 股息率 | 4475.00 | 5.91 | 3.36 | 2.47 | -3.44 | -29.48 |
| PSValue 市销率价值 | 4475.00 | 6.17 | 3.39 | 2.80 | -3.37 | -27.09 |

共同观察日按每个因子 raw 与 constrained 都有实际暴露的日期取交集。LiquidityFlow、ChipConcentration 和 InstitutionHolding 覆盖较稀疏，不能把其日数按连续 11 年理解。



## 成本与退市压力情景

默认单边成交名义成本为 10 bps，退市末端收益使用 -50% 压力代理。同时输出 0/10/20/30 bps 和 -30%/-50%/-100% 情景。

| factor | terminal_return | cost_bps | geometric_annual_ret | max_drawdown | sharpe |
| --- | --- | --- | --- | --- | --- |
| Liquidity 低换手 | -1.00 | 10.00 | 11.36 | -19.96 | 1.09 |
| Liquidity 低换手 | -0.50 | 0.00 | 14.13 | -18.00 | 1.34 |
| Liquidity 低换手 | -0.50 | 10.00 | 11.36 | -19.69 | 1.09 |
| Liquidity 低换手 | -0.50 | 20.00 | 8.66 | -24.52 | 0.85 |
| Liquidity 低换手 | -0.50 | 30.00 | 6.02 | -29.07 | 0.61 |
| Liquidity 低换手 | -0.30 | 10.00 | 11.36 | -19.58 | 1.09 |
| Momentum 动量 | -1.00 | 10.00 | -21.44 | -98.70 | -2.20 |
| Momentum 动量 | -0.50 | 0.00 | -18.51 | -97.54 | -1.87 |
| Momentum 动量 | -0.50 | 10.00 | -21.60 | -98.75 | -2.23 |
| Momentum 动量 | -0.50 | 20.00 | -24.58 | -99.37 | -2.56 |
| Momentum 动量 | -0.50 | 30.00 | -27.45 | -99.68 | -2.85 |
| Momentum 动量 | -0.30 | 10.00 | -21.66 | -98.77 | -2.23 |
| Size 大市值 | -1.00 | 10.00 | -19.08 | -97.92 | -1.46 |
| Size 大市值 | -0.50 | 0.00 | -18.68 | -97.74 | -1.43 |
| Size 大市值 | -0.50 | 10.00 | -19.16 | -97.95 | -1.47 |
| Size 大市值 | -0.50 | 20.00 | -19.63 | -98.15 | -1.51 |
| Size 大市值 | -0.50 | 30.00 | -20.10 | -98.33 | -1.55 |
| Size 大市值 | -0.30 | 10.00 | -19.19 | -97.97 | -1.47 |
| Value 低估值 | -1.00 | 10.00 | 6.80 | -21.40 | 0.77 |
| Value 低估值 | -0.50 | 0.00 | 7.65 | -20.88 | 0.86 |
| Value 低估值 | -0.50 | 10.00 | 6.87 | -21.48 | 0.78 |
| Value 低估值 | -0.50 | 20.00 | 6.10 | -22.07 | 0.70 |
| Value 低估值 | -0.50 | 30.00 | 5.34 | -22.67 | 0.62 |
| Value 低估值 | -0.30 | 10.00 | 6.90 | -21.51 | 0.79 |

## 正式 latest 晋级门槛

10 个核心因子须全部通过：共同样本覆盖不低于最大样本的 80%，三种主口径方向一致，constrained/net 最大回撤相对 raw 恶化不超过 10 个百分点，并且方向在 10/30 bps 成本下均不翻转。

| factor | coverage_ratio | direction_pass | drawdown_pass | cost_pass | factor_pass | failure_reason |
| --- | --- | --- | --- | --- | --- | --- |
| size | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| value | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| momentum | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| quality | 0.81 | 0.00 | 0.00 | 0.00 | 0.00 | direction,drawdown,cost |
| earnings_yield | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | drawdown,cost |
| lowvol | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | drawdown,cost |
| growth | 0.77 | 1.00 | 1.00 | 1.00 | 0.00 | coverage |
| leverage | 0.77 | 0.00 | 0.00 | 0.00 | 0.00 | coverage,direction,drawdown,cost |
| beta | 0.98 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| liquidity | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |

结论：5/10 个核心因子通过，因此动作是 `keep_current_latest`。

## 融券资格上界敏感性

2015 年后的 margin_secs 只限制 bottom-quintile 空头候选，不能证明当日有券，也不含借券费、召回概率和可借数量。因此空头腿仍标记为理论代理。


## 执行逻辑

- 月末收盘形成信号，下一市场交易日收盘尝试调仓，成交仓位从后续收盘到收盘区间开始计算收益。
- 多头涨停不能买、跌停不能卖。空头代理跌停不能开、涨停不能回补。
- 缺少当日行情视为停牌或不可交易，未完成订单逐日重试，直到成交或被下一次调仓覆盖。
- 持有期间缺失价格继续按零收益冻结资本。样本内退市在退市日映射到压力情景末端收益，计价后移除仓位。
- 成本按多空两腿实际成交名义金额扣减，不按固定月度费率拍脑袋扣除。

## 仍未解除的限制

- 历史 ST 已由 namechange 重建，但仍是 2026 年回填的 reconstructed PIT。
- 退市末端收益是压力代理，不是真实退市整理期、现金清算或场外转让收益。
- 空头腿仍是理论 bottom-quintile 代理。margin_secs 只能补充资格上界，仍不能证明券源、费率、召回和可借数量。
- PIT v2 已接入 ROE、ROA、杠杆、经营现金流、净利润。Growth 因缺少 netprofit_yoy/or_yoy 仍沿用 legacy fundamentals。历史财务版本仍非 revision-safe。
- universe_by_date 当前是形成日快照，不是逐日股票池。

## 机器可读证据

- 版本目录（相对 `DATA_PLATFORM_ROOT`）：
  `strategy_outputs/style-factors/20260802-full-constrained-validation/`。
- 三张图：`style_factor_robustness_comparison.png`、
  `style_factor_robustness_drawdown.png`、
  `style_factor_margin_qualification_sensitivity.png`。
- 可移植报告：`style_factor_full_history_robustness.html`（官方打包器桌面/移动 QA 通过）。
- 可复现验证：`notebooks/style-factor-full-history-constrained-validation.ipynb`。
- 因子诊断：15 个因子，见 factor_robustness_diagnostics.csv。
- 全量对照：factor_robustness_comparison.csv。
- 成本与退市情景：factor_robustness_scenarios.csv。
- 运行口径：robustness_meta.json。

promotion_gate.csv / promotion_decision.json 给出预先声明门槛的逐因子证据。
