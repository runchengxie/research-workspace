# 全市场 long-only 风格因子分析：2008-2026 三因子落地形态

## 研究问题

既有研究（3factor_vs_top800、3factor_deep_dive）测量的是全市场 Q5-Q1 的
多空价差。多空组合需要做空，且 Q5-Q1 的价差分布比真实多头组合更容易被摊薄。
本分析回答一个更贴近实盘的问题：同样的三因子在纯多头、Top-K、次交易日成交、
含成本约束下能拿到多少收益，以及这种落地形态的收益随时间如何衰减。

分析分两个阶段：

1. Phase 2（2008-2026）：全市场三因子（小市值、低换手、成长）long-only。
   成长因子依赖 fina_indicator，此前数据平台只有 2015 起的数据。本次通过
   官方归档工具回填了 2008 起的 fina_indicator vintage（含 netprofit_yoy、
   or_yoy 等成长字段），使三因子 2008 起即可计算。
2. Phase 1（2015-2026）：同一套三因子，分别在两个 universe 上验证。

## 数据与执行约定

- 区间：Phase 2 为 2008-01-31 至 2026-08-18；Phase 1 为 2015-01-01 至 2026-08-18。
- 股票池：全 A 或时点正确 top800（Phase 1 对比）；上市至少 180 天（Phase 2 raw
  数据无上市天数字段，改用价格与流动性过滤）、20 日成交额中位数不低于 2,000 万元。
- 信号：截面 zscore，方向沿用 style_factors 约定：小市值 = -z(size)、
  低换手 = +z(liquidity)、成长 = +z(growth)；复合分数为三者相加。
- 选股：月末形成信号，月度 Top-100 等权，下一交易日收盘成交。
- 成本：单边 30bp，按换手率扣除。
- 交易限制：Phase 1（clean 数据）过滤 ST、停牌、涨跌停；Phase 2（raw 数据）
  2008 起无 ST/停牌/涨跌停标记，退化为价格与流动性过滤。
- 收益口径：Phase 1 用复权价日收益，Phase 2 用未复权 pct_chg。

## 核心结果

### 全周期对比（Top-100 月度再平衡，成本 30bp）

| 变体 | Phase 2 2008-2026 | Phase 1 full 2015-2026 | Phase 1 top800 2015-2026 |
| --- | --- | --- | --- |
| 复合三因子 | 年化 15.0%、Sharpe 0.62、总回报 +1075% | 年化 6.8%、Sharpe 0.37、+108% | 年化 -6.2%、Sharpe -0.04、-51% |
| 小市值 | 年化 14.5%、Sharpe 0.60 | 年化 6.9%、Sharpe 0.37 | 年化 -17.0%、Sharpe -0.37 |
| 低换手 | 年化 7.5%、Sharpe 0.40 | 年化 -3.4%、Sharpe 0.01 | 年化 -6.4%、Sharpe -0.12 |
| 成长 | 年化 1.5%、Sharpe 0.20 | 年化 0.1%、Sharpe 0.15 | 年化 -7.7%、Sharpe -0.09 |

### 无摩擦分位腿（long-only Q1/Q5，信号曲线）

| 因子 | 2008-2026 Q5-Q1 年化 | 2008-2026 Q5 年化 | 2015-2026 Q5-Q1 年化 |
| --- | --- | --- | --- |
| 小市值 | +26.0%（Sharpe 1.71） | +26.1% | +13.0% |
| 低换手 | +26.1%（Sharpe 2.02） | +18.3% | +18.2% |
| 成长 | +8.6%（Sharpe 1.37） | +13.6% | +6.7% |

### Phase 2 年度收益（复合三因子）

| 年份 | 收益 | 年份 | 收益 |
| --- | --- | --- | --- |
| 2008 | -41.2% | 2018 | -28.2% |
| 2009 | +123.5% | 2019 | +29.4% |
| 2010 | +11.7% | 2020 | +10.0% |
| 2011 | -32.0% | 2021 | +16.8% |
| 2012 | +15.8% | 2022 | -11.2% |
| 2013 | +30.4% | 2023 | +4.7% |
| 2014 | +41.7% | 2024 | -2.1% |
| 2015 | +277.5% | 2025 | +44.5% |
| 2016 | +18.0% | 2026 至今 | -2.3% |
| 2017 | -19.5% | | |

## 关键发现

1. 2008-2026 全周期三因子多头复合表现强劲（年化 15%、Sharpe 0.62），主要来自
   小市值与低换手两个因子，成长贡献最小（年化 1.5%）。这与长期 Q5-Q1 价差研究
   的方向一致：小市值和低换手是主导 alpha 源。
2. 收益随时间显著衰减。同口径（full 全市场、Top-100、30bp）下，2015-2026 复合
   年化只有 6.8%（Sharpe 0.37），不足 2008-2026 的一半。2017 年后小市值与低换手
   风格整体回撤，2018-2024 连续多年负收益，2025 恢复。
3. top800 池内因子失效。在流动性最好的 800 只里，三个因子全部转负，说明这些
   因子的 alpha 集中在中小市值段，不可直接迁移到大票池。
4. 单因子成长最弱。无论全周期还是 2015 以来，成长因子的 long-only 贡献都远小于
   小市值和低换手，且 2015 以来 Sharpe 仅 0.15。
5. 相比多空价差，long-only 形态损失明显。例如低换手 Q5-Q1 全周期年化 26%，但
   long-only Top-100 只有 7.5%；小市值 Q5-Q1 26% 对应 long-only 14.5%。价差研究
   高估了可实现的收益，尤其是对低换手因子。

## 复现

```bash
# 在 strategy-research/experiments/qlib_pilot 下
PYTHONPATH=".:../../alpha-research/src:../../portfolio-backtester/src" \
  python long_only_style_analysis.py \
    --phase 2 --start-date 2008-01-01 --end-date 2026-08-18 \
    --outdir <out> --workers 16 --top-k 100
# Phase 1 full：--phase 1 --start-date 2015-01-01 --universe full
# Phase 1 top800：--phase 1 --start-date 2015-01-01 --universe top800
```

产物（每个 outdir）：

- long_only_quantiles_P{phase}_{universe}.csv：无摩擦 Q1/Q5/Q5-Q1 分位腿
- long_only_topk_P{phase}_{universe}.csv：含成本 Top-K 回测统计
- long_only_annual_P{phase}_{universe}.csv：年度收益
- long_only_daily_returns_P{phase}_{universe}.parquet：日收益序列
- panel_P{phase}_{universe}.parquet：因子面板（含打分）

## 数据来源

成长因子 2008 起的数据来自回填的 fundamentals vintage：

- 目录：data-root/experiments/style-factor-full-history-20260819/assets/tushare/
  a_share/fundamentals_vintages/vintage=20260819/
- 回填工具：market-data-platform/scripts/operations/
  archive_tushare_fundamentals_vintage.py（官方归档工具）
- 覆盖：fina_indicator、income、balancesheet、cashflow 四个数据集 2008-2026。
  fina_indicator 含 roe、roa、netprofit_yoy、or_yoy、debt_to_assets 等因子所需字段。
- loader 接入：strategy-research/style_factors/data.py 优先识别
  fundamentals_vintages/vintage=*/normalized/*/data 下的最新 vintage，再回退到
  2015 起的 top800_union 数据。