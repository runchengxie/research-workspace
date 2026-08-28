# Contextual Alpha 研究平台设计

## 目标

在现有 A 股研究主线上增加一条可复现的宏观、产业、公司基本面与量价联合研究链路，使宏观和产业数据能够以严格的时间点语义进入横截面股票研究，并通过公司暴露映射形成条件化特征。

本设计不复刻某家私募的具体模型或固定因子权重。工作区采用可验证的实现：

- 数据层保存宏观、产业和能源数据的原始观测、发布时间、抓取时间与修订版本。
- 研究层把公共情境变量映射到行业和公司暴露，生成 `context × exposure` 条件化特征。
- 第一阶段继续使用现有横截面 ranker 和树模型学习交互关系，不创建逐股票独立模型。
- 研究评估继续使用 walk-forward、CPCV、PBO、样本外、成本、换手和 regime 证据。
- 缺少可靠发布时间、修订证据或公司暴露时允许 abstain，不通过填补叙事制造可用信号。

最终形成以下数据流：

```text
公开/低成本宏观与产业源
        ↓
market-data-platform
raw snapshot → normalized observations → PIT context panel
        ↓
alpha-research
context transforms + company exposures + context interactions
        ↓
现有 ranker / XGBoost
        ↓
signals
        ↓
portfolio-backtester
成本、换手、容量、暴露和 regime 评估
        ↓
strategy-research
shadow challenger、ablation、晋级证据
```

## 核心设计选择

### 1. 基本面与量价不固定 70/30 权重

基本面与量价的权重由研究证据决定。第一版通过特征集合 challenger 比较增量价值，不在代码中写死基本面 70%、量价 30%。

### 2. 不做逐股票独立模型

第一版用可审计的条件化输入表达千股千面：

```text
context_feature(symbol, t)
    = context_state(t) × company_exposure(symbol, t)
```

树模型可以进一步学习非线性交互。显式交互稳定产生样本外增量以后，才评估 gating network、mixture-of-experts 或分行业模型。

### 3. 宏观数据主要作为情境和调制变量

同一个月度宏观值对当日所有股票相同，直接用于横截面排序的信息有限。研究层优先构造：

- 利率变化 × 杠杆或久期敏感度
- 信贷变化 × 融资敏感度
- 工业用电变化 × 工业行业暴露
- 能源价格或产量变化 × 能源成本/产出暴露
- 出口变化 × 出口行业暴露
- 商品库存变化 × 商品生产或投入暴露

纯宏观状态特征可以作为 regime 输入，但必须与 interaction challenger 分开消融。

### 4. 第一轮先验证市场级横截面，再考虑接 DailyWatch20

月度和季度宏观数据的自然频率低于 DailyWatch20 当前短周期标签。第一轮 contextual alpha 以 A 股 PIT universe 的独立横截面实验作为主要验证对象，冻结 5、20、60 个交易日三个 horizon，其中 20 个交易日为主 horizon，5 和 60 个交易日用于期限敏感性诊断。

DailyWatch20 只在独立实验已经显示稳定增量后增加 contextual overlay，避免为了复用现有 runner 强行把慢变量塞进 5 日预测问题。

## 仓库边界

### market-data-platform

负责：

- 数据源适配器
- 原始不可变快照
- 标准化 context observation schema
- 发布时间、观测时间、抓取时间、修订和 lineage
- PIT/as-of 读取
- 数据质量、完整性、staleness 和 current contract

不负责：

- 股票预期收益预测
- 公司 exposure 研究规则
- 因子有效性判断

### alpha-research

负责：

- context series 的研究变换
- 公司和行业 exposure
- `context × exposure` 特征
- 单因子和特征组证据
- 模型训练、walk-forward、CPCV、PBO 和稳健性
- challenger 的预测信号

### portfolio-backtester

复用现有组合、换手、交易成本、容量和暴露能力。现有公开接口无法表达 regime 条件评估时，才增加通用 regime slice 汇总接口。该接口不得包含具体宏观系列或策略名称。

### strategy-research

维护：

- contextual alpha 投资假设
- 数据组和 challenger 定义
- ablation 研究记录
- 生命周期、失败条件和 evidence 导航

实验 runner 可以组合 owner 仓库公开 API，但不在本目录实现通用数据、特征、模型或组合内核。

### strategy-app / strategy-pipeline / execution

第一阶段不改变生产策略、不增加生产发布资格，也不修改执行行为。某个 contextual challenger 通过既有晋级门禁后，再单独设计策略应用和编排接线。

## 当前数据契约边界

现有 `a_share_current.json` 的 `market=a_share`、`provider=tushare` 语义保持不变。Contextual Alpha 会同时使用 TuShare、国家统计局和国家能源局等来源，因此不把这些资产塞进 A 股单 provider current contract。

`market-data-platform` 新增独立市场域：

```text
market = cn_context
provider = composite
current contract = metadata/current_assets/cn_context_current.json
```

`paths.py` 相应扩展：

```text
SUPPORTED_MARKETS += cn_context
SUPPORTED_PROVIDERS_BY_MARKET[cn_context] = {composite}
```

`cn_context_current.json` 只选择已经标准化和发布的组合资产，不直接枚举每个 provider 的 raw 快照。第一版稳定 asset key：

```text
context_catalog
context_observations
context_pit
context_release_calendar
```

`PublishedAssetRef.provider` 对这些组合资产为 `composite`。完整 manifest 的 `lineage` 记录每个源 provider、源快照、hash、抓取时间和 parser version。

研究层同时读取：

```text
PublishedAssetContract.load_current(..., market="a_share")
PublishedAssetContract.load_current(..., market="cn_context")
```

这样不会改变 A 股现有 provider 语义，也不要求 `PublishedAssetContract` 支持单个 current contract 内的多 provider asset identity。

## 数据资产设计

### context series catalog

新增机器可读的 series catalog。每个序列至少记录：

```text
series_id
source_id
provider
source_series_key
name
family
frequency
unit
seasonal_adjustment
value_semantics
revision_policy
availability_policy
expected_release_lag
max_staleness
status
```

`series_id` 是工作区稳定标识。供应商字段只描述 lineage，不进入下游特征名。

第一批稳定 series family：

```text
rates
credit
prices
activity
energy
trade
commodity_inventory
```

### normalized context observations

标准化长表至少包含：

```text
series_id
period_start
period_end
value
unit
published_at
observed_at
ingested_at
source_retrieved_at
available_at
vintage_id
revision_number
source_hash
```

约束：

- `available_at` 是研究是否可见的权威时间。
- `published_at` 有官方时间时使用官方时间。
- 只有发布日期而无精确时间时使用保守规则，在下一个 A 股可交易时点才可用。
- 无可靠发布日期且没有历史抓取证据的回填数据不得声称 revision-safe PIT。
- `source_retrieved_at` 晚于研究 as-of 的观测不得回填进历史。
- 每次重新发布或修订形成新的 vintage，不覆盖旧观测。

### raw snapshot

每次数据请求或官方页面抓取保存最小可重现证据：

```text
request metadata
retrieval timestamp
response bytes/hash
source locator
parser version
rows produced
```

建议路径：

```text
assets/context/cn/raw/<provider>/<dataset>/vintage=<YYYYMMDDTHHMMSS>/
```

完成快照不可修改。新的观测和修订写入新的 vintage 目录。

### normalized 和 PIT 路径

```text
assets/context/cn/normalized/cn_context_observations_<version>/
assets/context/cn/pit/cn_context_pit_<version>/
assets/context/cn/catalog/cn_context_catalog_<version>.parquet
assets/context/cn/release_calendar/cn_context_release_calendar_<version>.parquet
```

current alias 按现有平台模式指向已验证版本，manifest 和 dataset registry 记录覆盖范围与 lineage。

### PIT panel

公开读取接口按 `as_of` 选择：

```text
available_at <= as_of
```

同一 `series_id + period_end` 存在多个 revision 时，选择 as-of 当时最新可见 vintage。

PIT loader 返回数据和 audit：

```text
revision_covered
freshness_verified
series_missing
series_stale
selected_vintages
max_observation_age
reconstructed_series
```

正式 contextual research 要求相关 series `revision_covered=true` 且 `freshness_verified=true`。探索性研究可以显式允许 reconstructed 历史，但产物必须标记 `promotion_eligible=false`。

## 第一批真实数据源

### P0：TuShare macro pack

复用现有 TuShare client、凭证、重试和限流基础设施。第一批 endpoint 固定为：

```text
shibor
shibor_lpr
cn_m
sf_month
cn_pmi
cn_cpi
cn_ppi
cn_gdp
cn_schedule
```

系列至少覆盖：

- Shibor O/N、1W、1M、3M、6M、1Y
- LPR 1Y、5Y
- M1、M2 及其同比字段
- 社融增量及可稳定获取的主要分项
- 制造业 PMI 与生产、新订单等第一批核心分项
- CPI 全国同比和环比
- PPI 核心同比/环比字段
- GDP 总量、同比和第二/第三产业同比

`cn_schedule` 用于补充已公布的经济数据发布日期。某个历史 observation 无法通过 schedule、源字段或 observed vintage 证明实际可用日时，标记为 reconstructed。

TuShare 只作为 provider。平台保存自己的 raw snapshot 和 retrieval timestamp，不把供应商当前返回值当作历史真相。

### P1：国家统计局 activity/energy pack

从国家统计局公开数据入口接入适合产业景气研究的月度或季度序列，第一批固定范围：

- 规模以上工业增加值同比
- 发电量总量和同比
- 火电、水电、核电、风电、太阳能发电量或同比中能够稳定获得的字段
- 原煤产量和同比
- 原油产量和同比
- 天然气产量和同比

adapter 直接面向官方公开入口和响应，不把 AKShare 对象或 schema 引入跨仓契约。可以使用 fixture 固定官方响应结构做解析测试。

历史发布时间无法可靠恢复时，历史区间标记为 reconstructed。上线后的定期抓取形成 observed vintage ladder。

### P1：国家能源局 electricity pack

接入公开发布的全社会用电相关数据，第一批固定范围：

- 全社会用电量及同比
- 第一、第二、第三产业用电量及同比
- 城乡居民生活用电量及同比
- 官方发布中可以稳定解析且口径连续的制造业或高技术行业用电指标

页面解析器保存原始页面或响应 hash，并针对标题、发布日期、单位和表格变化失败关闭。新增细分指标必须先进入 catalog，不允许 parser 静默增加列。

### P2：trade / commodity pack

P0/P1 证据链稳定后扩展：

- 海关进出口总量和重点商品
- 港口吞吐和集装箱
- 交易所仓单、库存或公开商品库存
- TuShare `fina_mainbz` 或等价 PIT 合法业务构成，用于改善出口和商品 exposure

P2 不阻塞第一轮 contextual alpha 实验。

### P3：FRED/ALFRED 和 EIA

作为全球情境扩展。优先使用可提供 vintage 或明确发布时间的 API。第一轮国内 A 股 contextual alpha 不依赖该阶段。

## context transform 设计

`alpha-research` 提供通用、确定性的 context transform。输入是 PIT observation panel，不负责文件读取。

第一版变换：

```text
level
change_1p
change_np
yoy
rolling_zscore
acceleration
rolling_percentile
```

对每个变换记录：

```text
series_id
transform
window
minimum_history
staleness_limit
feature_name
```

规则：

- 缺少足够历史时输出缺失并记录 evidence，不静默填零。
- 不跨超过 `max_staleness` 的时间前向填充。
- 月度数据在后续交易日使用最近可见值时同时输出 `context_age_days`。
- `yoy` 的 lag 按原始 series frequency 计算，不按交易日硬移 252 天。
- `surprise` 只有存在独立、PIT 合法的市场预期数据时才启用，第一版不从最终值反推预期。

## 公司 exposure 设计

第一版 exposure 可解释、可回测、可消融。禁止维护数千只股票的人工权重表。

### 基础 exposure family

```text
rate_sensitivity
credit_sensitivity
industrial_activity_sensitivity
energy_input_sensitivity
energy_output_sensitivity
export_sensitivity
commodity_input_sensitivity
commodity_output_sensitivity
property_cycle_sensitivity
```

### ExposureSpec

`alpha-research` 增加框架中立的 `ExposureSpec`。每个 spec 固定：

```text
name
industry_prior_map
fundamental_modifiers
clip_min
clip_max
version
```

`industry_prior_map` 使用 PIT 行业标签给出基础 exposure。`fundamental_modifiers` 是可选的财务调制规则，每条包含输入字段、方向、标准化方式、权重和缺失行为。最终 exposure 在 spec 指定范围内 clip。

第一版 experiment 至少启用：

- `rate_sensitivity`：行业 prior + 杠杆/利息负担类 PIT 财务调制
- `credit_sensitivity`：行业 prior + 杠杆/现金类 PIT 财务调制
- `industrial_activity_sensitivity`：行业 prior
- `energy_input_sensitivity`：行业 prior
- `energy_output_sensitivity`：行业 prior

`export_sensitivity`、commodity 和 property exposure 可以进入 API 与 schema，但缺少可靠数据时保持未启用，不用人工逐股票猜测补齐。

### exposure 输出

```text
trade_date
symbol
exposure_name
exposure_value
source_components
exposure_version
```

第一版统一使用 `[-1, 1]`。正负方向由 exposure spec 定义。`source_components` 保存行业 prior、财务 modifier 及缺失状态的可序列化证据。

行业映射表是研究配置和版本化证据，不属于 market-data-platform 的原始事实。

## contextual interaction 特征

第一版公开 API 接受：

```text
stock_frame
context_frame
exposure_frame
interaction_specs
as_of_col
symbol_col
```

输出普通 DataFrame，不泄漏 TuShare、AKShare、Qlib 或供应商对象。

interaction 采用确定性命名，例如：

```text
ctx__shibor_3m_change20__x__rate_sensitivity
ctx__industrial_power_yoy__x__industrial_activity_sensitivity
ctx__coal_output_yoy__x__energy_output_sensitivity
```

每个 interaction 必须可追溯到：

- context series/version
- transform spec
- exposure spec/version
- as-of join policy

严格 join 检查同时验证 `available_at <= trade_date/session cutoff` 和 exposure 的 PIT 生效时间。

## 模型接入

第一版不新增独立模型框架。现有原生/XGBoost ranker 接收扩展后的 feature frame。

独立市场级实验冻结四组 challenger：

```text
C0 = price/volume + existing stock-level baseline
C1 = C0 + context state
C2 = C1 + context × exposure
C3 = C2 + PIT fundamental feature group
```

若现有 alpha API 已有可复用的 fundamental feature group，C3 直接复用。缺少统一 market-wide baseline 时，实验配置显式列出 C0/C3 的现有 feature names，不创建第二套特征实现。

研究报告必须同时给出：

- C1 - C0：纯 context state 增量
- C2 - C1：interaction 增量
- C3 - C2：PIT fundamental 联合增量
- C3 - C0：完整 contextual fundamental 增量

这样可以区分宏观 regime 信息和真正横截面的公司敏感度信息。

## 研究协议

### 数据频率和标签

主研究 universe 使用平台发布的 A 股 PIT by-date universe。

冻结 horizon：

```text
5 trading days
20 trading days  # primary
60 trading days
```

模型选择和 feature set 决策以 20 日 horizon 为主。5 日和 60 日只判断期限稳定性，不在同一 final OOS 上选择最优 horizon。

### 样本外与泄漏控制

必须：

- 使用 PIT universe
- 使用 revision-safe 或明确 reconstructed 状态的数据
- context as-of join 基于 `available_at`
- fundamental/exposure 使用 PIT 生效时间
- walk-forward
- CPCV/PBO
- feature ablation
- 多 regime 切片
- 独立 final OOS

最终 OOS 在冻结 feature set、ExposureSpec、TransformSpec 和 interaction set 后才运行。

### 成本、换手和容量

contextual alpha 若提高预测指标但显著提高换手，必须报告净收益效果。沿用现有 `portfolio-backtester` 的交易成本和容量框架，不创建策略专用会计。

至少比较：

```text
IC / RankIC
net return
Sharpe / risk-adjusted metrics
turnover
cost drag
capacity proxy
industry/style exposure drift
```

### regime stability

第一版固定诊断 regime：

```text
rates_up / rates_down
credit_expanding / credit_contracting
industrial_accelerating / industrial_decelerating
high_vol / low_vol
benchmark_uptrend / benchmark_downtrend
```

regime 划分阈值只由训练期或预先固定规则产生。final OOS 不重新调阈值。

## strategy-research 实验

新增：

```text
strategy-research/experiments/macro_context_shadow/
```

至少包含：

```text
README.md
experiment.yml
run_contextual_alpha_shadow.py
```

runner 只组合公开 owner API，不复制数据、特征或组合内核。

README 说明：

- 投资假设
- context family
- exposure family
- C0/C1/C2/C3 challenger
- 5/20/60 日 horizon 与 20 日主 horizon
- 时间点语义
- 样本外协议
- 成本假设
- 失败条件

第一轮失败条件：

- C2 相对 C1 无稳定样本外增量
- 完整增量只来自单一行业或单一短窗口
- 结果在 revision-safe 子样本消失
- 成本后增量不可见
- 特征重要性高度集中且跨 fold 不稳定
- 主要结论必须依赖 reconstructed 数据才能成立

满足失败条件允许记录 `no_view` 或 rejected，不通过继续加数据和参数强行挽救。

## 数据和研究质量门禁

### data gate

每个 context asset 至少检查：

- schema
- duplicate observation
- period ordering
- published/available/retrieved ordering
- unit consistency
- revision uniqueness
- missing periods
- staleness
- raw hash / lineage
- composite manifest 的 source coverage

### alpha gate

至少覆盖：

- as-of join 不读取未来 observation
- revision selection 正确
- staleness 拒绝
- transform 边界
- frequency-aware yoy
- exposure boundedness
- interaction 确定性
- 缺失输入行为
- feature set identity

### evidence gate

promotion 继续使用现有 evidence/lifecycle 规则。Contextual Alpha 第一阶段固定为 `exploration`，完成稳定 shadow 后最多升到 `research_shadow`，不会直接获得生产资格。

## PR 实施顺序

跨仓库按子模块先行、顶层最后更新 gitlink。

### PR 0：research-workspace 设计

本设计文档。只冻结边界、schema 语义和实施顺序。

### PR 1：market-data-platform context core + TuShare macro

内容：

- `cn_context` / `composite` contract domain
- context series catalog schema
- normalized observation schema
- raw/vintage/PIT 语义
- TuShare macro endpoint pack
- `cn_schedule` release calendar
- CLI 或发布入口
- `cn_context_current.json`
- manifest、validation、tests、docs

首批真实数据覆盖 rates、credit、prices、PMI/GDP activity。

### PR 2：market-data-platform official activity/energy

内容：

- 国家统计局 adapter
- 国家能源局 adapter
- raw snapshot sealing
- observed/reconstructed vintage 标识
- energy/activity series catalog
- parser fixture、结构漂移和失败关闭测试

### PR 3：alpha-research contextual factors

内容：

- `ContextTransformSpec`
- `ExposureSpec`
- PIT-safe context/exposure join
- interaction feature builder
- feature evidence
- 单元、revision、staleness 和泄漏测试
- 文档和公开导入 smoke test

### PR 4：research-workspace market-wide shadow experiment

PR 1 至 PR 3 合并后：

- 更新 `market-data-platform` 和 `alpha-research` gitlink
- 增加 `macro_context_shadow` 实验
- 冻结 C0/C1/C2/C3
- 冻结 5/20/60 日 horizon，20 日为主
- 接现有数据、alpha 和回测公开接口
- 保存实验配置和 evidence 路径

### PR 5：portfolio-backtester regime diagnostics，条件实施

只有 PR 4 证明现有接口无法复用时增加通用 regime slice 汇总。现有 API 足够则取消该 PR。

### PR 6：DailyWatch20 contextual overlay，条件实施

只有 market-wide shadow 的 C2/C3 通过稳定性标准后，在 DailyWatch20 的现有 fundamental shadow 上增加 opt-in contextual feature set，并保持其原有标签、候选池和成本协议不变。

### PR 7：后续低成本数据扩展

独立小 PR 接 trade、commodity、业务构成、FRED/ALFRED、EIA。每个数据源必须对应明确 hypothesis 或已观察到的数据缺口，避免无边界数据囤积。

## 兼容性

- 不修改现有 `a_share_current.json` provider 语义。
- 不修改现有 `signals.parquet` 基础语义。
- 不修改 `targets.json`。
- 不改变现有生产策略默认 feature set。
- 新 `cn_context` 资产为 opt-in。
- 新 contextual features 为 opt-in feature group。
- 不要求 Qlib。
- 数据供应商对象不进入跨仓契约。

## 明确不做的内容

第一轮不做：

- 固定 70/30 基本面与量价权重
- 每只股票一套独立训练模型
- 自动搜索数千种宏观变换
- 大规模参数网格搜索
- 卫星、信用卡、企业级电表等高工程成本另类数据
- 在无历史发布时间证据时伪造 revision-safe 历史
- 直接把 contextual challenger 接入实盘

## 验收标准

完整第一阶段以 PR 1 至 PR 4 为目标，满足以下条件才算落地：

1. `cn_context_current.json` 能独立发布并读取，不改变 `a_share_current.json`。
2. 至少四类真实 context family 可以从 TuShare 和官方公开源自动更新。
3. 数据资产有 raw hash、vintage、`available_at`、PIT as-of 读取和完整 audit。
4. observed 和 reconstructed 历史在 manifest、PIT audit 和研究 evidence 中明确区分。
5. `alpha-research` 可以从普通 DataFrame 生成 context transforms、company exposures 和 interactions。
6. 测试明确证明未来 publication 和未来 revision 无法进入历史 feature frame。
7. 至少一个真实 A 股 market-wide shadow 完成 C0/C1/C2/C3 与 5/20/60 日冻结对比。
8. 报告包含 IC/RankIC、final OOS、成本、换手、容量代理和 regime stability。
9. 无稳定增量时能够形成 rejected/no_view 结论，不影响现有生产链。
10. 所有跨仓改动遵循各 owner 仓库公开 API 和本地质量门禁。
