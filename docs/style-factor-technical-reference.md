# A 股风格因子技术说明

> status: active
> owner: workspace
> last_verified: 2026-08-23
> source_of_truth: yes
> superseded_by: n/a

本页面向项目维护者，记录风格因子模块的运行入口、字段映射、产物契约和跨仓职责。面向研究读者的说明见[A 股风格因子研究方法与功能](style-factors.md)。

## 代码和输出位置

- 计算内核入口：`alpha_research.style_factors`（位于 `alpha-research/src/alpha_research/style_factors/`）
- 分位回测内核入口：`portfolio_backtester.style_factors_backtest`（位于 `portfolio-backtester/src/portfolio_backtester/style_factors_backtest.py`）
- 表现层入口：`style_factors`（位于 `strategy-research/style_factors/`，可 `python -m style_factors`）
- 标准输出目录：`$DATA_PLATFORM_ROOT/strategy_outputs/style-factors/<name>/`
- 标准发布入口：`style_factors.style_factor_attribution`
- 约束稳健性入口：`style_factors.robustness`
- 低换手定义诊断入口：`style_factors.liquidity_diagnostics`

## 因子标识

| 内部标识 | 中文名称 |
| --- | --- |
| `size` | 市值因子 |
| `value` | 价值因子 |
| `momentum` | 21 日动量因子 |
| `quality` | 质量因子 |
| `earnings_yield` | 盈利收益率因子 |
| `lowvol` | 低波动因子 |
| `growth` | 成长因子 |
| `leverage` | 低杠杆因子 |
| `beta` | 低贝塔因子 |
| `liquidity` | 低换手因子 |
| `liquidity_flow` | 大单资金流因子 |
| `chip_concentration` | 筹码集中度因子 |
| `institution_holding` | 机构持仓因子 |
| `fund_breadth` | 公募持股广度因子 |
| `fund_breadth_change` | 公募持股广度变化因子 |
| `fund_ownership` | 公募持仓比例因子 |
| `fund_ownership_change` | 公募持仓比例变化因子 |
| `dividend_yield` | 股息率因子 |
| `ps_value` | 市销率价值因子 |

## 本地研究运行

完整运行：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run --project strategy-research python -m style_factors \
  --outdir artifacts/style_analysis
```

快速调试从 2020 年开始读取分区：

```bash
uv run --project strategy-research python -m style_factors \
  --quick \
  --outdir artifacts/style_analysis_quick
```

## 约束稳健性运行

约束稳健性入口独立写入调用方指定目录，不会自动更新共享正式版本：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run --project strategy-research python -m style_factors.robustness \
  --baseline-artifacts /path/to/full-raw-artifacts \
  --constraints-dir /path/to/tushare_constraints_20260802 \
  --pit-vintage-dir /path/to/fundamentals_vintages/vintage=20260802 \
  --outdir /tmp/style-factor-robustness
```

该入口读取 `daily_clean`、形成日股票池、历史特殊处理状态、`suspend_d`、退市日期和封存的时点财务数据。执行模型包含下一交易日收盘调仓、涨跌停与停牌订单阻塞、按实际成交金额扣费，以及退市末端收益压力情景。

`margin_detail` 和 `slb_sec_detail` 用于构造已报告借券活动代理。该代理缺少真实券源、费率、召回和可借数量。

## 低换手定义诊断

低换手专题入口比较月末单日换手率、20 日和 60 日平均换手率、20 日和 60 日中位换手率，并同时生成市值和低波动联合中性化结果：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run --project strategy-research python -m style_factors.liquidity_diagnostics \
  --baseline-artifacts /path/to/current-style-factor-artifacts \
  --outdir artifacts/liquidity_factor_diagnostics
```

`--baseline-artifacts` 用于核对月末单日口径与当前标准算法的逐日收益。对账存在差异时，运行会直接失败。滚动窗口默认要求至少 75% 的有效观察，可以通过 `--minimum-coverage` 调整。

## 策略归因

策略收益文件的第一列为日期索引，第一条数据列为小数口径的日收益：

```csv
date,return
2024-01-02,0.0031
2024-01-03,-0.0018
```

运行命令：

```bash
uv run --project strategy-research python -m style_factors \
  --strategy-csv returns.csv \
  --strategy-name strategy \
  --outdir artifacts/style_analysis_strategy
```

全样本归因写入 `strategy_attribution.json`，逐年归因写入 `strategy_attribution_yearly.csv`。

## 标准发布

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run --project strategy-research python -m style_factors.style_factor_attribution \
  --out-name 20260629
```

标准发布先在同目录完成暂存文件，校验全部文件后原子重命名为 `<out-name>/`，最后原子更新 `latest.txt`。已有版本目录不会被覆盖。

## 标准产物

| 文件 | 内容 |
| --- | --- |
| `factor_summary.json` | 全样本收益、波动、夏普比率、回撤和胜率 |
| `factor_correlation.json` | 因子多空日收益相关性 |
| `factor_yearly.csv` | 逐年和年初至今表现 |
| `factor_<name>_daily.csv` | 单个因子的多空日收益 |
| `strategy_attribution.json` | 可选的全样本策略归因 |
| `strategy_attribution_yearly.csv` | 可选的逐年策略归因 |
| `style_analysis_report.md` | 自动生成的研究报告 |
| `style_factor_nav.png` | 单因子净值图 |
| `style_factor_comparison.png` | 多因子净值对比图 |
| `style_factor_corr.png` | 因子相关性热力图 |
| `style_factor_yearly.png` | 逐年因子收益图 |
| `meta.json` | 运行参数和数据范围 |
| `manifest.json` | 文件清单、校验值和数据沿袭信息 |

约束稳健性入口另行输出收益对照、成本与退市情景、因子诊断、逐因子日收益、晋级判断、运行口径、Markdown 附录和三张对照图。

低换手定义诊断另行输出以下产物：

| 文件 | 内容 |
| --- | --- |
| `liquidity_diagnostics_summary.csv` | 各定义的多头、多空、相对样本、单调性和风险指标 |
| `liquidity_diagnostics_quintiles.csv` | 每种定义的五组收益明细 |
| `liquidity_diagnostics_daily.csv` | 五组、多空和多头相对样本的日收益 |
| `liquidity_diagnostics_meta.json` | 数据范围、覆盖率、对账结果和运行口径 |
| `liquidity_factor_diagnostics.md` | 自动生成的中文诊断报告 |
| `liquidity_signal_nav.png` | 各定义的多空净值图 |
| `liquidity_quintile_returns.png` | 五组年化收益图 |
| `liquidity_long_only.png` | 多头、相对样本和多空收益对照图 |

## 数据字段

长期基准主要使用 `daily`、`daily_basic`、`fina_indicator`、`cashflow`、`moneyflow_ths`、`holder_structure`、`fund_portfolio_features` 和申万行业成员历史。约束复核增加 `daily_clean`、形成日股票池、`namechange`、`st`、`suspend_d`、`stk_limit`、`margin_secs`、`margin_detail` 和 `slb_sec_detail`。

`fund_portfolio_features` 来自数据平台已经 PIT 化的公募基金持仓状态资产。数据平台先按基金披露日映射到可用交易日，并在基金下一次披露时替换该基金的旧持仓状态；研究层再用向后 as-of 方式把最后一次已知状态映射到月末形成日。形成日以前没有任何公募事件、但已进入该资产历史覆盖期的股票按 0 持仓保留，避免把研究样本偷偷收缩成“已经被公募持有的股票”。

公募持仓变化信号在相邻月末形成日之间计算。数据平台原始特征资产中的 `*_qoq_change` 是异步披露事件之间的差分，不直接作为标准年度风格因子的季度变化定义。当前四个候选信号分别使用公募基金持有数量、该数量的形成日变化、各基金 `stk_float_ratio` 合计，以及该合计的形成日变化。它们仍属于研究候选，需经过覆盖率、增量 IC、市值/流动性暴露、分组单调性和成本检验后再决定是否晋级生产策略。

低换手定义诊断逐日读取 `daily_basic` 中的换手率，在每个月末形成 20 日和 60 日平均及中位统计。市值控制使用总市值，低波动控制使用前 21 个收益观察值的波动率。

财务指标按 `ann_date` 对齐。非正 `PB` 和 `PE_TTM` 只影响对应估值因子的样本。`period_return` 表示实际覆盖期收益，`is_partial_year` 标记部分年度，主报告使用几何年化收益。

## 跨仓职责

- 因子研究接口归属 `alpha-research`。
- 回测和归因能力归属 `portfolio-backtester`。
- 运行编排和标准产物发布归属 `strategy-pipeline`。
- 因子计算内核（`alpha_research.style_factors`）归属 `alpha-research`，分位回测内核（`portfolio_backtester.style_factors_backtest`）归属 `portfolio-backtester`，表现层（`strategy-research/style_factors`）归属 `strategy-research`（ADR-0006 拆分后无顶层参考实现）。
- 下游系统通过版本化文件契约消费结果，避免维护第二套同源研究算法。

跨仓协作使用公开命令行入口和文件契约。消费方应先校验 `manifest.json` 中的文件清单和校验值，再读取研究产物。
