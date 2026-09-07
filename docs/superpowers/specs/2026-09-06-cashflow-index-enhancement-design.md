# Cashflow Index Enhancement Research Design

**Date:** 2026-09-06  
**Status:** Approved for planning  
**Scope:** Research comparison only; no live trading or production eligibility change

## Goal

把现金流策略从“现金流股票池 + ML 选 Top-K + 等权”扩展为可比较的组合构造实验，明确收益来自选股、权重方式还是调仓方式。

## Strategy boundary

`quant-research` 保留现金流定义、PIT 数据、ML 信号、研究排名和私有实验参数。它输出一个最小的候选表，至少包含：

```text
signal_date, symbol, selection_rank, ml_score, benchmark_weight
```

`quant-platform` 只提供公开、可复用的组合构造与调仓机制，不包含现金流名称、私有数据源或策略晋升结论。

## Portfolio variants

同一份候选和同一份 ML 排名必须支持以下三个 variant：

1. `topk_equal_weight`
   选择 Top-K，每只股票等权。保留为当前方法的基线。
2. `topk_benchmark_weight`
   选择 Top-K，使用现金流基准权重后重新归一。用于隔离等权带来的规模暴露。
3. `benchmark_ml_tilt`
   保留完整基准成分，用 ML 分数对基准权重做连续超低配。初始确定性规则为：

   ```text
   raw_weight_i = benchmark_weight_i * exp(tilt_strength * zscore(ml_score_i))
   final_weight_i = raw_weight_i / sum(raw_weight)
   ```

   `tilt_strength` 必须是显式配置；零值必须精确复制基准权重。公共层不假设现金流基准是市值加权，基准权重由私有研究输入提供。

## Rebalance variants

三种组合构造都使用同一套调仓日历：

- `monthly`: 每月最后一个可用交易日；
- `quarterly`: 每季度最后一个可用交易日；
- `d11_h5`: 五个互斥 sleeve，按稳定的交易日相位错开，每个交易日只更新一个 sleeve，完整组合目标在五个交易日内完成；

`d11_h5` 的信号 vintage 与执行日期必须分离。一次研究信号产生一个固定目标，五个 sleeve 分批执行，不允许每个 sleeve 使用重新计算的 ML 信号。若输入日历无法形成五个有效 sleeve，必须失败关闭并给出诊断。

## Public interfaces

公共平台新增通用接口，具体名称在实施计划中锁定：

- 从排名、基准权重和 variant 配置构造目标权重；
- 根据交易日历生成 monthly、quarterly 和固定相位 staggered rebalance events；
- 计算 portfolio return、benchmark return、excess return、tracking error、information ratio、turnover、active share 和基础行业/规模暴露占位字段；
- 输出带 schema version、输入哈希、variant、rebalance policy 和确定性排序的研究结果。

公共接口只接受结构化 DataFrame 或已版本化的公共 contract，不读取私有仓库模块。

## Private research integration

私有仓库新增一个 cashflow construction experiment runner：

- 读取现有现金流研究排名及基准权重；
- 对三个 portfolio variant 和三个 rebalance variant 运行同一时间窗口；
- 保留现有 PIT、reconstructed-PIT、research-only 和 `eligible_for_live=false` 状态；
- 写出逐日收益、持仓/目标权重、换手和暴露归因；
- 生成一份矩阵摘要，方便比较同一 ML 信号下的构造差异。

## Acceptance criteria

- Top-K 等权结果与现有基线在相同输入下保持一致；
- `benchmark_ml_tilt` 在 `tilt_strength=0` 时与基准逐日权重一致；
- 所有 variant 的权重总和为 1，且不产生负权重；
- D11-H5 的五个 sleeve 使用同一个信号日期和目标快照，并在五个执行日内完成一次目标更新；
- 所有实验结果可按 variant、rebalance policy 和 signal vintage 复现；
- 报告至少包含绝对收益、基准收益、超额收益、TE、IR、换手率和 Active Share；
- 不改变任何 live promotion gate，不发送真实订单，不向公共平台写入现金流策略逻辑。

## Failure behavior

- 缺少 `symbol`、`benchmark_weight`、`selection_rank` 或 `ml_score` 时拒绝运行；
- 基准权重有重复、负值、非有限值或权重和不为正时拒绝运行；
- 调仓日历为空、D11-H5 无法构成五个 sleeve 或目标快照不一致时拒绝运行；
- 任何失败都必须保留可读错误和结构化诊断，不返回看似有效的部分结果。

## Non-goals

- 不决定最终生产策略；
- 不把 Top-K 等权替换成指数增强；
- 不把现金流基准权重改成市值权重；
- 不在本阶段接入 Feishu、券商或真实价格执行；
- 不迁移整个 `research-workspace` 的未提交执行模拟改动。
