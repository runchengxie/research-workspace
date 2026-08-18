# 决策记录：热点板块选股 PIT 约束

- case_id: hotsector-pit-discipline
- as_of: 2026-08-18
- decision.status: no_view
- 结论：非 PIT 的多臂回顾回执不足以支撑排序能力可信的判定。

## 判断

hotsector 的唯一通过项 walk_forward 来自 `hotsector-numeric-v2-retrospective-receipt-20260717.json`，
该回执 `strict_point_in_time=false`、`research_only=true`、`eligible_for_live=false`。
因此 `hotsector.point_in_time_discipline` 判断如实登记：未启用 PIT 时间点约束。

## 决策

按缺数据即放弃判断的原则，排序能力有效性维度 abstain，decision.status 取 no_view。
PIT 回测出具之前，禁止把该非 PIT 回执当作晋级证据。
