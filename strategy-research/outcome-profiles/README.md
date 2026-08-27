# Outcome Profiles

本目录保存 `outcome_profile.v1` 决策结果目标。对象描述研究者希望某类决策结果满足哪些目标、约束和诊断维度，用于把研究问题从单一预测指标推进到可检查的决策结果。

Outcome profile 描述偏好和约束，不描述市场预测。预测分数、预期收益或预测分布仍由 alpha owner 产生。目标是否在当前证据下可行，需要经过冻结样本外、成本、容量、执行和市场状态等研究证据检验，不能由本对象自行宣称。

文件名必须与 `outcome_profile_id` 一致：

```text
strategy-research/outcome-profiles/<outcome_profile_id>.json
```

每个 `metrics` 条目需要声明 `name`、`direction`、`role` 和 `unit`。`role=constraint` 时还必须提供 `operator` 与有限数值 `threshold`。支持的 operator 为 `lt`、`lte`、`gt` 和 `gte`。

本层不会把多个 metric 合成为单一 utility、confidence 或综合评分。多个目标存在冲突时，研究应用应保留 Pareto trade-off 或明确记录 `no_view`，不要用临时权重把冲突藏起来。

校验入口：

```bash
python scripts/decision_governance_check.py
python scripts/decision_governance_check.py --outcome-profile strategy-research/outcome-profiles/<id>.json
```
