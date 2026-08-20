# top800 因子归因分析（2026-08-10）

> 方法：顶层 style_factors OLS 归因，top800 v2 策略日收益回归到 15 因子 long-short
> 收益；重叠窗口 2025-01 到 2026-05（338 天）。结果：artifacts/style_analysis/strategy_attribution.json

## 整体归因

| 指标 | 值 |
| --- | --- |
| R² | 0.5181 |
| 期间收益 | +57.43% |
| **annual_alpha** | **-11.51%** |
| size β | +0.42 |
| beta β | -2.17 |
| growth β | +1.31 |

## 逐年 alpha 与主要贡献

- **2025**（+39.24%）：beta β=-2.21 贡献 +40.35（偏低贝塔）、growth +14.86、
  size -8.33；annual_alpha **-6.94%**。
- **2026**（+13.07%）：growth +18.93、beta +15.02；annual_alpha **-37.67%**。

## 核心结论

1. **size 暴露方向与 exposure_screen 读数相反**：exposure_screen 显示"偏小盘"
   （-2.97，相对 cap 加权基准），OLS 归因 size β=+0.42 显示偏大盘。两者基准不同，
   归因 β 更能反映暴露对收益的真实影响。
2. **策略收益主要来自因子暴露，不是选股 alpha**：2025/2026 alpha 均为负（-6.94%/
   -37.67%），R² 0.52 说明因子解释过半收益。最大贡献是 beta（偏低贝塔，贡献
   +40%）与 growth（+15~19%）。
3. **eval IC +0.086 部分反映风格暴露**：IC 正说明"选对风格"，但风格本身在
   2025-2026 逆风（低贝塔/成长走弱），alpha 被因子收益吞噬。纯选股能力为负，
   但策略靠因子暴露赚钱，这是风格策略的常态。
4. **优先级调整**："修复 size 暴露"下调——策略实际偏大盘（β+0.42）而非小盘赌注；
   beta/growth 暴露才是主要收益来源，若担忧风格回撤这才是需关注的暴露。

## 文件

strategy_attribution.json、strategy_attribution_yearly.csv、style_factor_yearly_matrix.csv
