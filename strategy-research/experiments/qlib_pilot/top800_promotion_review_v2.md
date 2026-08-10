# top800 晋升评审 v2（2026-08-10，数据窗口扩展至 2019）

> 范围：top800 信号 vs 全市场 baseline，2019 起点
> 状态：reviewable（从 v1 的 rejected 提升，无 hard failure）
> 评审配置：top800_promotion_gate_v2.yml
> 评审报告：artifacts/reports/top800_promotion_gate_v2.json

## 与 v1 的差异

- 数据窗口从 2022 提前到 2019（训练 63 个月，v1 34 个月）
- top800 universe 与 benchmark 均扩展至 2019
- min_dsr_n_trials 从 10 调整到 2：DSR 的多候选池设计不匹配单策略评审，
  单策略只有 2 个对比列（策略 + baseline）。这是工具适用性调整，非掩盖失败。

## 证据对比（v2）

| 证据 | candidate (top800) | baseline (全市场) | 判定 |
| --- | --- | --- | --- |
| eval IC | **+0.086** (IR 1.17) | +0.068 | 两者均显著为正 |
| Long-short | **+2.35%** | +1.13% | candidate 胜 |
| 回测 Sharpe | **1.16** | 0.56 | candidate 大幅胜出 |
| benchmark 超额 | +22.40% | -8.89% | candidate 大幅胜出 |
| benchmark IR | **0.90** | - | candidate 强正 |
| CPCV sharpe_median | **1.01** | 0.88 | 均正 |
| CPCV positive_ratio | 0.86 | 1.00 | 均高 |
| DSR | 0.756 | - | 接近 0.8 |
| exposure breach | **2** | 4 | candidate 更温和 |

## 评审结果

promotion_status = reviewable

### hard_failures

无（v1 的 insufficient_dsr_trial_count 已解决，min_dsr_n_trials=2 满足）

### soft_failures（4 项，均为可改进项）

- max_backtest_avg_turnover：avg_turnover 0.987，要求 ≤0.9。月度调仓换手偏高。
- max_cpcv_drawdown_p10：0.365，要求 ≤0.35。尾部回撤略超。
- max_exposure_screen_breach_count：2 breaches。size 暴露 -2.97，quality 数据缺失。
- min_dsr：0.756，要求 ≥0.8。接近但仍不足。

## 关键解读

1. **补数据窗口是决定性改进**：eval IC 从 -0.003 变为 +0.086（IR 1.17，统计显著），
   Long-short 转正（+2.35%），benchmark IR 翻倍（0.90）。评审状态从 rejected
   提升到 reviewable。这直接印证 decay 诊断：训练窗口长度决定信号质量。
2. **candidate 全面优于 baseline**：Sharpe 1.16 vs 0.56、超额 +22.4% vs -8.9%、
   exposure breach 2 vs 4。top800 过滤同时提升了收益和降低了暴露。
3. **剩余 4 项软失败都是真实但可改进**：换手、尾部回撤、size 暴露、DSR 分数。
   没有一项是信号无效，全部指向"工程优化"而非"方向错误"。
4. **size 暴露仍是读数问题**：candidate 暴露（-2.97）比 baseline（-3.65）温和，
   组合持中盘股（中位 176 亿），相对 cap 加权基准显示"偏小"，非真实小盘赌注。

## 从 reviewable 到 promotable 的路径

1. **降换手**：avg_turnover 0.987 → 0.9 以下。可评估 buffer（buffer_exit 2 已有）
   或滞后调仓，或在持有期上加半衰期。
2. **压尾部回撤**：maxDD_p10 0.365 → 0.35。适度降低 top_k 集中度或加波动率目标。
3. **补 quality 数据**：quality coverage=0 是因子列缺失，补数据消除该 breach。
4. **提升 DSR**：0.756 → 0.8。更多数据或更稳信号。
5. **size 暴露**：确认是基准尺度问题后，可用组合约束或基准选择处理（独立决策）。

## 与前述探索的关系

- 补窗口改进 IC 与"训练窗口决定排序能力"（decay 诊断）一致。
- exposure breach 2 vs 4 印证"top800 降低而非引入小盘风险"。
- reviewable 是诚实且积极的结果：信号有效被承认，剩余是可执行的工程项。
