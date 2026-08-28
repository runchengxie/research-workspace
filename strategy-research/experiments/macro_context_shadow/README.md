# Macro Context Shadow

`macro_context_shadow_v1` 验证宏观、产业和公司暴露是否为 A 股横截面预测带来稳定增量。实验处于 `exploration`，禁止生产发布。

实验固定比较 C0 至 C4 五组特征，并使用 5、20、60 个交易日标签，其中 20 日是唯一主选择周期。C4 增加披露后可用的公募基金拥挤度与增持特征。宏观序列必须来自 `cn_context` current contract，股票数据来自 `a_share` current contract。实验只组合 `market-data-platform`、`alpha-research` 和 `portfolio-backtester` 的公开 API，不在此目录复制通用实现。

## Fund context C4

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
