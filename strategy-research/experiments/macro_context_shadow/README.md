# Macro Context Shadow

`macro_context_shadow_v1` 验证宏观、产业和公司暴露是否为 A 股横截面预测带来稳定增量。实验处于 `exploration`，禁止生产发布。

实验固定比较 C0 至 C4 五组特征，并使用 5、20、60 个交易日标签，其中 20 日是唯一主选择周期。C4 增加披露后可用的公募基金拥挤度与增持特征。宏观序列必须来自 `cn_context` current contract，股票数据来自 `a_share` current contract。实验只组合 `market-data-platform`、`alpha-research` 和 `portfolio-backtester` 的公开 API，不在此目录复制通用实现。

## Fund context C4

### Fund PIT audit

The reproducible audit is separate from the return experiment and should be run
before interpreting any fund-only result:

```bash
PYTHONPATH=strategy-research \
  uv run --no-project --with duckdb --with pandas \
  python -m experiments.macro_context_shadow.fund_pit_audit \
  --data-root "$DATA_PLATFORM_ROOT" --output /tmp/fund-pit-audit.json
```

The 2026-08-29 audit found 16,725,952 raw rows, 20,430 funds, 7,305 symbols and
47 report periods. The derived feature asset passed the publication-date PIT
checks: 0 missing PIT dates, 0 invalid date order, 0 duplicate symbol/trade-date
rows, and 0 rows whose available date was not the next available trade date.
The raw asset contains 197 extra rows at its nominal grain: 34 are exact duplicate
rows and 163 duplicate keys contain differing portfolio fields. The latter needs a
provider-side deduplication/version-selection rule in `market-data-platform`; it is
an ingestion-quality issue, not evidence of an economic signal.

Further profiling shows the 163 conflicting rows are concentrated in older report
periods from 2017-06 through 2021-06, across approximately 35 funds and 116 stocks.
Many pairs have market value and share count close to a 2x ratio while percentage
fields differ, so the conflict cannot be safely resolved by taking the maximum,
dividing by two, or summing. The raw schema has no page, revision, or source-row
identifier that would justify one of those choices. The correct remediation is to
re-fetch those periods with immutable request/page evidence, or quarantine them
from revision-safe research; the loader therefore fails closed on the current
backfill.

The audit deliberately reports `pit_status=publication_date_pit` and
`revision_safe=false`. The current TuShare backfill preserves `ann_date` and the
derived one-trading-day availability rule, but it does not preserve a historical
retrieval/vintage archive for each observation. Fund-only findings therefore
remain exploration evidence and cannot be promoted as revision-safe Alpha.

基金特征来自 `market-data-platform` 的 `fund_portfolio_features` 与
`fund_top10_portfolio_features`。研究层只接受已经按 `available_date` 做过
as-of 过滤的行；`fund_context.build_fund_context_features` 不会自动前填或
把报告期数据提前到披露日前。

六个公开特征为：

```text
fund_crowding_level
fund_ownership_change
fund_holder_count_change
fund_low_crowding_accumulation
fund_top10_concentration
fund_accumulation_without_crowding
```

核心候选信号是“低当前持仓比例 + 持仓比例环比上升 + 前十大基金集中度不过高”。
它表达的是披露后的配置变化，不是实时资金流。C4 只能在 C3 的同一训练、验证、
成本和容量协议下比较增量，不能单独根据分组均值晋级。

### Current exploratory evidence

截至 2026-08-29，本地资产包含 660,903 条基金持仓特征记录、5,988 只股票和
47 个报告期。使用 2025-01 至 2026-07 的未来 20 日收益做描述性扫描，原始
“低拥挤 + 增持”相对其他股票的差值为：Shibor 下行 +0.99%、横盘 +0.53%、
上行 +0.09%。在行业和规模分组内重新排序后，差值变为：下行 +0.04%、横盘
+0.54%、上行 -0.39%。

这说明候选信号可能是条件化的，但当前 Shibor 历史大部分为 `reconstructed`，
基金历史也没有完整 provider vintage；以上结果不能作为 promotion evidence。

可复跑扫描：

```bash
PYTHONPATH=strategy-research \
  uv run --no-project --with duckdb --with pandas \
  python -m experiments.macro_context_shadow.run_fund_context_exploration \
  --data-root "$DATA_PLATFORM_ROOT" --output /tmp/fund-context-c4.json
```

按样本期拆分后，行业/规模中性结果显示：2025 年 Shibor 下行阶段信号相对
其他股票约领先 2.06 个百分点；2026 年同一状态反而落后约 1.96 个百分点。
该时间不稳定性是 C4 必须继续做 final OOS、CPCV/PBO 和成本检验的直接原因。

没有可靠 `available_at`、`source_retrieved_at`、vintage 或公司暴露的数据会拒绝进入 promotion-safe 运行。探索模式可以记录 reconstructed 历史，但任何依赖 reconstructed 数据的结论都不能晋级。

失败条件包括：PIT 可见性不完整、上下文数据过期、C2/C3/C4 没有样本外增量、
增量仅由 reconstructed 数据产生、成本后优势消失、行业或风格暴露漂移超限。
真实运行前必须先完成 final OOS、CPCV/PBO、换手成本、容量和 regime 稳定性证据。

运行入口：

```bash
python -m macro_context_shadow.run_contextual_alpha_shadow --data-root "$DATA_PLATFORM_ROOT" --dry-run
```

## Shibor first exploration

The first reproducible scan is an equal-weight market conditioning test. It uses
the visible `rates.shibor_3m` series, classifies five-observation changes as
`up`, `down`, or `flat`, and measures the next 20 trading-day equal-weight
market return. Historical rows marked `reconstructed` are reported separately
and do not support a promotion-safe conclusion.

```bash
PYTHONPATH=strategy-research \
  python -m experiments.macro_context_shadow.run_shibor_regime_exploration \
  --data-root "$DATA_PLATFORM_ROOT" \
  --as-of 20260831 \
  --output /tmp/shibor-regime.json
```

The current run is exploratory only: 411 regime rows are available, but only 3
are strict PIT rows. The observed 20-day means are `down=1.98%`, `flat=4.25%`,
and `up=2.59%`; these are descriptive results, not evidence of tradable Alpha.
The next stock-level experiment must add company exposures and PIT fundamentals
before testing C0/C1/C2 rankers.

## M0 portfolio shadow

The M0/M3 portfolio shadow uses the latest disclosed state, selects the top
quintile each day, equal-weights the selected names, and charges the configured
one-way turnover cost. M0 ranks holder-count change; M3 requires both holder-count
change and ownership-ratio change to be in the top quintile. It is deliberately
separate from the pooled event scan:

```bash
PYTHONPATH=strategy-research \
  uv run --no-project --with duckdb --with pandas \
  python -m experiments.macro_context_shadow.run_m0_portfolio_backtest \
  --data-root "$DATA_PLATFORM_ROOT" --turnover-bps 30 \
  --output /tmp/m0-portfolio.json
```

The latest rerun on 2026-08-29 produced these gross/net annualized returns:

```text
             2025 gross/net       2026 gross/net
M0           53.7% / 45.7%        -30.7% / -34.6%
M3           48.7% / 39.8%        -27.7% / -32.4%
```

Mean daily turnover was 7.0%/7.6% for M0 and 8.2%/9.1% for M3 in 2025/2026.
M3 therefore adds turnover without improving the 2025 result; both models are
negative in 2026. These figures are not promotion evidence: the history is
short, labels overlap, the fund source lacks a complete historical vintage
archive, and the portfolio rule still needs benchmark-relative attribution,
capacity and a frozen final-OOS protocol.

### Benchmark-relative read-through

### Clean-window sensitivity

As a sensitivity check, the portfolio runner now accepts `--start-date` and was
rerun from 2022-01-01, after the conflicted historical periods. This uses the
existing derived asset rather than a newly rebuilt raw asset, so it is a window
stability check, not a replacement for the pending clean rebuild.

The result does not improve the investment case. M0 underperformed the matched
benchmark after cost in every year from 2022 through 2026: approximately -27.5%,
-11.4%, -4.9%, -2.5%, and -7.9%, respectively. M3 was approximately -18.7%,
-15.5%, -9.0%, -4.1%, and -6.0%. M0's 2026 block-bootstrap probability of a
positive active mean was 0.55%; M3's was 2.55%. This suggests that excluding
the early duplicate periods alone is unlikely to rescue the fund-holder-count
signal.

An equal-weight return of the same clean A-share price universe was used as a
descriptive matched benchmark. With compounding and 30bps turnover cost, M0's
active total return was -0.1 percentage points in 2025 and -7.5 percentage
points in 2026. M3 was -3.9 and -6.0 percentage points respectively. The
signals therefore currently look more like time-varying market/style exposure
than demonstrated standalone Alpha.

The benchmark-relative HAC t-statistic for M0 active daily returns was -0.07 in
2025 and -2.03 in 2026; M3 was -0.69 and -1.59. M0's 2026 net maximum drawdown
was -27.6%. These diagnostics use 20 lags to account for serial dependence and
are descriptive evidence for the shadow only, not a formal promotion decision.

Treating 2026 as a frozen final-OOS period, the 20-day block bootstrap of net
active daily returns gave M0 a 95% mean interval of approximately
`[-0.129%, -0.011%]` and a probability of a positive mean of `0.7%`. M3's
corresponding interval was `[-0.112%, +0.002%]`, with positive-mean probability
`3.0%`. This is a negative final-OOS signal, not a basis for production use.

The source contract confirms `daily.amount` is thousand CNY. A first-pass
participation estimate puts M0's 1% participation capacity at roughly CNY 252
billion median and CNY 41 billion at the daily p10, but this is only an upper
bound based on selected-universe ADV. It does not yet model changed-name ADV,
single-name limits, market impact or capacity decay, and must not be used for
promotion.

### Final-OOS and regime decision

The fixed M0/M3 pair was also used in a 6-group, 2-test-group CPCV-style model
selection diagnostic. Across 15 paths, the model selected from the training
portion had positive test active return on only 40% of paths. M0 was selected
on 9 paths with a 55.6% positive-test rate; M3 was selected on 6 paths with a
16.7% positive-test rate. This is a stability warning, not a claim of formal
CPCV/PBO certification.

Conditioning the daily active returns on the reconstructed Shibor 5-observation
regime did not rescue the signal. M0's average active return was approximately
`+0.0077%` per day in down-regime, `-0.0222%` in flat-regime and `-0.0111%` in
up-regime; M3 was approximately `-0.0028%`, `-0.0230%` and `+0.0007%`.
Because these results use reconstructed context history and the frozen 2026
final-OOS test already fails, no Shibor gate is promoted to C3/C4 or production.
