# Contextual Alpha 研究平台设计

## 目标

在现有 A 股研究主线上增加一条可复现的宏观、产业、公司基本面与量价联合研究链路，使宏观和产业数据能够以严格的时间点语义进入横截面股票研究，并通过公司暴露映射形成条件化特征。

目标不是复刻某家私募的具体模型或固定因子权重。工作区采用更可验证的实现：

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

### 1. 不固定 70/30 权重

基本面与量价的权重由研究证据决定。第一版通过特征集合 challenger 比较增量价值，不在代码中写死基本面 70%、量价 30%。

### 2. 不做逐股票独立模型

第一版用可审计的条件化输入表达千股千面：

```text
context_feature(symbol, t)
    = context_state(t) × company_exposure(symbol, t)
```

树模型可以进一步学习非线性交互。只有在显式交互已经稳定产生样本外增量后，才评估 gating network、mixture-of-experts 或分行业模型。

### 3. 宏观数据主要作为情境和调制变量

同一个月度宏观值对当日所有股票相同，直接用于横截面排序的信息有限。研究层必须优先构造：

- 利率变化 × 杠杆或久期敏感度
- 信贷变化 × 融资敏感度
- 工业用电变化 × 工业行业暴露
- 能源价格或产量变化 × 能源成本/产出暴露
- 出口变化 × 出口行业暴露
- 商品库存变化 × 商品生产或投入暴露

纯宏观状态特征仍可提供给树模型作为 regime 输入，但必须与 interaction challenger 分开做消融。

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

复用现有组合、换手、交易成本、容量和暴露能力。只有现有公开接口无法表达 regime 条件评估时，才增加通用 regime slice 汇总接口。该接口不得包含具体宏观系列或策略名称。

### strategy-research

维护：

- contextual alpha 投资假设
- 数据组和 challenger 定义
- ablation 研究记录
- 生命周期、失败条件和 evidence 导航

不承载通用特征计算。

### strategy-app / strategy-pipeline / execution

第一阶段不改变生产策略、不增加生产发布资格，也不修改执行行为。只有某个 contextual challenger 通过既有晋级门禁后，才设计策略应用和编排接线。

## 数据资产设计

### context series catalog

新增机器可读的 series catalog。每个序列至少记录：

```text
series_id
source_id
provider
source_series_key
name
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
- 只有发布日期而无精确时间时使用保守规则，默认在下一个可交易时点才可用。
- 无可靠发布日期且没有历史抓取证据的回填数据不得声称 revision-safe PIT。
- `source_retrieved_at` 不得晚于 as-of 读取时间后还被回填进历史。
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

完成快照不可修改。新的观测和修订写入新的 dated/vintage 目录。

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
```

正式 contextual research 要求 audit 通过。探索性研究可以显式允许 reconstructed 历史，但产物必须标记不可用于 promotion。

## 第一批真实数据源

### P0：TuShare macro pack

利用现有 TuShare 客户端、凭证和限流基础设施接入低维护成本的国内宏观数据。首批覆盖：

- Shibor
- LPR
- M2/货币供应
- 社融增量
- PMI
- CPI
- PPI
- GDP 或工业活动类可稳定获得的宏观系列

TuShare 只作为 provider。平台仍保存自己的 raw snapshot 和 retrieval timestamp，不把供应商当前返回值当作历史真相。

### P1：国家统计局 activity/energy pack

从国家统计局公开数据入口接入适合产业景气研究的月度或季度序列，优先：

- 工业增加值
- 发电量
- 火电、水电、风电、光伏等结构数据
- 原煤、原油、天然气等主要能源产量

若官方接口的历史发布时间无法可靠恢复，历史区间标记为 reconstructed，今后每日/每月抓取形成 observed vintage ladder。

### P1：国家能源局 electricity pack

接入公开发布的全社会用电相关数据，优先：

- 全社会用电量
- 第二产业或工业用电量
- 第三产业用电量
- 可稳定解析的制造业或高技术行业用电指标

页面解析器必须保存原始页面或响应 hash，并针对标题、发布日期、单位和表格变化做失败关闭。

### P2：trade / commodity pack

在前两批证据链稳定后扩展：

- 海关进出口总量和重点商品
- 港口吞吐和集装箱
- 交易所仓单、库存或公开商品库存

P2 不阻塞 P0/P1 contextual alpha 实验。

### P3：FRED/ALFRED 和 EIA

作为全球情境扩展。优先使用可提供 vintage 或明确发布时间的 API。第一轮 A 股国内 contextual alpha 不依赖该阶段。

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
- 月度数据可在后续交易日保持最近可见值，但必须带 `context_age_days` 或等价 age 特征。
- `surprise` 只有存在独立、PIT 合法的市场预期数据时才启用，第一版不从最终值反推预期。

## 公司 exposure 设计

第一版 exposure 要可解释、可回测和可消融。禁止维护数千只股票的人工权重表。

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

### 构造来源

按证据可靠性从高到低组合：

1. PIT 行业分类
2. PIT 财务比例，例如杠杆、利息负担、毛利率、现金、资本开支强度
3. 可获得且 PIT 合法的业务分部、地区或收入结构
4. 显式研究配置中的行业映射

第一版必须至少实现行业基础 exposure 和少量财务调制项，保证大部分 A 股可以获得 exposure，同时避免伪精确。

### exposure 输出

```text
trade_date
symbol
exposure_name
exposure_value
source_components
exposure_version
```

`exposure_value` 采用有界范围，例如 `[-1, 1]` 或 `[0, 1]`。具体方向由 exposure spec 定义。

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
ctx__rates_10y_change20__x__rate_sensitivity
ctx__industrial_power_yoy__x__industrial_activity_sensitivity
ctx__coal_output_yoy__x__energy_output_sensitivity
```

每个 interaction 必须可追溯到：

- context series/version
- transform spec
- exposure spec/version
- as-of join policy

## 模型接入

第一版不新增独立模型框架。现有 `DailyWatch20Ranker` 和研究后端接收扩展后的 feature frame。

冻结四组 challenger：

```text
C0 = incumbent / existing baseline
C1 = C0 + context state
C2 = C0 + context state + context × exposure
C3 = C2 + PIT fundamental feature group
```

如果某个现有 fundamental shadow 已经包含 C3 的部分内容，则以现有 feature set 为基线，保持相同 label、训练窗口、成本和候选池，只增加 context 维度。

研究报告必须同时给出：

- context state 单独增量
- interaction 相对于 context state 的增量
- fundamental 与 context 的联合增量

这样可以区分宏观 regime 信息和真正横截面的公司敏感度信息。

## 研究协议

### 时间尺度

月度和季度 context 数据不以预测未来 1 到 5 天为唯一验证目标。第一轮同时评估多个冻结 horizon，至少包括短周期和中周期，具体 horizon 使用现有研究标签系统表达。

若 DailyWatch20 的策略身份只允许固定短 horizon，则 contextual alpha 先作为独立 cross-sectional experiment 研究，再决定是否接入 DailyWatch20。

### 样本外与泄漏控制

必须：

- 使用 PIT universe
- 使用 revision-safe 或明确 reconstructed 状态的数据
- as-of join 基于 `available_at`
- walk-forward
- CPCV/PBO
- feature ablation
- 多 regime 切片
- 独立 final OOS

最终 OOS 在冻结 feature set 和 transform spec 后才运行。

### 成本、换手和容量

contextual alpha 若提高预测指标但显著提高换手，必须报告净收益效果。沿用现有 `portfolio-backtester` 的交易成本和容量框架，不创建一套策略专用会计。

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

对以下状态至少保留可重现切片：

```text
rates_up / rates_down
credit_expanding / credit_contracting
industrial_accelerating / industrial_decelerating
high_vol / low_vol
bull / bear or benchmark trend state
```

regime 只用于诊断和条件有效性判断，不允许在同一个 OOS 样本上反复调阈值直到显著。

## strategy-research 实验

新增：

```text
strategy-research/experiments/macro_context_shadow/
```

至少包含：

```text
README.md
experiment.yml
claims / evidence references
```

README 说明：

- 投资假设
- context family
- exposure family
- challenger 集合
- 时间点语义
- 样本外协议
- 成本假设
- 失败条件

第一轮失败条件包括：

- interaction 相对 context-only 无稳定样本外增量
- 增量只来自单一行业或单一短窗口
- 结果对 revision-safe 数据消失
- 成本后增量不可见
- 特征重要性高度集中且跨 fold 不稳定
- 必须依赖 reconstructed 数据才能成立

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

### alpha gate

至少覆盖：

- as-of join 不读取未来 observation
- revision selection 正确
- staleness 拒绝
- transform 边界
- exposure boundedness
- interaction 确定性
- 缺失输入行为
- feature set identity

### evidence gate

promotion 仍使用现有 evidence/lifecycle 规则。Contextual Alpha 第一阶段固定为 exploration 或 research_shadow，不获得生产资格。

## PR 实施顺序

跨仓库按子模块先行、顶层最后更新 gitlink。

### PR 0：research-workspace 设计

本设计文档。只冻结边界、schema 语义和实施顺序。

### PR 1：market-data-platform context core + TuShare macro

内容：

- context series catalog schema
- normalized observation schema
- raw/vintage/PIT 语义
- TuShare macro provider pack
- CLI 或发布入口
- current contract asset keys
- manifest、validation、tests、docs

首批真实数据至少覆盖 rates、credit、prices、PMI。

### PR 2：market-data-platform official activity/energy

内容：

- 国家统计局 adapter
- 国家能源局 adapter
- raw snapshot sealing
- observed/reconstructed vintage 标识
- energy/activity series catalog
- parser fixture 和失败关闭测试

### PR 3：alpha-research contextual factors

内容：

- context transform specs
- company exposure specs
- PIT-safe join
- interaction feature builder
- feature evidence
- 单元和泄漏测试
- 文档和公开导入 smoke test

### PR 4：research-workspace shadow experiment

在 PR 1 至 PR 3 合并后：

- 更新子模块 gitlink
- 增加 `macro_context_shadow` 实验
- 冻结 C0/C1/C2/C3 challenger
- 接现有数据、alpha 和回测公开接口
- 保存实验配置和 evidence 路径

### PR 5：portfolio-backtester regime diagnostics，条件实施

仅当 PR 4 发现现有接口无法复用时增加通用 regime slice 汇总。若现有 API 足够，本 PR 取消。

### PR 6：后续低成本数据扩展

独立小 PR 接 trade、commodity、FRED/ALFRED、EIA。每个数据源必须证明增量研究价值或明确服务的 hypothesis，避免无边界数据囤积。

## 兼容性

- 不修改现有 `signals.parquet` 基础语义。
- 不修改 `targets.json`。
- 不改变现有生产策略默认 feature set。
- 新 context 资产为 opt-in。
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

1. 至少四类真实 context family 可以从公开或现有低成本 provider 自动更新。
2. 数据资产有 raw hash、vintage、`available_at`、PIT as-of 读取和完整 audit。
3. `alpha-research` 可以从普通 DataFrame 生成 context transforms、company exposures 和 interactions。
4. 测试明确证明未来 publication 和未来 revision 无法进入历史 feature frame。
5. 至少一个真实 A 股 shadow experiment 完成 C0/C1/C2/C3 冻结对比。
6. 报告包含 IC/RankIC、OOS、成本、换手、容量代理和 regime stability。
7. 无稳定增量时能够形成 rejected/no_view 结论，不影响现有生产链。
8. 所有跨仓改动遵循各 owner 仓库公开 API 和本地质量门禁。
