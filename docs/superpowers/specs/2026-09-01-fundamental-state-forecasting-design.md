# Fundamental State Forecasting 设计

## 目标

新增一条独立的基本面状态预测研究线，检验以下问题：先预测未来企业经营状态，再结合当前估值形成横截面选股分数，是否比直接把当前基本面作为短中期股票收益特征更稳定。

研究链路为：

```text
PIT annual fundamentals
        ↓
future fundamental targets
        ↓
persistence / linear / ML forecasts
        ↓
OOS fundamental forecast evaluation
        ↓
forecast + current valuation score
        ↓
portfolio-backtester research backtest
```

第一版停留在 `exploration`，不接 `strategy-app`、`strategy-pipeline`、`targets.json` 或实盘执行。

## 研究假设

核心假设是企业经营状态的短中期变化具有可预测成分，而且这种预测在加入当前估值后可能形成稳定的横截面股票信息。

第一阶段优先研究一年期基本面状态，不直接预测五年或十年股票收益。初始目标包括：

- `delta_roa_1y`
- `revenue_growth_1y`
- `future_gross_margin_1y` 或对应变化量
- 后续数据口径稳定后再加入净利润增长、现金流质量和 ROIC

## 文献依据

本研究借鉴以下文献的研究结构，不照搬其具体模型或数据口径：

- Ou and Penman (1989), Journal of Accounting and Economics。先由财务报表信息预测一年期盈利变化，再研究组合收益。
- Abarbanell and Bushee (1997), Journal of Accounting Research。研究基本面信号、未来盈利与股价之间的联系。
- Chen, Cho, Dou and Lev (2022), Journal of Accounting Research。使用高维财务数据和机器学习预测一年期盈利变化，并检验样本外预测与股票收益。
- Fama and French (2006), Journal of Financial Economics。用估值理论连接预期盈利能力、投资和预期收益。
- Novy-Marx (2013), Journal of Financial Economics。展示盈利能力在横截面收益中的信息价值。
- Richardson and Stock (1989), Journal of Financial Economics。说明多年收益统计推断受到重叠区间和有限样本问题影响。

## 数据与 PIT 约束

`market-data-platform` 继续负责原始财务数据、revision lineage、披露日期和 PIT 可用性。`alpha-research` 不自行选择修订版本。

第一版标签构造函数要求输入满足：每个 `(symbol, report_period)` 只有一条已经通过 PIT 审计的 canonical annual observation。输入必须显式提供 `available_date`。

每个训练标签携带：

- `feature_as_of_date`
- `target_report_period`
- `target_available_date`
- `fundamental_label_end_date`

`fundamental_label_end_date` 等于目标财务状态第一次合法可见的日期，用于 purge 和 embargo。训练集不能因为报表期已经结束就提前看到尚未披露的目标值。

## Alpha 研究接口

`alpha-research` 新增 `alpha_research.fundamental_state`，保持纯 pandas/numpy、框架中立和可独立测试。

公开研究构件包括：

- `FundamentalTargetSpec`
- `build_annual_fundamental_target_panel`
- `build_persistence_baseline`
- `evaluate_fundamental_forecast`
- `FundamentalScoreSpec`
- `build_fundamental_forecast_score`
- `purge_and_embargo_fundamental_rows`

现有 `ResearchModel` 继续承担单目标模型训练。第一版一个 target 一个模型，不新增 multi-task 训练框架。

## Baseline 与评价

任何 ML 模型都必须至少比较 persistence baseline。对于 level target，persistence 等于当前值；对于 delta 或百分比变化 target，persistence 等于零变化。

基本面预测第一层评价至少包括：

- MAE
- RMSE
- cross-sectional rank IC
- 对变化类 target 的 direction accuracy

只有基本面预测在 OOS 上有稳定增量后，才进入股票收益评价。

## 估值桥接

第一版不实现完整 DCF。使用透明的同日横截面百分位加权分数，将预测质量、预测成长和当前估值组合成 `fundamental_score`。

该桥接必须支持消融比较：

```text
current fundamentals only
forecast fundamentals only
current fundamentals + valuation
forecast fundamentals + valuation
```

## 组合层

`portfolio-backtester` 第一版保持零修改。研究信号以普通外部 score 进入现有组合和回测接口。

优先测试低换手持有规则，例如新仓采用较严格排名阈值、旧仓使用更宽退出阈值。现有 incumbent requalification 能力优先复用。

## 仓库边界

- `strategy-research`：thesis、生命周期、文献、实验规格和失败条件
- `market-data-platform`：PIT 财务数据和 revision provenance
- `alpha-research`：标签、baseline、模型评价、预测分数
- `portfolio-backtester`：组合、成本、容量、暴露和回测
- `strategy-app`、`strategy-pipeline`、`quant-execution-engine`：第一版不修改

## 第一版成功条件

第一版不以 Sharpe 为唯一成功条件。研究至少需要回答：

1. ML 是否稳定优于 persistence baseline 预测未来基本面？
2. 预测基本面是否比当前基本面提供额外横截面信息？
3. 加入当前估值后，预测基本面形成的分数是否在 OOS 上具有可重复的股票收益排序能力？
4. 结果是否在年份、行业和市场环境切片下保持合理稳定？

如果第一问失败，研究应记录负结果并停止向更复杂模型升级。
