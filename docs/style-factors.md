# A 股风格因子分析

> status: active
> owner: workspace
> last_verified: 2026-06-29
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
`market-data-platform` 发布的 TuShare A 股日线、日频估值和可选财务指标中构造 9 个风格因子：

| 因子 | 当前方向 | 主要输入 |
| --- | --- | --- |
| Size 大市值 | 大市值 - 小市值 | `total_mv` |
| Value 低估值 | 低 PB - 高 PB | `pb` |
| Momentum 动量 | 高 21 日动量 - 低 21 日动量 | `close` |
| Quality 盈利 | 低 PE_TTM - 高 PE_TTM | `pe_ttm` |
| LowVol 低波动 | 低 20 日波动 - 高 20 日波动 | `close` |
| Growth 成长 | 高增长 - 低增长 | `netprofit_yoy`、`or_yoy` |
| Leverage 低杠杆 | 低资产负债率 - 高资产负债率 | `debt_to_assets` |
| Beta 低贝塔 | 低 252 日 beta - 高 252 日 beta | `pct_chg` |
| Liquidity 低换手 | 低换手 - 高换手 | `turnover_rate` |

每个交易日先做截面缩尾和标准化。每个月最后一个交易日按因子排序分成 5 组，等权持有到下个月末，输出最高五分位组合减最低五分位组合的日收益序列。

这个工具适合做市场风格复盘、候选策略收益归因和研究解释。账户级风险引擎还需要补充行业中性化、协方差风险预测、特异风险建模、组合优化和 PIT 指数成分约束。

## 数据窗口

本机共享数据当前覆盖：

```text
daily / daily_basic: 2008-01-02 ~ 2026-06-26
```

全量运行默认读取全部可用日期。`--quick` 从 `2020-01-01` 开始读取分区，用于调试和快速产出。

## 运行命令

本地临时输出：

```bash
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
  uv run python -m src.style_factors \
  --outdir artifacts/style_analysis
```

快速调试：

```bash
uv run python -m src.style_factors \
  --quick \
  --outdir artifacts/style_analysis_quick
```

发布到共享数据根的标准位置：

```bash
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
  uv run python src/style_factors/style_factor_attribution.py \
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
  --strategy-name cstree \
  --outdir artifacts/style_analysis_cstree
```

归因使用 OLS：

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
| `manifest.json` | 仅标准发布脚本生成，记录文件清单和 latest 指针 |

## 方法边界

- 估值类输入中，非正 PB/PE_TTM 会被视为缺失，避免把异常值当成极端低估值或高质量。
- Growth 和 Leverage 依赖 `fina_indicator`，按 `ann_date` 对齐，避免使用尚未公告的数据。
- 财务指标来自当前可用 raw fundamentals 链路；正式研究引用时仍应结合 `market-data-platform` 的 PIT fundamentals 质量说明。
- 因子收益是全市场等权多空代理因子收益，暂未纳入交易成本、涨跌停成交约束、ST 过滤和行业中性化。
- 2026 年这类未完整年度的 `period_return` 是年初至数据截止日收益，`annual_return` 是按日均收益年化。
