结论：**5000 分账户已经能拿到一大部分相关数据；10000 分账户覆盖更稳，但不是所有常规接口都会因为 10000 分而变快。** 这些数据**可以作为特征**，但现在这个项目里还没有现成接入。要做得像样，需要先把它们做成 PIT/as-of 特征资产，否则就是把未来信息塞进模型里，然后假装发现了阿尔法，量化圈传统艺能之一。

## 1. Tushare 5000 / 10000 分能拿到哪些相关数据？

Tushare 的权限大体分两类：积分接口和单独开权限接口。官方权限表写得很清楚：5000 分以上常规数据每分钟 500 次、常规数据无总量上限；10000 分以上常规数据频次仍是 500 次/分钟，但多了“特色数据”权限，特色数据 300 次/分钟。分钟数据、新闻、公告、港美股等很多东西是单独权限，跟积分不是一回事。人类终于把一个账号体系做成了迷宫，令人欣慰。([Tushare][1])

### 相关接口大致如下

| 数据类型            |                                Tushare 接口 |             5000 分是否够 | 说明                                                         |
| --------------- | ----------------------------------------: | --------------------: | ---------------------------------------------------------- |
| 个股资金流向，普通版      |                               `moneyflow` |                 **够** | 2000 分起，A 股个股资金流向，按大中小单拆分，数据从 2010 年开始。([Tushare][2])      |
| 个股资金流向，东方财富     |                            `moneyflow_dc` |                 **够** | 5000 分起，数据从 2023-09-11 开始，字段包括主力净流入、超大单/大单等。([Tushare][3]) |
| 个股资金流向，同花顺      |                           `moneyflow_ths` | **5000 可能不够，10000 够** | 最近文档片段显示 6000 分可调取；如果只有 5000 分，保守看可能会被拒。([Tushare][4])     |
| 行业/概念资金流，同花顺    | `moneyflow_ind_ths` / `moneyflow_cnt_ths` | **5000 可能不够，10000 够** | 同花顺行业、概念资金流文档显示 6000 分可调取。([Tushare][5])                   |
| 沪深港通资金流         |                          `moneyflow_hsgt` |                 **够** | 2000 分起；5000 分每分钟可提取 500 次，包含北向/南向资金。([Tushare][6])        |
| 公募基金持仓          |                          `fund_portfolio` |                 **够** | 5000 分以上可用，季度更新；8000 分以上频次更高。适合做“公募持仓”类特征。([Tushare][7])   |
| 龙虎榜机构明细         |                                `top_inst` |                 **够** | 5000 分起，返回龙虎榜机构买卖明细。注意它只覆盖上榜股票，不是全市场机构交易。([Tushare][8])    |
| 前十大股东 / 前十大流通股东 |    `top10_holders` / `top10_floatholders` |                 **够** | 2000 分以上可调，5000 分频次更高；可以间接抽取机构股东、持股比例等。([Tushare][9])      |
| 股东增减持           |                         `stk_holdertrade` |                 **够** | 2000 分起，记录重要股东/高管/公司增减持事件。([Tushare][10])                  |

这里要拆穿一个常见误区：**资金流入流出不等于真实机构净买入。** `moneyflow`、`moneyflow_dc`、`moneyflow_ths` 多数是按成交单大小或数据商口径推断的“主力/大单/超大单”，不是监管级账户穿透后的机构账户数据。它可以作为市场行为特征，但别把它当成“机构在告诉你明天涨停”。机构没那么慷慨，数据商也没那么神。

## 2. 这些数据能不能作为这个项目的特征？

**能，但现在不能直接无脑塞进去。**

我看了你上传的项目结构：
`market-data-platform` 是数据生产和发布层；`cross-sectional-trees` 是只读消费平台资产的低频截面研究仓；`quant-execution-engine` 只读目标持仓做执行。项目文档里明确写了数据流是：

```text
provider 数据 -> 平台资产目录 -> current contract -> 下游只读消费
```

而当前 A 股 contract 支持的 TuShare 资产主要是：

```text
instruments
trade_cal
daily
adj_factor
daily_basic
limit_status
daily_clean
normalized_fundamentals
pit_fundamentals
universe_by_date
universe_symbols
universe_meta
```

也就是说，**当前 contract 里没有 moneyflow、fund_portfolio、top_inst、top10_holders 这些资产**。另外，`cross-sectional-trees/configs/presets/a_share.yml` 现在默认特征基本是价格、成交量、技术指标，`fundamentals.enabled: false`，行业也默认关闭。现状很清楚：数据能作为特征，但工程入口还没铺好。

## 3. 我会怎么用这些数据做特征？

### A. 机构持仓类，优先级高

这类数据适合你的低频截面项目，因为你的主线是周/月频、截面排序、持仓导出。公募持仓、十大股东这种数据虽然慢，但噪音比日内资金流小一点，至少不像“主力净流入”那样每天给你一堆看似聪明的幻觉。

建议先做这些特征：

```text
fund_hold_mv_to_float_mv
fund_hold_mv_to_total_mv
fund_hold_amount_to_float_share
fund_count_holding_stock
fund_hold_mv_qoq_change
fund_hold_ratio_qoq_change
top10_inst_hold_ratio
top10_float_inst_hold_ratio
holder_concentration_top10
days_since_fund_report
days_since_holder_report
```

关键处理方式：

```text
report_period 只是报告期，不是可用日期。
ann_date / disclosure_date 才接近模型可见日期。
available_date 应该设成 ann_date 后的下一个可交易日，或按你实际收盘后跑模型的时点决定。
```

如果你直接用 `2024Q4` 持仓去预测 2024 年 12 月底之后的收益，但这份持仓实际 2025 年 1 月/3 月才披露，那就是未来函数。漂亮的回测，一坨假的。

### B. 资金流类，能用，但要克制

资金流更适合做短中期行为特征。不要直接喂原始净流入金额，市值大的股票天然金额大，这种特征会变成“我发现了贵州茅台很大”这种惊天废话。

建议做标准化/滚动特征：

```text
mf_net_amount_5d_to_amount
mf_net_amount_20d_to_amount
mf_net_amount_60d_to_amount
mf_net_amount_20d_to_float_mv
mf_elg_net_5d_to_amount
mf_lg_net_20d_to_amount
mf_buy_sell_imbalance_20d
mf_net_amount_20d_industry_zscore
mf_net_amount_20d_cs_rank
```

如果用 `moneyflow_dc` 或 `moneyflow_ths`，建议至少做：

```text
主力净流入 / 成交额
超大单净流入 / 成交额
大单净流入 / 成交额
5/20/60 日滚动和
滚动变化率
截面 rank 或 zscore
```

对当前项目尤其要注意：你的 `a_share.yml` 里 `label.shift_days: 1`，这意味着模型特征最好代表“今天收盘后可见，下一交易日再交易”。资金流数据通常盘后更新，所以**如果你是在收盘后生成信号、次日交易，使用当日资金流是可以讨论的；如果你假设盘中交易，那就必须至少滞后一日。**

### C. 龙虎榜机构明细，只能当稀疏事件特征

`top_inst` 很诱人，但它只覆盖龙虎榜股票。它不是全市场日度机构交易数据。适合做事件特征：

```text
top_inst_net_buy_to_amount
top_inst_buy_count_20d
top_inst_sell_count_20d
days_since_top_inst_buy
is_top_inst_event_20d
```

这种特征缺失率会很高，不能直接 complete-case 过滤。否则你的训练集会被砍成一小片，还以为模型变精了，其实只是样本死了。

## 4. 对这个项目的接入方式

### 最快 MVP：先做一个外部特征 parquet

你可以先在 `market-data-platform` 外面或里面生成一个统一特征文件：

```text
artifacts/assets/tushare/a_share/alt_features/a_share_flow_ownership_latest/data/part.parquet
```

字段保持这样：

```text
trade_date
symbol
available_date
mf_net_amount_20d_to_amount
mf_elg_net_amount_20d_to_amount
fund_hold_mv_to_float_mv
fund_hold_mv_qoq_change
top10_inst_hold_ratio
top_inst_net_buy_20d_to_amount
...
```

然后在 `cross-sectional-trees` 里临时借用现有 `fundamentals.source: file` 的 join 机制。这个命名不优雅，但能先验证效果。人类工程里“先验证再重构”已经算文明了。

示例配置思路：

```yaml
fundamentals:
  enabled: true
  source: "file"
  file: "artifacts/assets/tushare/a_share/alt_features/a_share_flow_ownership_latest/data"
  required: false
  ffill: false
  allow_missing_features: true
  fields:
    - available_date
  features:
    - mf_net_amount_20d_to_amount
    - mf_elg_net_amount_20d_to_amount
    - fund_hold_mv_to_float_mv
    - fund_hold_mv_qoq_change
    - top10_inst_hold_ratio
    - top_inst_net_buy_20d_to_amount

features:
  list:
    - sma_20
    - sma_60
    - sma_120
    - sma_5_diff
    - sma_10_diff
    - sma_20_diff
    - sma_60_diff
    - sma_120_diff
    - rsi_7
    - rsi_14
    - rsi_21
    - macd_hist
    - ret_5
    - ret_20
    - ret_60
    - rv_20
    - rv_60
    - volume_sma5_ratio
    - volume_sma20_ratio
    - volume_sma60_ratio
    - log_vol
    - vol
    - mf_net_amount_20d_to_amount
    - mf_elg_net_amount_20d_to_amount
    - fund_hold_mv_to_float_mv
    - fund_hold_mv_qoq_change
    - top10_inst_hold_ratio
    - top_inst_net_buy_20d_to_amount

  missing:
    method: "cross_sectional_median"
    features:
      - mf_net_amount_20d_to_amount
      - mf_elg_net_amount_20d_to_amount
      - fund_hold_mv_to_float_mv
      - fund_hold_mv_qoq_change
      - top10_inst_hold_ratio
      - top_inst_net_buy_20d_to_amount
    add_indicators: true
```

更干净的长期方案是新增一个 `alternative_features` 或 `panel_features` enrichment，不要继续把资金流/持仓塞进 `fundamentals` 这个篮子里。篮子能装，但它不是垃圾桶。

### 正式工程方案

在 `market-data-platform` 增加几个资产：

```text
tushare.a_share.moneyflow.v1
tushare.a_share.moneyflow_dc.v1
tushare.a_share.fund_portfolio_pit.v1
tushare.a_share.holder_pit.v1
tushare.a_share.top_inst_events.v1
tushare.a_share.alt_features.v1
```

每个资产都要有：

```text
manifest.yml
schema_version
provider
source_api
start_date / end_date
rows / symbols / files
quality report
```

然后更新：

```text
metadata/current_assets/a_share_current.json
metadata/dataset_registry.csv
```

`cross-sectional-trees` 再从 current contract 读取这些新资产。这样才符合你项目现有的“数据平台生产，研究仓只读消费”的架构。

## 5. 我会怎么排优先级？

我的建议顺序是：

1. **先接 `fund_portfolio` 公募基金持仓 PIT 特征。**
   它和你现在的低频截面策略匹配度最高，披露慢但含义清楚。

2. **再接 `moneyflow_dc` 或普通 `moneyflow` 的滚动标准化特征。**
   5000 分基本够用，覆盖日度行为信息。不要一开始就纠结 THS，先验证有没有增量。

3. **再接 `top10_holders` / `top10_floatholders`。**
   可做股东结构、机构持股、集中度、变动方向。

4. **最后接 `top_inst`。**
   这个是事件特征，覆盖稀疏，不能让它主导样本筛选。

5. **THS 资金流和行业/概念资金流放到 10000 分后再说。**
   有价值，但先别把预算献给“更多字段等于更多阿尔法”的古老邪教。

## 6. 研究上必须验证什么？

一个学术型研究者会先问：这些特征在控制了 `ret_5/20/60`、成交量、波动率、市值、行业以后，还有没有独立解释力？如果没有，它只是价格/成交量特征的华丽马甲。

一个实盘型研究者会先问：这些数据是否稳定更新？每天几点可用？历史回填和实时更新口径一致吗？停牌/ST/涨跌停股票怎么处理？如果不能回答，回测再好也只是给服务器烧香。

至少要跑这些检查：

```text
1. 单特征 IC / rank IC
2. 分行业 IC
3. 加入前后 benchmark ladder
4. 加入前后 CPCV
5. 加入前后 turnover / cost drag
6. feature importance 稳定性
7. 与已有技术特征的相关性
8. 覆盖率和缺失率
9. PIT 泄漏检查
10. ablation：只加 holdings、只加 moneyflow、两者都加
```

当前 evidence 里 turnover/capacity 的长窗口压力测试还处于 pending，所以这些新特征应该先作为实验组，不应该直接推到 production gate。先证明它们能提供增量，再让它们进入正式候选。

## 直接建议

如果你只是要验证这条路线：**5000 分够开始。**
可以拿 `fund_portfolio`、`moneyflow`、`moneyflow_dc`、`top_inst`、`top10_holders`、`top10_floatholders`、`stk_holdertrade` 这些核心数据。

如果你想减少权限摩擦、接 THS 资金流/特色数据，并且预算不敏感：**10000 分更省事。**
但别期待 10000 分让普通接口全面飞升，官方表里 5000 和 10000 的常规接口频次都是 500 次/分钟，10000 的主要差异是特色数据权限。([Tushare][1])

我会先做一个 `a_share_flow_ownership_features` MVP，只放 8 到 12 个经过 PIT 处理的特征，跑一轮 feature evidence 和 CPCV。要是连这都打不过现有价格/成交量 baseline，就别急着买更贵权限，先把这条路埋了，给它立块小碑：**“死于没有增量信息。”**

[1]: https://tushare.pro/document/1?doc_id=290 "Tushare数据"
[2]: https://tushare.pro/document/2?doc_id=170&utm_source=chatgpt.com "Tushare数据"
[3]: https://tushare.pro/document/2?doc_id=349&utm_source=chatgpt.com "Tushare数据"
[4]: https://tushare.pro/document/2?doc_id=348&utm_source=chatgpt.com "Tushare数据"
[5]: https://tushare.pro/document/2?doc_id=343&utm_source=chatgpt.com "Tushare数据"
[6]: https://tushare.pro/document/2?doc_id=47&utm_source=chatgpt.com "Tushare数据"
[7]: https://tushare.pro/document/2?doc_id=121&utm_source=chatgpt.com "Tushare数据"
[8]: https://tushare.pro/document/2?doc_id=107&utm_source=chatgpt.com "Tushare数据"
[9]: https://tushare.pro/document/2?doc_id=61&utm_source=chatgpt.com "Tushare数据"
[10]: https://tushare.pro/document/2?doc_id=175&utm_source=chatgpt.com "Tushare数据"
