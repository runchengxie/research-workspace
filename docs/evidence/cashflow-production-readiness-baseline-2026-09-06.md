# 现金流策略生产候选基线（2026-09-06）

## 结论

现金流策略当前可以开始工程化推进，但只能推进到“研究 shadow / 飞书测试群候选”，不能直接进入正式生产群。

本基线将候选身份暂定为：

```text
cashflow_quality_top50_v1
```

候选规则：980092 规则影子股票池、质量过滤、价值陷阱过滤、自由现金流加权、单股权重上限 10%、季度调仓。

## 当前证据

| 门禁 | 当前状态 | 权威证据 | 影响 |
| --- | --- | --- | --- |
| 严格 PIT 与核心资格字段 | 未通过 | `strategy-research/research/experiments/cashflow_indices/decisions/980092_final_decision_20260905.md` | 不能宣称完整历史可执行 |
| 统一四臂样本外比较 | 未验证 | 同上 | 不能证明相对 DailyWatch20/D11-H5 的稳定增量 |
| 成本与容量 | 仅筛查通过 | 同上 | 仍需真实成交金额、冲击和容量模型 |
| 风格、集中度和子区间 | 诊断性通过 | `strategy-research/research/experiments/cashflow_indices/current_status_980092.md` | 需要冻结版本后重跑 |
| 生产应用入口 | shadow runner 已建立 | `strategy-app/src/strategy_app/cashflow/` | 尚未因研究门禁通过而获得生产资格 |
| 不可变发布与回执 | shadow contract 已建立 | `strategy-pipeline/src/strategy_pipeline/cashflow_publication.py` | 需要接入实际调度链并连续运行 |
| Feishu 测试群推送 | adapter 已建立，未真实发送 | `/home/richard/code/market-intel/src/a_share_daily/cashflow_delivery.py` | 需要显式测试群、凭证和 dry-run/回执验证 |

readiness 现在应由 `research_contracts.cashflow_readiness.build_cashflow_readiness_payload()` 从
evidence bundle 生成，而不是手工拼接。该函数会重新计算 bundle hash，并检查
所有灰度 gate 的 evidence 路径；现在还会复用 canonical promotion validators，
拒绝只有 `outcome=pass` 但缺少窗口、成本情景、冻结 OOS、CPCV、regime 或容量字段
的伪通过记录，并校验 `source_artifacts` 中每个外部研究产物的 SHA-256。当前
现金流 bundle 的 6 个 source artifact hash 均匹配，但由于研究 gate 仍是
partial/pending，整体 attestation 仍为 `unverified`。

## 数据源审计补充（2026-09-06）

市场数据平台已经存在可复用的 sealed PIT fundamentals v2 资产，且包含
`operating_cashflow`、`free_cashflow`、质量字段和 `available_date`。这说明
“重新接一套数据源”不是当前的主要问题；当前问题是：

- `20260906` vintage 已完成 raw/normalized/PIT 构建并通过市场数据平台的
  immutable seal 校验；其 manifest freshness valid through 为 `20260909`，因此
  当前日期的数据新鲜度门禁已通过，但这不等于严格 PIT 准入已通过。
- 最新 PIT schema 使用 `n_cashflow_act` / `n_income` 字段；audit 已显式支持
  该别名，但不会因为字段别名被识别就放宽 PIT 或修订安全门禁。
- `20260906` 审计回执
  `strategy-research/research/evidence/cashflow_pit_input_audit_20260906.json`
  明确标注 `historical_revision_safe: false`，唯一当前 blocker 为
  `historical_revision_not_safe`；该 vintage 只能作为 reconstructed PIT / shadow
  输入，不能据此把严格 PIT 门禁改成通过。
- 还需要把现金流候选的实际 quality/value-trap/FCF 计算接到这套 PIT 事件流，
  形成按 `source_date` 可重放、带输入哈希和 freshness 证明的 feature artifact。
- 当前 materializer 的 canonical 输出还不能直接喂给 `strategy-app`：runner
  要求 `selection_score`、`free_cash_flow`、`eligible`、`quality_pass` 和
  `value_trap_pass`。其中 FCF 口径以及 quality/value-trap 的冻结规则必须先登记
  在策略 policy 中，再由独立 feature builder 生成；不能把原始 PIT 行或默认布尔值
直接当成候选特征。

新增的 `cashflow_pit_features.v2` contract 还会要求
`available_date <= source_date`，并验证 immutable、historical revision-safe
以及 manifest identity。它不会从 raw PIT rows 猜测或填充策略字段。对现有
980092 shadow panel 的实测结果是 blocked：该 panel 缺少
`available_date`、`selection_score`、`eligible`、`quality_pass` 和
`value_trap_pass`，因此不能直接接入每日飞书目标生成。

已新增 `cashflow_quality_feature_builder.v1`，并把旧研究脚本中曾经混用的
两个字段拆开登记：原始 `cfo_to_operating_profit_ratio >= 0.30` 才能进入基础
候选池；随后在同一 source date 横截面上生成 `cfo_quality_percentile`，它作为
quality score 的一个组件，且 value-trap 条件要求该 percentile `>= 0.60`、
`revenue_growth_persistence >= 0`。quality score 是五个组件的横截面 percentile
平均值，至少需要两个非空组件。缺列或 PIT receipt 不安全时不会中性填充。

同时修正 full-candidate panel builder：它现在把 income、cashflow、balance
和 indicator 输入实际使用到的 disclosure dates 汇总为每个 symbol 的
`available_date`。这只是 provenance 修复，不会把旧的 formation date 伪装成
公告日期；历史 panel 需要重新构建后才会拥有该字段。

因此下一阶段应优先做“PIT feature materializer + freshness/coverage audit”，
而不是先配置正式群推送。

该 materializer 现已实现于
`strategy-research/src/style_factors/cashflow_pit_materializer.py`：它只读取
`available_date <= source_date` 的可见事件，并按 symbol/report period 去重，
同时返回 sealed manifest 输入哈希；它目前只负责 PIT 输入审计和 canonical
事件物化，不宣称已经完成策略 feature builder。对当前真实 vintage（截至 2026-09-06）
运行时，审计已证明 freshness、schema 和 immutable snapshot 有效，但仍阻塞于
`historical_revision_not_safe`，因此不会生成可供 strategy-app 使用的生产
feature frame。

## 准入顺序

```text
候选身份冻结
  -> PIT / OOS / 成本 / 容量门禁
  -> strategy-app runner
  -> immutable artifact + fail-closed receipt
  -> Feishu 测试群幂等推送
  -> 20–30 个交易日双跑
  -> 重新评估是否允许小范围正式推送
```

## 明确禁止

- 不把规则影子回溯称为官方指数历史。
- 不把研究脚本直接接入飞书 webhook。
- 不在数据缺失时用默认值或零值生成可推送目标。
- 不因为 DailyWatch20 或 D11-H5 已有发布合同，就继承它们的生产资格。
