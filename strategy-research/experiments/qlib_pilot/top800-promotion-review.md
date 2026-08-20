# top800 晋升评审（2026-08-10）

> 范围：top800 信号 vs 全市场 baseline，promotion-gate 评审
> 状态：reviewable（v2，从 v1 的 rejected 提升，无 hard failure）
> 配置：top800_promotion_gate.yml（v1）、top800_promotion_gate_v2.yml（v2）
> 报告：artifacts/reports/top800_promotion_gate.json、top800_promotion_gate_v2.json

## 评审结论

**v1（数据窗 2022 起）**：rejected——DSR trials 不足（2<10，数据仅 198 天），
非信号问题，统计功效不足。

**v2（数据窗扩展至 2019 起）**：reviewable——补数据窗口后无 hard failure，
eval IC 由 -0.003 转 +0.086（IR 1.17），Long-short 转正（+2.35%），评审从
rejected 提升到 reviewable。

## v2 证据对比

| 证据 | candidate (top800) | baseline (全市场) | 判定 |
| --- | --- | --- | --- |
| eval IC | **+0.086** (IR 1.17) | +0.068 | 两者均显著为正 |
| Long-short | **+2.35%** | +1.13% | candidate 胜 |
| 回测 Sharpe | **1.16** | 0.56 | candidate 大幅胜出 |
| benchmark 超额 | +22.40% | -8.89% | candidate 大幅胜出 |
| benchmark IR | **0.90** | - | candidate 强正 |
| CPCV sharpe_median | **1.01** | 0.88 | 均正 |
| DSR | 0.756 | - | 接近 0.8 |
| exposure breach | **2** | 4 | candidate 更温和 |

## 剩余软失败（4 项，均可改进，非方向错误）

- max_backtest_avg_turnover：0.987，要求 ≤0.9（月度调仓换手偏高）。
- max_cpcv_drawdown_p10：0.365，要求 ≤0.35（尾部回撤略超）。
- max_exposure_screen_breach_count：2（size 暴露 -2.97，quality 数据缺失）。
- min_dsr：0.756，要求 ≥0.8。

## 关键解读

1. **补数据窗口是决定性改进**：eval IC 从 -0.003 变 +0.086（IR 1.17），评审从
   rejected 提升到 reviewable。印证"训练窗口长度决定信号质量"（见
   top800-decay-diagnosis）。
2. **candidate 全面优于 baseline**：Sharpe 1.16 vs 0.56、超额 +22.4% vs -8.9%、
   exposure breach 2 vs 4。top800 过滤同时提升收益和降低暴露。
3. **暴露是读数问题**：candidate 暴露（-2.97）比 baseline（-3.65）温和，组合持
   中盘股，相对 cap 加权基准显示"偏小"，非真实小盘赌注。top800 降低而非引入
   小盘风险（v1 同结论）。
4. **v1 的 rejected 是诚实的**：数据窗口短导致 DSR 功效不足，与信号有效性无关。

## 从 reviewable 到 promotable 的路径

1. **降换手**：avg_turnover 0.987 → 0.9 以下（buffer/滞后调仓/半衰期）。
2. **压尾部回撤**：maxDD_p10 0.365 → 0.35（降集中度或加波动率目标）。
3. **补 quality 数据**：quality coverage=0 是因子列缺失，补数据消除该 breach。
4. **提升 DSR**：0.756 → 0.8（更多数据或更稳信号）。
5. **size 暴露**：确认是基准尺度问题后，用组合约束或基准选择处理（独立决策）。
