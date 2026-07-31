# A 股风格因子分析

> status: active
> owner: workspace
> last_verified: 2026-07-30
> source_of_truth: yes
> superseded_by: n/a

本页说明顶层 `src/style_factors` 的用途、运行方式和输出约定。这个模块用于 A 股市场风格复盘和策略收益归因，正式输出目录是：

```text
$DATA_PLATFORM_ROOT/strategy_outputs/style-factors/<name>/
```

逐年市场风格切换的解读示例见
[A 股年度市场风格解读：2008-2026](style-factor-market-regimes-2008-2026.md)。

## 它是什么

`style_factors` 是一个参考 Barra CNE5 思路的全市场风格代理因子分析工具。它从
`market-data-platform` 发布的 TuShare A 股日线、日频估值和可选财务指标中构造 15 个风格因子：

| 因子 | 当前方向 | 主要输入 | 数据来源 |
| --- | --- | --- | --- |
| Size 大市值 | 大市值 - 小市值 | `total_mv` | daily |
| Value 低估值 | 低市净率（PB） - 高 PB | `pb` | daily_basic |
| Momentum 动量 | 高 21 日动量 - 低 21 日动量 | `close` | daily |
| Earnings Yield 盈利估值 | 低 PE_TTM - 高 PE_TTM | `pe_ttm` | daily_basic |
| LowVol 低波动 | 低 20 日波动 - 高 20 日波动 | `close` | daily |
| Growth 成长 | 高增长 - 低增长 | `netprofit_yoy`、`or_yoy` | fina_indicator |
| Leverage 低杠杆 | 低资产负债率 - 高资产负债率 | `debt_to_assets` | fina_indicator |
| Beta 低贝塔 | 低 252 日 beta - 高 252 日 beta | `pct_chg` | daily |
| Liquidity 低换手 | 低换手 - 高换手 | `turnover_rate` | daily |
| Quality 复合质量 | 高 ROE + 低杠杆 + 盈利稳定 + 现金流质量 | `roe`、`debt_to_assets`、`netprofit_yoy` 滚动 std、`n_cashflow_act/net_profit` | fina_indicator + cashflow |
| LiquidityFlow 大单资金流 | 大单净买占比高 - 低 | moneyflow_ths 大单净买 | moneyflow_ths（本地） |
| ChipConcentration 筹码集中度 | 前十大流通股集中度高 - 低 | holder_structure 前十大流通股占比 | holder_structure（本地） |
| InstitutionHolding 机构持仓 | 前十大机构流通持股占比高 - 低 | holder_structure 前十大机构持股 | holder_structure（本地） |
| DividendYield 股息率 | 股息率高 - 低 | daily_basic `dv_ttm` | daily_basic（本地） |
| PSValue 市销率价值 | 低 PS_TTM - 高 PS_TTM | `ps_ttm` | daily_basic（本地） |

每个交易日先做截面缩尾（1%/99%）和标准化。每个月最后一个交易日按因子排序分成 5 组，等权持有到下个月末，输出最高五分位组合减最低五分位组合的日收益序列。

> 复合质量因子（`quality` / `factor_quality`）已于 2026-07 从 `1/PE_TTM` 估值代理重构为
> 等权复合：ROE、低资产负债率、盈利稳定性（`-rolling_std(netprofit_yoy, 8)`）、现金流质量
> （`n_cashflow_act / net_profit`），各子指标先截尾再横截面 z 后合成。旧版把 `1/PE_TTM` 当作质量
> 是误称，现已与 `earnings_yield`（盈利估值）拆分为两个独立因子。

这个工具适合做市场风格复盘、候选策略收益归因和研究解释。账户级风险引擎还需要补充协方差风险预测、特异风险建模、组合优化和 PIT 指数成分约束，行业中性化已内置（见下方方法边界）。

## 参考运行窗口

2026-07-30 发布的参考运行使用以下输入窗口：

```text
daily / daily_basic: 2008-03-03 ~ 2026-07-29
```

这段日期用于复现该次报告，不代表 current 契约的实时截止日。全量运行默认读取执行时
可用的全部日期。`--quick` 从 `2020-01-01` 开始读取分区，用于调试和快速产出。

新因子覆盖受本地数据落地时间限制：`liquidity_flow`（moneyflow_ths）自 2026-02 起，
`chip_concentration` / `institution_holding`（holder_structure）自 2015-03 起。因此其统计结论
不应与长周期因子直接比较。

## 运行命令

本地临时输出：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run python -m src.style_factors \
  --outdir artifacts/style_analysis
```

快速调试：

```bash
uv run python -m src.style_factors \
  --quick \
  --outdir artifacts/style_analysis_quick
```

发布到共享数据根的标准位置（输出写入 `$DATA_PLATFORM_ROOT/strategy_outputs/style-factors/<out-name>/`）：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run python -m src.style_factors.style_factor_attribution \
  --out-name 20260629
```

## 策略归因

如果要解释某条策略日收益，传入一个 CSV。第一列必须是日期索引，第一条数据列必须是日收益，小数口径，例如 `0.01` 表示 `+1%`。

```csv
date,return
2024-01-02,0.0031
2024-01-03,-0.0018
```

运行：

```bash
uv run python -m src.style_factors \
  --strategy-csv returns.csv \
  --strategy-name strategy \
  --outdir artifacts/style_analysis_strategy
```

归因使用普通最小二乘（OLS）：

```text
strategy_daily_return = intercept + beta_size * size + ... + beta_liquidity * liquidity + residual
```

全样本结果写入 `strategy_attribution.json`，逐年结果写入 `strategy_attribution_yearly.csv`。年度文件包含每年的 `r_squared`、`annual_alpha`、各风格 `beta_*`、当年因子收益 `factor_return_*` 和贡献估算 `contribution_*`。

## 输出文件

| 文件 | 内容 |
| --- | --- |
| `factor_summary.json` | 全样本因子年化收益、波动、夏普、回撤和胜率 |
| `factor_correlation.json` | 因子多空日收益相关性 |
| `factor_yearly.csv` | 因子逐年收益、波动、夏普和回撤 |
| `factor_<name>_daily.csv` | 单个因子的多空日收益 |
| `strategy_attribution.json` | 可选，全样本策略 OLS 归因 |
| `strategy_attribution_yearly.csv` | 可选，逐年策略 OLS 归因和贡献拆分 |
| `style_analysis_report.md` | Markdown 报告 |
| `style_factor_nav.png` | 单因子净值图 |
| `style_factor_comparison.png` | 多因子净值对比 |
| `style_factor_corr.png` | 因子相关性热力图 |
| `style_factor_yearly.png` | 逐年因子收益图 |
| `meta.json` | 运行参数和输出 metadata |
| `manifest.json` | 标准发布脚本生成，包含 `research.style-factors.v1` schema、共享 artifact envelope、逐文件 SHA-256/大小和 lineage |

标准发布先写入同目录 staging，所有文件与 `manifest.json` 完成后再原子重命名为
`<out-name>/`，最后原子更新 `latest.txt`。已经存在的版本目录不会被覆盖。消费方必须使用
`research-contracts` 校验文件清单和 SHA-256 后再渲染，不得直接信任半成品目录。

## 方法边界

- 估值类输入中，非正 PB/PE_TTM 会被视为缺失，避免把异常值当成极端低估值或高盈利收益率。
- Growth 和 Leverage 依赖 `fina_indicator`，按 `ann_date` 对齐，避免使用尚未公告的数据。
- 财务指标来自当前可用 raw fundamentals 链路。正式研究引用时仍应结合 `market-data-platform` 的 PIT fundamentals 质量说明。
- 行业中性化已内置（PIT 申万 L1）：每个因子在合成 z-score 前，先按申万一级行业在每期截面内做行业内 demean，再做跨行业横截面 z-score，最终因子为行业中性。行业来源为本地落地的申万 PIT 行业（`sw_industry_member` + `sw_industry`），按 `in_date <= trade_date <= out_date` 判定每只股票在每个时点的 L1 行业，时点准确、无前视。不使用 `stock_basic.industry` 或 `ths_member` 静态映射做中性化（后者仅作为普通行业标签接入）。详尽说明见 `src/style_factors/helpers/_neutralize.py` 与 `factor_calc._standardize_factors`。
- 因子收益是全市场等权多空代理因子收益，暂未纳入交易成本、涨跌停成交约束、ST 过滤。
- 2026 年这类未完整年度的 `period_return` 是年初至数据截止日收益，`annual_return` 是按日均收益年化。

## 跨仓边界

`src/style_factors` 是本工作区风格因子计算、回测与归因的唯一权威实现
（`source_of_truth: yes`）。依据 2026-07-29 `research-workspace` 与 `market-intel` 整合评估报告的
边界划分，风格因子的职责归属如下：

- 因子定义与计算 → `alpha-research`（`style_factors` 当前承载参考实现）
- 回测与归因 → `portfolio-backtester`（`style_factors` 当前承载参考实现）
- 运行与产物发布 → `strategy-pipeline`（标准发布脚本产出 `manifest.json` 与 `latest` 指针）
- 报告渲染与飞书投递 → `market-intel`（仅消费，不重复实现）

产物通过版本化文件交接给下游：

```text
$DATA_PLATFORM_ROOT/strategy_outputs/style-factors/<name>/
```

`market-intel` 侧应只消费上述产物（读取 `style_factors[*]` 由
`strategy-pipeline/src/strategy_pipeline/pipeline/output_summary_sections.py` 完成），
不得维护第二套同源研究算法（`market-intel/src/a_share_analysis/style/` 为待收口的重复实现，
见其 `docs/boundary-contract.md`）。跨仓协作只走公开 CLI 与文件契约，不反向 import 本模块运行时内部。
