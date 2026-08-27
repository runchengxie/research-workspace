# Outcome-first 决策研究设计

## 目标

在现有 prediction → portfolio → execution → evidence 链条上增加 outcome-first 决策层。研究者先声明希望决策结果满足哪些目标和约束，再用冻结的样本外协议判断候选策略是否在当前证据下可行。

本设计借鉴 Carr 与 Sturm 的 Distribution Builder 思想，但不移植 GBM、Skorokhod embedding 或 Azéma–Yor 作为生产假设。工作区只采用目标结果、经验可行性、非支配比较和路径依赖退出四个思想。

## 边界

- `strategy-research` 维护 outcome profile 的语义、引用和治理，不承担计算。
- `portfolio-backtester` 维护通用结果分布和持仓路径指标，不包含 DailyWatch20 参数或策略判断。
- `strategy-app` 维护 decision receipt、Pareto 比较和 DailyWatch20 专用 path-aware exit 研究 overlay。
- `alpha-research` 的预测、CPCV、PBO 与过拟合诊断保持现有职责。本轮不增加新的 alpha 接口。
- 本轮不实现通用 barrier engine、DRO、MILP、Skorokhod embedding 或生产退出策略。

## Outcome profile

新增 `outcome_profile.v1`。它描述决策偏好，不描述市场预测。

核心字段：

- `schema_version` 固定为 `outcome_profile.v1`
- `outcome_profile_id` 为稳定标识
- `strategy_id` 指向策略身份
- `decision_type` 为 `entry`、`exit`、`portfolio`、`allocation`、`execution` 或 `custom`
- `statement` 为人类可读目标说明
- `status` 为 `proposed`、`active`、`superseded` 或 `retired`
- `as_of` 为日期
- `metrics` 为非空列表

每个 metric 包含：

- `name`
- `direction` 为 `higher_is_better` 或 `lower_is_better`
- `role` 为 `objective`、`constraint` 或 `diagnostic`
- `unit`
- constraint 额外要求 `operator` 与有限数值 `threshold`

`research_case.v1` 增加可选 `outcome_profiles` 引用。校验器确认引用文件存在，文件名与 `outcome_profile_id` 一致，并拒绝重复 metric 名称、错误枚举、非有限阈值和不完整 constraint。

Outcome profile 不合成单一 utility 或总分。它允许多个 objective 与 constraint 同时存在。

## 通用 outcome metrics

`portfolio-backtester` 新增通用结果分布接口，输入已经实现的交易或持仓结果，不预测未来。

第一版提供：

- observations
- mean return
- median return
- loss probability
- 5%、25%、75%、95% quantile
- 5% CVaR
- MFE 均值与中位数
- MAE 均值与中位数
- peak giveback 均值与 90% quantile
- holding period 均值、中位数与 90% quantile

接口失败关闭。空输入、非有限数值、非法 holding period 或列长度不一致均报错。CVaR 定义为 return 小于等于对应 quantile 的样本均值。

这些指标属于通用回测结果诊断，因此由 `portfolio-backtester` 持有。公开入口和包级 smoke test 同步更新。

## Decision receipt 与 Pareto 比较

`strategy-app.decision_evaluation` 保留现有 metric map 契约，并增加 `pareto_relation`：

- `candidate_dominates`
- `baseline_dominates`
- `equivalent`
- `tradeoff`

比较只使用声明过 direction 的 decision metrics。所有 direction-normalized delta 非负且至少一项严格为正时 candidate dominates。全部非正且至少一项严格为负时 baseline dominates。全部为零时 equivalent，其余情况为 tradeoff。

系统不把多个 metric 压成单一综合分。

## DailyWatch20 path-aware exit challenger

第一版是研究 overlay，不修改生产策略，不重新训练模型，也不改变 entry。

输入是一组 baseline trade episodes。每个 episode 从 baseline entry 开始，以 baseline exit 为最后一行。每行必须有：

- `trade_id`
- `trade_date`
- `price`
- `score`
- `uncertainty`

`score` 与 `uncertainty` 都要求位于 `[0, 1]`。uncertainty 必须由调用方提供，禁止从 score 伪造。

冻结 policy 包含：

- `base_drawdown`
- `min_drawdown`
- `signal_decay_penalty`
- `uncertainty_penalty`
- `age_penalty_per_day`
- `grace_days`

对每个观察日计算：

```text
signal_decay = max(entry_score - current_score, 0)
age_excess = max(holding_days - grace_days, 0)
raw_limit = base_drawdown
            - signal_decay_penalty * signal_decay
            - uncertainty_penalty * current_uncertainty
            - age_penalty_per_day * age_excess
allowed_drawdown = clip(raw_limit, min_drawdown, base_drawdown)
drawdown_from_peak = 1 - current_price / running_peak
```

当 `drawdown_from_peak >= allowed_drawdown` 时退出。若从未触发，则沿用 baseline 最后一行退出。

Challenger 只允许更早退出。退出后不在该 episode 内重新配置资本，因此第一版测量纯 exit effect，避免把再投资选择混入因果比较。

每个 trade 输出 baseline/challenger exit date、return、holding days、MFE、MAE、peak giveback、trigger threshold 和 exit reason。通用分布汇总由 `portfolio-backtester` 完成。

## 防过拟合协议

- 单次研究 run 只接受一个冻结 `PathAwareExitPolicy`。
- 第一版不提供参数 grid search API。
- receipt 记录完整 policy 和内容身份。
- 任何候选晋级仍需使用现有 walk-forward、CPCV、PBO、多重检验、成本与 regime 证据。
- 参数若来自探索阶段，必须在新的冻结样本外窗口验证，不能把同一窗口的最优参数当作确认性结果。
- outcome profile 无候选满足时允许输出 `no_view` 或经验不可行，不通过继续调参强行制造 pass。

## P4 门槛

只有 DailyWatch20 path-aware challenger 在冻结样本外、成本、regime 与过拟合控制下显示稳定增量后，才考虑把通用 path-state barrier primitive 下沉到 `portfolio-backtester`。本轮不创建该通用接口。

## 兼容性

- 现有 research cases 无需迁移，`outcome_profiles` 为可选字段。
- 现有 decision receipt 调用方式保持兼容，只增加确定性派生字段。
- 现有 portfolio/backtest 输出保持不变，新 metrics 为显式调用。
- DailyWatch20 production policy 与当前 incumbent requalification 不变。
