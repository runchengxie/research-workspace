# A 股基本面特征族与长周期 Shadow 设计

- Date: 2026-08-30
- Status: proposed
- Scope: `research-workspace` 及 `market-data-platform`、`alpha-research`、`strategy-research`，必要时复用 `portfolio-backtester` 公共 API
- Production impact: none; 本设计不修改任何生产默认、不自动晋级策略
- Motivation: 把现有零散的 Value / Quality / Growth 基本面研究整理成可解释、严格 PIT、可做族级 ablation 的研究协议，并将公募基金持仓降级为辅助上下文特征

## 1. 背景与问题

工作区已经存在三类容易混淆的“基本面相关”能力：

1. 当前 A 股/ DailyWatch20 生产特征中已有估值与风格变量，例如 `pb`、`pe_ttm` 派生的 `value_yield`、`earnings_yield`，以及 size/liquidity 等控制特征；
2. `alpha-research.daily_watch20_pit_features` 已有严格 PIT 的 Quality / Growth 研究特征，包括 ROA、毛利率、CFO/assets、负应计、营收同比和净利润同比；
3. 已关闭的 `feat/fund-crowding-context-shadow` 曾把公募基金持仓变化作为 standalone ranking hypothesis，最终样本外和成本后结果不足以支持该方向。

当前缺口不是“没有基本面因子”，而是：

- Value / Quality / Growth 没有统一、机器可读的 family contract；
- 现有 DailyWatch20 fundamental shadow 只有 `Q0 -> Q1 quality -> Q2 quality+growth`，无法区分 Value、Quality、Growth 各自增量；
- 当前生产基线本身已经包含 `1/PB` 与 `1/PE`，因此直接做“baseline + Value”会重复使用同一特征，实验解释错误；
- 慢基本面仍主要在短期标签体系附近研究，缺少预注册的 20/60 日长周期对照；
- fund ownership / crowding 的合理用途应是 VQG 模型上的辅助上下文，而不是重新成为主排名信号；
- 2026-08-30 之前的历史已经被反复查看，新实验不能把这些数据重新包装为“新的 OOS”。

## 2. 目标

本改动系列将完成以下目标：

1. 在 `alpha-research` 建立稳定的基本面特征族契约：`value`、`quality`、`growth`，并单独标识 `style_controls` 与 `fund_context`；
2. 保留现有 PIT Quality/Growth 逻辑为 canonical implementation，不复制第二份实现；
3. 增加 Value family，覆盖 earnings yield、book yield、sales yield，并确保数据在评分日可见；
4. 在 `strategy-research` 新建 `fundamental_family_shadow`，以族级 ablation 回答哪类基本面真正带来增量；
5. 预注册 20 日主周期与 60 日慢基本面 challenger；5 日只作为诊断；
6. 将 fund context 只作为 `VQG + fund_context` 的最后辅助 arm；
7. 所有历史重跑明确标记为 retrospective / diagnostic，新 OOS 从 2026-08-31 起冻结累积；
8. 输出可审计 receipt，记录特征集合、标签周期、PIT lineage、成本、换手、容量、统计检验与 evidence class。

## 3. 非目标

本系列不会：

- 直接把 `fundamentals.enabled` 切到生产开启；
- 修改 `configs/presets/a_share.yml` 的生产默认特征或模型参数；
- 修改 `DAILY_WATCH20_FEATURES` 以直接加入新的 Quality/Growth production feature；
- reopen 或 merge 已关闭的 `feat/fund-crowding-context-shadow`；
- 把 fund-holder-count / crowding 重新作为 standalone production ranking signal；
- 引入 Qlib 作为新的强制训练依赖；
- 因为历史结果好看而事后改变 primary horizon、成本、样本区间或晋级门槛；
- 把 2026-08-30 以前的新一轮回放称为新的 final OOS。

## 4. Owner 边界

### `market-data-platform`

负责数据可见性与稳定读取接口：

- DailyWatch20 / A-share research loader 暴露评分日已可见的 `pb`、`pe_ttm`、`ps_ttm`；
- 不在 alpha 或 research 层自行读取 provider 私有文件；
- 保持 published/current contract 和 lineage 语义；
- 如 `ps_ttm` 在 daily-clean 已存在，仅做向后兼容的列暴露，不改变生产资产 schema。

### `alpha-research`

负责因子语义与变换：

- canonical Value / Quality / Growth family constants；
- Value yield 构造与同日横截面处理；
- 复用现有 PIT Quality/Growth builder；
- horizon profile / label configuration 的纯 alpha 侧公共 helper；
- 不决定策略是否晋级，不写生产 preset。

### `strategy-research`

负责研究问题、arm matrix、冻结协议与 evidence：

- `fundamental_family_shadow` 实验配置；
- 族级 ablation；
- 20/60 日研究 runner；
- retrospective 与 future-OOS evidence class；
- fund context auxiliary arm；
- 研究报告与机器 receipt。

### `portfolio-backtester`

只在现有公共 API 不足时补通用能力：

- 固定频率 rebalance / equal-weight 或 Top-K portfolio replay；
- turnover、成本、drawdown、capacity 与 benchmark attribution；
- 不承载 Value/Quality/Growth 因子定义。

### `strategy-pipeline` / `strategy-app`

本系列默认不要求生产变更。

如果实现过程中需要复用 DailyWatch20 已有公共 scoring/evaluation API，只允许通过公开 owner API 调用；不得把新研究逻辑重新搬回 pipeline。任何 production candidate 都必须在本研究系列完成后另开独立设计与 PR。

## 5. 基本面特征族契约

建议在 `alpha-research` 增加一个公开模块，例如：

```text
alpha_research.daily_watch20_fundamental_families
```

具体文件名可在实现计划中按现有模块命名规则调整，但公共语义固定。

### 5.1 Value

Value 表达市场价格相对基本面尺度的便宜程度：

```text
value_book_yield      = 1 / PB
value_earnings_yield  = 1 / PE_TTM
value_sales_yield     = 1 / PS_TTM
```

规则：

- 分母必须为有限正值，否则为 null；
- 不对 null 做跨日期 forward-fill；
- 数据来自评分日可见的 daily-basic / daily-clean 状态；
- `sales_yield` 是本轮新增研究项；
- `value_yield` / `earnings_yield` 的现有生产语义保持不变；
- 新 family contract 可以把现有列映射为 Value 成员，但不得偷偷复制计算公式形成两套实现。

是否使用 raw yield 或同日 percentile rank 必须在 family metadata 中显式记录。对于 family ablation，默认使用 owner-native 语义并在所有 arm 中保持一致。

### 5.2 Quality

继续使用现有 strict PIT 实现：

```text
pit_quality_roa_pct
pit_quality_gross_margin_pct
pit_quality_cfo_to_assets_pct
pit_quality_negative_accrual_pct
```

不重写计算逻辑；继续要求 exact-date PIT、revision-safe provenance、freshness 与 report-age contract。

### 5.3 Growth

继续使用：

```text
pit_growth_revenue_yoy_pct
pit_growth_netprofit_yoy_pct
```

同样复用现有 strict PIT implementation。

### 5.4 Style controls

下列变量不宣传为基本面 Alpha family，默认作为控制/已有模型结构保留：

```text
size_pct
liquidity_pct
low_volatility_pct
beta / volatility regime 等已注册 style exposure
```

`turnover_rate` / `turnover_20` 也不归入 Quality 或 Growth。

### 5.5 Fund context

fund context 是辅助上下文族，不属于基本面主族，不允许作为本系列的 standalone primary arm。

候选可包括：

```text
fund_crowding_level
fund_ownership_change
fund_holder_count_change
fund_low_crowding_accumulation
fund_top10_concentration
fund_accumulation_without_crowding
```

只使用当前 `main` 上已经合并的数据读取/审计能力；不得依赖已关闭 PR #251 的 branch head。

## 6. 为什么需要两个 baseline

当前 `production_model_features()` 已包含：

```text
value_yield      # 1/PB
earnings_yield   # 1/PE_TTM
```

所以新实验必须同时保留两个不同角色的 baseline。

### P0: current-production-feature anchor

```text
P0 = production_model_features()
```

P0 用于回答：在相同新研究标签协议下，当前 production feature set 表现怎样。

P0 不是“纯技术面”。

### T0: technical/control core

```text
T0 = P0 - {value_yield, earnings_yield}
```

T0 是 Value/Quality/Growth family ablation 的共同基线。

所有 style controls、market features 和当前非估值 production feature 保持不变，避免一次实验同时改变太多结构。

因此：

- `T0 -> V` 测完整 Value family 增量；
- `P0 -> V` 主要测新增 sales-yield 及 family 规范化后的差异；
- `T0 -> Q/G/VQ/VG/QG/VQG` 测各基本面 family 的独立与组合贡献。

## 7. 冻结 arm matrix

主实验固定为：

| Arm | 特征集合 | 目的 |
| --- | --- | --- |
| P0 | 当前 production feature set | 当前特征锚点 |
| T0 | P0 去掉现有 PE/PB value features | 族级共同基线 |
| V | T0 + Value | 测估值族 |
| Q | T0 + Quality | 测质量族 |
| G | T0 + Growth | 测成长族 |
| VQ | T0 + Value + Quality | 测估值+质量 |
| VG | T0 + Value + Growth | 测估值+成长 |
| QG | T0 + Quality + Growth | 测质量+成长 |
| VQG | T0 + Value + Quality + Growth | 主基本面 challenger |
| VQG_F | VQG + fund_context | 仅辅助诊断 |

`VQG_F` 不进入基本面主 family 的 promotion decision family；fund 数据不是 revision-safe 时，其 evidence class 必须为 `exploratory_only`。

不得在看到结果后删除表现差的 arm 或增加特定组合来优化结果。新组合需要新 experiment version。

## 8. Horizon 设计

### 8.1 20 日：primary

- 单一未来 20 个交易日标签；
- 作为基本面 family selection 的唯一 primary horizon；
- rebalance / evaluation sampling 以 20 交易日节奏为主，避免把慢变量强迫成每日高换手信号；
- 训练/验证 purge 与 embargo 必须覆盖完整 20 日标签成熟期。

### 8.2 60 日：preregistered slow-fundamental challenger

- 单一未来 60 个交易日标签；
- 在任何 60 日结果被读取前固定配置；
- 使用 60 日级别 purge/embargo；
- 目的只回答“慢基本面在更长周期是否更稳定”，不会因为表现更好自动取代 20 日 primary。

### 8.3 5 日：diagnostic only

- 用于复核已有“短周期基本面较弱”的历史观察；
- 不参与主晋级判断；
- 不允许因为 5 日表现更好而改变 primary horizon。

### 8.4 标签实现

优先复用 `alpha-research` 已支持任意正整数 horizon 的 next-open label helper，而不是新写第二套 forward-return 逻辑。

每个 horizon 使用独立配置和独立 receipt，禁止在一个模型中事后挑选最优 horizon。

## 9. PIT 与数据质量门禁

### Value

Value 来自日频 daily-basic 状态，也必须满足：

- stock/date 唯一；
- 当日字段不可来自未来日期；
- 无非法正负无穷；
- 不用未来修订后的 provider state 回填过去日期；
- `ps_ttm` 缺失时 V/VQ/VG/VQG 当日 coverage 显式下降，不用 PE/PB 代填。

### Quality / Growth

沿用现有 hard gates：

- `provenance_policy=require_observed`；
- `revision_safe=true`；
- `freshness_verified=true`；
- observation age <= 3 天；
- report age <= 250 天；
- exact-date as-of state；
- 每个源字段完整 lineage；
- derived ratio 使用同一 report period。

### Fund context

- `available_date <= trade_date`；
- duplicate conflict fail-closed；
- 没有完整 vintage ladder 时必须记录 `revision_safe=false`；
- 不得产生 production-eligible receipt。

## 10. 训练与评估协议

### 10.1 模型

优先复用现有 alpha ranker / trainer 公共 API，不引入新的训练框架。

所有 arm 在同一 horizon 下必须共享：

- 相同训练日期；
- 相同 validation / test 日期；
- 相同 universe；
- 相同模型超参数；
- 相同 sample-weight policy；
- 相同缺失值策略；
- 相同成本与 portfolio construction。

唯一允许变化的是 family feature set。

### 10.2 Universe

主 family evidence 使用完整 `hard_eligible` A-share cross-section 或其现有 owner-defined PIT universe；不得让不同 arm 因特征 coverage 使用不同日期/股票集合后直接比较。

主配对统计使用 common finite intersection。

如果复用 DailyWatch20 strict-v2 hot pool，只作为附加 execution/selection diagnostic，不把热点池结果冒充全市场基本面有效性。

### 10.3 Portfolio

至少输出：

- cross-sectional Rank IC；
- Top-K / top-quantile return；
- matched equal-weight benchmark active return；
- one-way turnover；
- 10 / 20 / 30 / 50 bps 成本压力；
- max drawdown / downside deviation；
- size、liquidity、value、momentum 等 exposure drift；
- capacity diagnostics（在 owner API 能提供时）。

20 日和 60 日主组合默认使用与 horizon 对齐的低频 rebalance，不以每日完整换仓人为制造高 turnover。

### 10.4 统计

由于 forward-return 窗口可能重叠，推断不能使用朴素 IID t-test。

至少要求：

- paired comparison；
- HAC / Newey-West 或 block bootstrap；
- 多 arm 主指标使用 Holm family correction；
- 时间窗口稳定性；
- 不同市场 regime 的非负稳定性诊断。

正式阈值在 implementation plan 中从现有 fundamental-shadow policy 继承可复用部分，并为 20/60 日 horizon 创建新 policy version；不得复用 5 日 policy 的 embargo 数字冒充长周期适用。

## 11. Evidence class 与新 OOS 边界

这是本设计最重要的治理约束之一。

### 历史回放

任何使用 `trade_date <= 2026-08-30` 的新 family experiment 输出都必须：

```text
eligible_as_new_oos_evidence = false
evidence_class = retrospective_diagnostic
```

原因是这些历史已经被多次观察，不能再次称为未见样本。

### Future OOS

冻结起点：

```text
new_oos_start = 2026-08-31
```

代码和 family/horizon policy 在该日期前固定后，后续新日期可以累积为真正 prospective evidence。

如果实现 PR 在 2026-08-31 之后才合并，receipt 必须同时记录 `policy_frozen_at`，并把 `new_oos_start` 自动推迟到“不早于 policy freeze 后第一个未观察交易日”，禁止倒填 OOS 身份。

## 12. Fund context 的降级规则

已关闭的 fund-crowding 研究结论保持历史事实，不因本设计被重写。

本系列只保留三类价值：

1. PIT / disclosure-date audit；
2. duplicate conflict fail-closed 与 provenance；
3. 作为强 VQG 模型的 auxiliary context。

`VQG_F` 只有在以下条件下才值得解释：

- VQG 本身在同窗有有效基础证据；
- fund feature coverage 足够；
- VQG_F 与 VQG 使用完全相同的股票/日期 common intersection；
- 成本后有增量；
- 增量不只来自 size/industry/crowding exposure；
- fund history 的 evidence class 被正确标记。

即使 `VQG_F` 历史结果优秀，也不能凭当前缺少完整 vintage 的 fund 数据成为 production candidate。

## 13. 失败关闭与错误处理

Runner 遇到以下情况必须 fail closed：

- family contract 中请求的列缺失；
- PIT lineage 不完整；
- arm 之间 evaluation keys 不一致；
- horizon 对应 purge/embargo 未满足；
- common intersection 低于预注册 coverage 门槛；
- 成本、benchmark 或 portfolio receipt 缺失；
- historical output 被误标为 new OOS；
- fund context 被误标为 revision-safe；
- production config 被研究 runner 修改。

失败时仍应写 blocked receipt，记录原因和已解析 lineage，而不是静默跳过日期。

## 14. 产物

每次不可覆盖的 run 至少保存：

```text
experiment.yml / frozen_config.json
family_registry.json
feature_coverage.parquet
scores.parquet
portfolio_daily.parquet
paired_metrics.parquet
window_metrics.parquet
regime_metrics.parquet
lineage.json
receipt.json
```

receipt 至少包含：

- git SHAs / package versions；
- input asset hashes / current-contract hashes；
- exact family feature names；
- horizon / label policy；
- purge / embargo；
- train/validation/evaluation date ranges；
- evidence class；
- new-OOS eligibility；
- cost assumptions；
- benchmark semantics；
- family coverage；
- primary paired metrics；
- limitations；
- `production_default_changed=false`；
- `automatic_promotion_allowed=false`。

## 15. PR 规划

### PR 0 — research-workspace design

本设计文档，仅固定范围与依赖，不包含运行逻辑。

### PR A1 — market-data-platform: valuation research input

目标：

- 在 DailyWatch20 / A-share owner loader 中稳定暴露 `ps_ttm`；
- 保持现有 `pb`、`pe_ttm` 行为；
- 增加列存在、日期范围、stock/date 唯一和向后兼容测试；
- 不修改 published asset 的经济语义。

如果实现时确认已有公开 loader 已提供等价 `ps_ttm`，则 A1 缩减为测试/契约确认，不新造 API。

### PR A2 — alpha-research: fundamental family contract

目标：

- Value / Quality / Growth / style-control family registry；
- canonical sales-yield transform；
- 复用现有 `QUALITY_FEATURES` / `GROWTH_FEATURES`；
- T0/P0 feature-set helper；
- 5/20/60 horizon profile helper；
- 单测覆盖 invalid valuation、missing columns、family overlap、production feature immutability 与 label policy。

### PR B — strategy-research: V/Q/G ablation

新增：

```text
experiments/fundamental_family_shadow/
```

包含：

- frozen `experiment.yml`；
- P0/T0/V/Q/G/VQ/VG/QG/VQG matrix；
- 20 日 primary runner；
- 5 日 diagnostic；
- common-intersection coverage；
- paired metrics / cost / turnover / exposure diagnostics；
- retrospective receipt；
- tests 和 README。

PR B 不包含 fund-context arm，保证主基本面实验可以独立 review。

### PR C — strategy-research: 60d + fund auxiliary

目标：

- 增加 preregistered 60d slow-fundamental run；
- horizon-aware purge/embargo；
- 增加 `VQG_F` auxiliary arm；
- 使用 main 上的 fund PIT/data-quality owner API；
- 明确 `VQG_F` 不进入 production eligibility；
- 增加 fund revision-safety evidence classification 测试。

如果通用 portfolio/horizon replay 能力缺失，先在 `portfolio-backtester` 补 provider PR，再让 PR B/C 消费；不在 `strategy-research` 复制通用实现。

### PR D — research-workspace integration

在 owner PR 均合并后：

- 更新 submodule gitlinks；
- 更新 research catalog / roadmap / docs navigation；
- 运行 workspace governance、boundary、docs、catalog tests；
- 记录历史 diagnostic 的 evidence identity；
- 不改 production preset。

### 后续独立 production-candidate PR

只有 VQG 在预注册协议下取得足够证据后，才允许另起设计讨论：

- 是否让 statement fundamentals 进入生产；
- 哪个 family 进入；
- feature schema migration；
- model retrain / rollout / rollback；
- live shadow 与 production gate。

该步骤明确不属于当前实现系列。

## 16. 测试策略

### market-data-platform

- `ps_ttm` owner loader contract；
- existing columns parity；
- stock/date uniqueness；
- date filtering；
- missing asset / missing column fail closed。

### alpha-research

- family constants frozen；
- family membership 无重复；
- T0 确实移除 current value features；
- P0 与 production model feature order 一致；
- positive finite denominator rules；
- no forward fill；
- existing PIT Q/G behavior parity；
- 20/60 label column and maturity semantics；
- production feature constant 未被修改。

### strategy-research

- exact frozen arm set；
- same dates/universe/model params across arms；
- common finite intersection；
- 20 primary / 60 secondary / 5 diagnostic semantics；
- horizon-aware embargo；
- retrospective outputs cannot claim new OOS；
- receipt content-address / no overwrite；
- fund auxiliary cannot become production eligible；
- closed branch #251 is not a runtime dependency。

### workspace integration

- submodule refs resolve to merged commits；
- docs links；
- research catalog/schema checks；
- cross-repo private import boundary；
- governance / maintainability gates relevant to touched files。

## 17. Rollback

该系列必须 provider-first、consumer-second：

- A1/A2 merge 后即使 B/C 回滚，也只增加研究 API，不改变 production；
- B/C 可独立回滚，不影响现有 DailyWatch20 fundamental shadow；
- D 只同步已合并 owner commits；
- 任何 production change 均不在本系列，因此不存在生产回滚耦合。

如果 family parity 或 PIT 语义发现问题，保留 owner API 的测试和 blocked receipt，停止 consumer rollout，先在 owner 仓修正，不通过改变研究结果解释来绕过问题。

## 18. 完成标准

本系列完成时应满足：

1. workspace 有唯一、清晰的 Value / Quality / Growth family contract；
2. Value 包含 PE/PB/PS 三个估值尺度，Q/G 继续严格 PIT；
3. 当前 production feature anchor 与真正 T0 baseline 被明确区分；
4. 9 个主 family arms 在完全一致的 evaluation keys 上可复跑比较；
5. 20 日 primary 和 60 日 preregistered challenger 都有 horizon-aware leakage protection；
6. 5 日只作为 diagnostic；
7. 历史结果全部标记 retrospective，不冒充新的 OOS；
8. future OOS freeze 规则机器可检查；
9. fund context 只能作为 VQG auxiliary，且 provenance 限制被 receipt 固化；
10. 所有新增能力通过 owner API 提供，没有把通用实现复制到 research/pipeline；
11. 没有修改生产 preset、生产 feature schema 或自动晋级状态；
12. 最终 integration PR 的 workspace governance / docs / boundary tests 通过。
