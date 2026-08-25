# 基金持仓数量因子 Final OOS 增量实验

日期：2026-08-24
状态：诊断性研究，不是晋级证据。

## 研究问题

在保持技术特征、PIT full-market universe、月频、Top-5、XGBoost、date-equal
样本权重和 20% 尾部 Final OOS 切分不变的前提下，基金持仓数量水平和事件
变动是否带来增量信息？

四个正式臂为：

1. baseline：技术特征；
2. +fund_count：加 fund_count_holding_stock；
3. +fund_count_qoq_change：加 fund_count_holding_stock_qoq_change；
4. +both：同时加入两个字段。

另外做了按月横截面置乱的 +both_placebo，以及 3 个额外 placebo seed。

## 数据和口径

- PIT universe：`$DATA_PLATFORM_ROOT/assets/universe/a_share_all_full_by_date.csv`
- 最新 full fund asset：
  `$DATA_PLATFORM_ROOT/assets/tushare/a_share/fund_portfolio_features/a_share_all_fund_portfolio_features_20260821/data`
- fund asset 事件范围：2015-01-20 至 2026-07-22
- daily clean：a_share_all_20150101_20260824_daily_clean
- 月度面板：566,386 行、5,781 只股票、139 个 universe 日期
- panel 主键重复：0
- fund state observed：96.6%
- fund state age：中位数 31 天，P90 97 天，P99 706 天
- 原始字段缺失：level 3.4%，qoq change 3.9%；按月横截面中位数填补
- 四个正式臂的 train rows / test rows 完全一致：387,344 / 138,681

为了匹配项目原生 modeling_dataset，技术特征先做 complete-case 过滤，再做
1% winsorize + robust 横截面变换；不是先把早期缺失值变成 0。

本 runner 的 complete-label model dates 是 2015-07-31 至 2026-06-30，
Final OOS 是 2024-05-31 至 2026-06-30，共 26 个日期。原 Final OOS 文字证据
写的是 2024-06-28 至 2026-07-30/31；这是一项需要用 canonical pipeline
复核的日期边界差异，因此下面结果应视为高可比诊断，而不是替代原生 artifact。

## 正式臂结果

金额列按 daily amount × 1,000 转成 CNY。10/20/30bp 的净收益使用项目 turnover
诊断的近似成本：首期单边成本，之后按 2 × bps × Top-5 名称换手。

| arm | Rank IC | Q5-Q1 | 10bp 总收益 | 10bp Sharpe | 20bp Sharpe | 30bp Sharpe | Top-5 换手 | capacity p10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 10.374% | 1.981% | 194.99% | 1.333 | 1.284 | 1.235 | 94.62% | 0.75x |
| +fund_count | 8.601% | 1.738% | 96.65% | 0.922 | 0.868 | 0.813 | 97.69% | 0.45x |
| +fund_count_qoq_change | 9.917% | 1.927% | 153.24% | 1.105 | 1.058 | 1.012 | 93.85% | 0.48x |
| +both | 8.468% | 1.680% | 106.33% | 0.903 | 0.856 | 0.810 | 95.38% | 0.74x |
| +both_placebo | 9.475% | 1.758% | 163.93% | 1.178 | 1.129 | 1.080 | 98.46% | 0.99x |

相对 baseline：

- level：Rank IC -1.773 个百分点，Q5-Q1 -0.243 个百分点，10bp Sharpe
  -0.411；
- qoq change：Rank IC -0.457 个百分点，Q5-Q1 -0.054 个百分点，10bp Sharpe
  -0.228；
- both：Rank IC -1.906 个百分点，Q5-Q1 -0.301 个百分点，10bp Sharpe
  -0.430。

因此 qoq change 虽然比 level 温和，但在这组同口径 OOS 中没有增量改善。

## 阶段和 placebo

OOS 三段的 Q5-Q1：

| 阶段 | baseline | qoq change | level |
|---|---:|---:|---:|
| early | 1.972% | 1.914% | 1.598% |
| mid | 2.676% | 2.527% | 2.292% |
| recent | 1.209% | 1.408% | 1.385% |

qoq change 只在最近约 9 个月局部超过 baseline，前两个阶段都没有超过，
不满足“最近阶段 + 至少两个历史阶段同方向”的门槛。

直接按原始基金字段做跨期因子诊断时，qoq change 的 Rank IC 在
2015-2019、2020-2023、2024-2026 分别为 -3.99%、-0.67%、-1.19%，
Q5-Q1 分别为 -0.773%、-0.126%、-0.074%。这与之前用“月末持仓水平差分”
得到的弱正向结果不是同一个变量：资产中的 qoq 字段是在事件行上按股票
对持仓状态做 diff，不能与月末 as-of 状态差分混用。

3 个额外 placebo seed 的结果如下：

| seed | Rank IC | Q5-Q1 | 10bp 总收益 | 10bp Sharpe |
|---:|---:|---:|---:|---:|
| 1 | 9.390% | 1.841% | 291.66% | 1.559 |
| 2 | 9.419% | 1.746% | 85.99% | 0.819 |
| 3 | 9.170% | 1.656% | 469.22% | 2.073 |

置乱字段仍能得到相当强的 OOS 结果，说明 Top-5、高换手和小样本下的技术
模型本身足以产生很大的结果波动；不能把 +fund 臂的表现归因于基金信息。

## 结论和下一步

结论：四臂均未通过基金因子的增量门槛。当前不建议把基金持仓字段加入主模型，
也不建议继续投入 Top10 资产工程。

建议保留两条低成本后续路线：

1. 先用 canonical strategy-pipeline 固定同一 OOS 日期边界，复核本 runner
   与原生 baseline 的数值差异，尤其是最后一个完整月；
2. 如果仍需利用 level 字段，只做一个预注册的拥挤度惩罚实验（明确负向方向），
   把它作为风险/容量控制变量，而不是正向 alpha。

在 canonical 复核确认之前，不应将 qoq change 的最近阶段局部改善解释成稳定
信息增量。

## 可复现产物

- runner：
  strategy-research/experiments/style_factors/fund_count_final_oos_ablation_20260824.py
- 全量面板和结果目录：本机临时目录 `fund_count_final_oos_ablation_20260824_v3`，不纳入版本库
- 主要文件：metrics.csv、periods.csv、raw_factor_regimes.csv、quality.json、
  summary.json
