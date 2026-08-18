# 决策记录：DailyWatch20 晋级就绪度

- case_id: daily-watch20-promotion-readiness
- as_of: 2026-08-18
- decision.status: no_view
- 结论：当前证据不足以判定 DailyWatch20 是否满足生产级验收。

## 判断

DailyWatch20 在短窗口 walk-forward（15 窗口，sharpe_median）与 CPCV（6 组）上呈现正的排序能力，
基准考试表（benchmark ladder）给出 a_share_all_equalw/h5 与 a_share_top800/h20 两个通过单元。
这些支撑 `daily_watch20.alpha_persistence` 判断的短期排序能力。

但以下缺口使晋级判断不成立：

- final_oos 仅以书面替代声明代替真实最终样本外，不构成生产级。
- cost 长窗口成本压力证据 pending，短窗口 30bps 假设不足以外推。
- regime 未按牛市、熊市、震荡市分别报告表现。
- pit 财务报表 PIT 未启用（statement_features_enabled=false）。

## 决策

按缺数据即放弃判断的原则，晋级维度 abstain，decision.status 取 no_view。
待 E2 长窗口晋级证据（真实 final_oos、成本压力、分状态表现）补齐后重新评审。
