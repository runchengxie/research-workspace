# A 股风格因子分析

> status: active
> owner: workspace
> last_verified: 2026-08-02
> source_of_truth: yes
> superseded_by: n/a

本页说明顶层 `src/style_factors` 的用途、运行方式和输出约定。这个模块用于 A 股市场风格复盘和策略收益归因，正式输出目录是：

```text
$DATA_PLATFORM_ROOT/strategy_outputs/style-factors/<name>/
```

逐年市场风格切换的解读示例见
[A 股年度市场风格解读：2008-2026](style-factor-market-regimes-2008-2026.md)。
完整 2008–2026 股票池、交易约束、成本和退市压力情景的对照见
[A 股风格因子 2008–2026 全历史约束稳健性附录](style-factor-constrained-robustness-2008-2026.md)。

## 它是什么

`style_factors` 是一个参考 Barra CNE5 思路的全市场风格代理因子分析工具。它从
`market-data-platform` 发布的 TuShare A 股日线、日频估值和可选财务指标中构造 15 个风格因子：

| 因子 | 当前方向 | 主要输入 | 数据来源 |
| --- | --- | --- | --- |
| Size 大市值 | 大市值 - 小市值 | `total_mv` | daily_basic |
| Value 低估值 | 低市净率（PB） - 高 PB | `pb` | daily_basic |
| Momentum 动量 | 高 21 日动量 - 低 21 日动量 | `close` | daily |
| Earnings Yield 盈利估值 | 低 PE_TTM - 高 PE_TTM | `pe_ttm` | daily_basic |
| LowVol 低波动 | 低 21 个收益观察值波动 - 高波动 | `close` | daily |
| Growth 成长 | 高增长 - 低增长 | `netprofit_yoy`、`or_yoy` | fina_indicator |
| Leverage 低杠杆 | 低资产负债率 - 高资产负债率 | `debt_to_assets` | fina_indicator |
| Beta 低贝塔 | 低 252 日 beta - 高 252 日 beta | `pct_chg` | daily |
| Liquidity 低换手 | 低换手 - 高换手 | `turnover_rate` | daily |
| Quality 复合质量 | 高 ROE + 低杠杆 + 盈利稳定 + 现金流质量 | `roe`、`debt_to_assets`、最近 8 个报告期 `netprofit_yoy` 的滚动 std、`n_cashflow_act/net_profit` | fina_indicator + cashflow |
| LiquidityFlow 大单资金流 | 大单净买占比高 - 低 | moneyflow_ths 大单净买 | moneyflow_ths（本地） |
| ChipConcentration 筹码集中度 | 前十大流通股集中度高 - 低 | holder_structure 前十大流通股占比 | holder_structure（本地） |
| InstitutionHolding 机构持仓 | 前十大机构流通持股占比高 - 低 | holder_structure 前十大机构持股 | holder_structure（本地） |
| DividendYield 股息率 | 股息率高 - 低 | daily_basic `dv_ttm` | daily_basic（本地） |
| PSValue 市销率价值 | 低 PS_TTM - 高 PS_TTM | `ps_ttm` | daily_basic（本地） |

日频价格序列先计算滚动动量、波动和 beta。估值、财务、辅助数据与行业历史只在每个月最后一个交易日拼接。每个因子按自己的非缺失样本独立做截面缩尾（1%/99%）、行业内去均值和标准化，不再要求股票同时具备正 PB、正 PE 等其他因子的输入。随后按因子排序分成 5 组，下一交易日起持有。两腿月初等权建仓、月内固定份额自然漂移，到下个月末再平衡。输出最高五分位组合减最低五分位组合的日收益序列。

> 复合质量因子（`quality` / `factor_quality`）已于 2026-07 从 `1/PE_TTM` 估值代理重构为
> 等权复合：ROE、低资产负债率、盈利稳定性（按最近 8 个已公告报告期计算 `-rolling_std(netprofit_yoy, 8)`）、现金流质量
> （`n_cashflow_act / net_profit`），各子指标先截尾再横截面 z 后合成。旧版把 `1/PE_TTM` 当作质量
> 是误称，现已与 `earnings_yield`（盈利估值）拆分为两个独立因子。

这个工具适合做市场风格复盘、候选策略收益归因和研究解释。账户级风险引擎还需要补充协方差风险预测、特异风险建模、组合优化和 PIT 指数成分约束。当前只内置信号层行业去均值，不是组合层严格行业中性（见下方方法边界）。

## 审计基准运行

2026-08-01 的修正后全量复算使用以下输入窗口：

```text
daily / daily_basic: 2008-01-02 ~ 2026-07-31
formation dates: 2008-01-31 ~ 2026-07-31（223 个月末）
factor observations: 735,938 stock-months
SW L1 membership coverage: 89.6%
```

这段日期用于本次算法审计，不代表正式发布目录的 current 指针已经切换到该口径。全量运行默认读取执行时可用的全部日期。`--quick` 从 `2020-01-01` 开始读取分区，用于调试和快速产出。

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

生成独立约束稳健性附录，不更新共享 `latest`：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run python -m src.style_factors.robustness \
  --baseline-artifacts /path/to/full-raw-artifacts \
  --constraints-dir /path/to/tushare_constraints_20260802 \
  --pit-vintage-dir /path/to/fundamentals_vintages/vintage=20260802 \
  --outdir /tmp/style-factor-robustness
```

该入口读取 `daily_clean`、PIT 形成日股票池、namechange 重建 ST、`suspend_d`、
instruments 退市日期和 sealed PIT v2，模拟下一交易日收盘起的涨跌停与停牌订单阻塞，
按实际成交名义额扣成本，并输出退市末端收益压力情景。`margin_detail` / `slb_sec_detail`
只形成已报告借券活动代理，退市真实收益、真实券源和 revision-safe 历史版本仍是显式未解决项。

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

## 报告与历史运行

仓库内曾保留 3 个历史运行目录。它们对应 3 次不同参数和代码版本的运行，并非 3 种固定报告模板：

| 目录 | 口径 | 用途 |
| --- | --- | --- |
| `artifacts/style_analysis_2008/` | 2026-07-30 的 15 因子全历史运行 | 旧基准，已被本次审计发现的方法问题影响 |
| `artifacts/style_analysis_codex_full_20260629/` | 旧 9 因子全历史运行 | legacy 对照，不应与现口径拼接 |
| `artifacts/style_analysis_codex_quick_20260629/` | 旧 9 因子、2020 年以后 quick 运行 | 调试样本，不能冒充全历史报告 |

每次完整运行实际生成 1 份 Markdown 主报告、4 张 PNG 图和 JSON/CSV 明细。解释层另有[年度风格解读](style-factor-market-regimes-2008-2026.md)与[Value 长周期分析](value-regime-18y.md)，两者均不是自动生成物，必须在算法或数据口径变化后人工复核。

## 输出文件

| 文件 | 内容 |
| --- | --- |
| `factor_summary.json` | 全样本累计收益、几何年化收益、兼容旧字段的日均复利年化、波动、夏普、回撤和胜率 |
| `factor_correlation.json` | 因子多空日收益相关性 |
| `factor_yearly.csv` | 因子逐年/年初至今收益、起止日期、是否完整年度、波动、夏普和回撤 |
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

约束稳健性入口另行输出 `factor_robustness_comparison.csv`、
`factor_robustness_scenarios.csv`、`factor_robustness_diagnostics.csv`、每个因子的 constrained
gross/net 日收益、`robustness_meta.json`、Markdown 附录和对照图。这些文件默认只写调用方指定的
临时目录，不属于标准发布契约。

标准发布先写入同目录 staging，所有文件与 `manifest.json` 完成后再原子重命名为
`<out-name>/`，最后原子更新 `latest.txt`。已经存在的版本目录不会被覆盖。消费方必须使用
`research-contracts` 校验文件清单和 SHA-256 后再渲染，不得直接信任半成品目录。

## 方法边界

- 估值类输入中，非正 PB/PE_TTM 会被视为对应因子的缺失值，不会再连带删除 Size、Momentum 等其他因子的股票。
- Growth 和 Leverage 依赖 `fina_indicator`，按 `ann_date` 对齐，避免使用尚未公告的数据。
- Quality 的盈利稳定性在财报行上按最近 8 个已公告报告期计算，最少 4 期。缺少 ROE 的股票不生成 Quality 分数。
- 财务指标来自当前可用 legacy raw fundamentals 链路，早期数据还会回退到 `a_share_top800_union`。当前长历史运行没有完整消费 `daily_clean`、逐日 PIT 股票池和 revision-safe PIT v2，因此只属于 screen-grade 历史代理，不应标为 decision-grade 或可交易回测。
- 申万历史成员表按 `in_date <= trade_date <= out_date` 对齐。每个因子先在行业内 demean，再做全截面 z-score。无行业匹配的股票作为残差组处理。该方法降低信号的行业均值暴露，但没有约束多空两腿的行业权重，不能称为严格行业中性。
- 因子收益是全市场代理多空收益。月内缺失收益按 0 处理以保留停牌股票的资本权重，但仍缺少退市末日收益、交易成本、涨跌停可成交性、ST、新股和做空可实现性约束。
- 独立 robustness 入口对上述限制做压力测试：使用 180 天上市期、PIT 形成日股票池、namechange 重建历史 ST、`st` 事件旁证、`suspend_d` 显式停牌、涨跌停延迟成交、实际换手成本、退市末端收益情景和 sealed PIT v2。它仍不能补齐真实退市清算收益、逐日真实券源/费率/召回/可借数量及 2026-08-02 以前 revision-safe 的历史财务版本，因此保持 screen-grade。
- `period_return` 是实际覆盖期收益。首年、末年或短覆盖因子的年度行会标记 `is_partial_year=true`。主报告使用几何年化。`annual_ret` 旧字段仅为兼容既有消费者。
- 归因只纳入策略样本期覆盖率至少 80% 的因子，并基于完整交集回归。alpha 来自 OLS 截距，不使用均值必为零的残差。

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
