# A 股微盘稳健性研究协议

本实验检验现有 A 股风格因子、小盘候选和低换手候选对最小市值股票的依赖程度。它属于研究诊断，不登记生产策略，不修改 `targets.json`，也不授权任何策略晋级。

## 冻结问题

第一轮只回答以下问题：

1. 删除形成日最小市值 10%、20%、30% 股票后，现有因子和 long-only 候选剩余多少历史收益。
2. 同一股票池下，等权和形成日总市值权重的差异有多大。
3. buffer、交易成本和受限容量如何改变 small-cap 与 small-cap + low-turnover 结果。
4. 2019 年和 2023 年注册制相关阶段前后是否存在结构性差异。

第 4 项只报告关联和阶段差异。阶段切片不能识别注册制的因果效应。

## 形成日 reference universe

所有 factor 和 candidate 共用同一 reference universe，顺序固定为：

```text
PIT A 股形成日 universe
→ minimum listed days
→ formation-day amount > 0
→ non-ST
→ finite positive total_mv
```

微盘 cutoff 不能按某个 factor 的缺失样本单独计算。

每个形成日按

```text
total_mv ascending
symbol ascending
```

稳定排序。

对于 exclusion `p`：

```text
excluded_count = floor(N * p)
```

第一轮固定：

```text
0.00
0.10
0.20
0.30
```

市值相同由证券代码稳定打破平局。

## 因子重算

每个 exclusion variant 都通过

```python
compute_factors(..., formation_universe=variant_keys)
```

独立重算。

历史 momentum、volatility 和 beta 仍使用完整历史市场输入。quality 子指标、形成日辅助因子、PIT 行业去均值和最终 z-score 使用过滤后的形成日股票池。

禁止从 full-universe `<factor>_z` 简单删除行后称作微盘稳健性。

## 小盘与低换手候选

候选信号使用过滤后的形成日股票池重新计算 size 和 low-vol controls，再构造：

```text
small_cap
low_turnover
low_turnover_residual
composite = small_cap + low_turnover
large_cap_control
```

low-turnover 主口径沿用 prior 60 session mean，形成日观测不进入窗口。

## EW / VW

第一轮固定比较：

```text
equal
value
```

`value` 使用形成日 `total_mv`。权重只影响已选证券的目标权重，不能改变 candidate ranking、selected symbols 或 buffer 决策。

因子组合使用 `portfolio-backtester` 的 quantile weighting API。形成日完成初始权重以后保持固定份额，持有期内自然漂移。

## Buffer

long-only 路径固定比较：

```text
no_buffer: buffer_count == target_count
buffered: target_count=40, buffer_count=60
```

两种 weighting mode 复用完全相同的 selected symbol sets。

## 成本与容量

主 long-only matrix 使用现有 weight-level execution engine，并报告交易成本后的结果。

完整 cash-ledger capacity ladder 只跑：

```text
candidate = small_cap, composite
exclusion = 0%, 30%
weighting = equal, value
buffer = buffered
capital = 10m, 100m, 500m CNY
```

执行约束复用现有：

```text
5% prior-amount participation
100-share lot
T+1
3-day buy window
5-day sell window
涨跌停 / 停牌约束
```

## 样本边界

参数和矩阵冻结为：

```text
development: 2015-01-01 ~ 2023-12-31
final holdout: 2024-01-01 ~ 2026-07-31
```

查看 final holdout 后不能修改 exclusion grid、weighting mode、buffer、候选定义或主 turnover 窗口，再把相同 2024+ 数据称为 untouched holdout。

## 注册制相关阶段

固定报告切片：

```text
pre_registration_pilot: date < 2019-07-22
registration_pilot: 2019-07-22 <= date < 2023-02-17
full_registration: date >= 2023-02-17
```

2019-07-22 用作科创板首批股票上市交易阶段边界。2023-02-17 用作全面实行股票发行注册制制度规则节点。

这些日期只负责描述时期。市场周期、流动性、指数结构、投资者参与和其他监管变化都可能共同影响结果，因此报告不得写成制度因果识别。

## 稳定产物

完整运行输出：

```text
microcap_universe_diagnostics.csv
microcap_factor_matrix.csv
microcap_weighting_matrix.csv
microcap_buffer_matrix.csv
microcap_capacity_matrix.csv
microcap_yearly.csv
microcap_regimes.csv
microcap_summary.json
```

大体量运行产物保存在仓库外。仓库只保存代码、协议、测试和后续经过复核的小型结论摘要。

## 运行入口

```bash
uv run --project strategy-research python \
  strategy-research/experiments/style_factors/microcap_robustness_20260829.py \
  --data-root "$DATA_PLATFORM_ROOT" \
  --outdir /path/to/microcap_artifacts
```

缓存目录通过 `--cache-dir` 指定。`--resume` 只有在数据范围、owner commit、上市时间门槛、exclusion grid 和 weighting modes 的 manifest 完全一致时才复用缓存。

## 研究边界

- bottom-30% 剔除后收益衰减只能证明结果依赖最小市值样本，不能直接证明壳价值机制。
- EW 与 VW 差异只能描述数量权重的影响，不能代替流动性和容量证据。
- long-short 风格因子用于定价和暴露研究。实际候选策略仍按 long-only 执行证据解释。
- 本实验状态在有仓库内可追溯证据以前保持 `in_progress`。
