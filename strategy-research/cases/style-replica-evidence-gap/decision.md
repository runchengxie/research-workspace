# 决策记录：StyleReplica 证据缺口

- case_id: style-replica-evidence-gap
- as_of: 2026-08-18
- decision.status: no_view
- 结论：职责拆分成立，但因子有效性无证据支撑。

## 判断

`style_replica.factor_semantics_owner_split` 判断把因子语义归 alpha、组合语义归 portfolio、表现层归
strategy-research，这是对职责拆分的如实登记，属于事实类判断。但该判断不代表因子有效。

`style_replica_a80_b20.json` 证据包如实登记七项检查全部 missing：
pit、walk_forward、benchmark_matrix、cost、final_oos、cpcv、regime。

## 决策

按缺数据即放弃判断的原则，因子有效性维度 abstain，decision.status 取 no_view。
职责拆分与因子有效性是两件事，不能相互代替。
