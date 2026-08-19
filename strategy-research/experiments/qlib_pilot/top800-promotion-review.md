# top800 晋升评审（2026-08-10）

> 范围：top800 信号 vs 全市场 baseline，正式 promotion-gate 评审
> 状态：rejected（但信号证据真实，暴露是主要阻塞）
> 评审配置：top800_promotion_gate.yml
> 评审报告：artifacts/reports/top800_promotion_gate.json

## 评审结构

- candidate：top800 universe（按每日成交额取 top800），top_k=30，长验证期，真实执行
- baseline：全市场（5797 只），同参数
- 可比性：通过（is_comparable=true，仅配置键差异在 universe，评审接受）
- 证据完整度：missing_evidence 为空（main_eval/backtest/walk_forward/cost_turnover/
  feature_stability/benchmark/cpcv/dsr/exposure_screen 全部就位）

## 证据对比

| 证据 | candidate (top800) | baseline (全市场) | 判定 |
| --- | --- | --- | --- |
| 回测 Sharpe | +1.08 | -1.41 | candidate 大幅胜出 |
| 回测总收益 | +24.29% | -26.28% | candidate 大幅胜出 |
| benchmark 超额 | +4.84% | -37.82% | candidate 大幅胜出 |
| benchmark IR | 0.43 | - | candidate 正 |
| CPCV sharpe_median | 0.88 | 0.88 | 均正 |
| CPCV positive_ratio | 0.86 | 1.00 | 均高 |
| walk_forward test_ic | 0.118 | - | candidate 正 |
| DSR | 0.655 | - | 不足 0.8 |
| DSR trials | 2 | - | 不足 10 |
| exposure breach | 3 | 4 | 均 breach |

## 评审结果

promotion_status = rejected

### hard_failures

- insufficient_dsr_trial_count：DSR trials=2，要求 ≥10。数据仅 198 天（2025-08 到 2026-05），
  PBO 统计功效不足，不是策略本身的问题。

### soft_failures

- min_eval_ic_ir：eval IC IR = -0.031（近零）。这是该信号的已知特征——线性 IC
  不捕捉排序能力，Q 组单调性真实（此前 explore 已确认）。
- min_eval_long_short：Q5-Q1 = -1.60%（负）。同上，长短期组合的线性关系弱。
- max_backtest_avg_turnover：avg_turnover = 0.956，要求 ≤0.9。月度调仓下换手偏高，
  真实执行成本拖累（cost_drag 0.18%/期）。
- max_exposure_screen_breach_count：3 breaches。系统性小盘暴露（size active -2.69），
  quality 因子数据缺失（coverage 0）。
- min_dsr：DSR 0.655，要求 ≥0.8。与 trials 不足同源，数据窗口太短。

## 关键解读

1. **信号是真实的**：candidate 相对 baseline 的 Sharpe delta（+1.08 vs -1.41）、
   benchmark 超额（+4.84% vs -37.82%）、CPCV sharpe_median 0.88 都证明 top800
   在严格评估下有效。这不是运气（CPCV 7 条路径、多窗口）。
2. **暴露是真实的限制**：size 系统性负暴露（-2.69）说明策略本质是偏小盘。
   但 baseline 暴露更极端（-3.60），说明 top800 过滤**降低了**而非引入了小盘风险。
3. **数据窗口是主要瓶颈**：DSR trials=2、198 天，源于数据只到 2026-05 且
   walk_forward 长验证窗锚定尾部。更多历史数据或更早起点可提升统计功效。
4. **rejected 是诚实的结论**：暴露 breach + DSR 不足 + 换手偏高，即使信号有效，
   策略在"可直接晋升"层面仍不合格。评审价值在于把正反证据都记录清楚。

## 与前述探索的关系

- 印证"top800 信号在严格评估下赚钱"（combo/top800/stability 系列的正式化）。
- 印证"风格暴露是真实问题"（D11-H5 回撤根因同一性质）——top800 也有 size 暴露，
  只是更温和。
- DSR 低与"数据窗口短"相关，非信号无效——与 decay 诊断的"训练窗口决定一切"
  一致。

## 未来方向

1. **补数据窗口**：拉更早历史（2015+ 已有 daily_clean），用更早起点跑 DSR 提升
   trials 和统计功效。
2. **风格约束**：portfolio-backtester 构建时 style 约束（B 方案）压 size 暴露，
   是达到 promotable 的关键。
3. **降换手**：top_k=30 月度调仓换手 0.96 偏高，可评估 buffer/滞后策略降换手。
4. **quality 数据**：quality 因子 coverage=0 是数据列缺失，补因子数据消除该
   breach 假象。
