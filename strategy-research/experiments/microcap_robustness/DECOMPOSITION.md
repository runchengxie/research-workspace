# 微盘特征机制分解

本页是 `microcap_robustness` 的第二阶段协议。第一阶段先检验结果是否依赖最小市值股票；第二阶段再把 size 暴露与流动性、彩票型收益、特质波动、换手和质量拆开比较。

这套分析描述条件预测关系。回归系数、double-sort 或制度阶段差异都不能直接解释为结构性因果。

## 冻结形成日特征

### Size

```text
log_market_cap = log(total_mv)
```

只使用形成日有限正市值。

### Amihud illiquidity

```text
window = prior 60 market sessions
minimum observations = 45
formation session excluded
amount_cny = amount * 1000
ILLIQ = mean(abs(return) / amount_cny)
```

非正成交额视为缺失，不生成无穷值。

### MAX

```text
window = prior 21 market sessions
minimum observations = 15
formation session excluded
MAX = maximum daily return
```

### IVOL

```text
window = prior 60 market sessions
minimum observations = 40
formation session excluded
stock_return = intercept + beta * broad_market_return + residual
IVOL = residual standard deviation
```

所有 exclusion variant 使用同一个全市场 clean-return proxy，不因微盘剔除重新定义市场基准。

### Turnover

沿用第一阶段定义：

```text
prior 60 market sessions mean
minimum observations = 45
formation session excluded
```

### Quality

每个 exclusion variant 通过 `compute_factors(..., formation_universe=...)` 独立重算 `factor_quality`。历史财务数据存在重建区间，因此 `research_spec.json` 不把整段历史声明为原始 vintage-safe PIT。

## Double sort

固定运行：

```text
Size × ILLIQ
Size × MAX
Size × IVOL
Size × Turnover
Size × Quality
```

通用 double-sort 使用值升序、证券代码升序稳定打破平局。旧 `build_size_turnover_double_sort` 保持兼容 wrapper。

forward return 从形成日之后开始，到下一形成日结束：

```text
formation date excluded
next formation date included
```

## 截面回归

每个形成日独立运行：

```text
forward_return
~ intercept
+ z_log_market_cap
+ z_illiquidity_60d
+ z_max_return_21d
+ z_ivol_60d
+ z_turnover_lagged_mean_60d
+ z_factor_quality
```

每个解释变量先在当日按 1% / 99% 缩尾，再做截面 z-score。主规格使用 complete-case 样本，输入数、有效数和丢弃数必须写入 diagnostics。

## 系数时间序列

月度主规格对每个 date-level coefficient 做 intercept-only 时间序列回归，并使用 statsmodels HAC / Newey-West covariance：

```text
maxlags = 3
```

报告：

```text
coefficient mean
HAC standard error
t-stat
formation count
positive share
coefficient standard deviation
median cross-sectional R²
```

如果以后增加 weekly 或 biweekly sensitivity，HAC lag 必须显式改成对应配置，不能无说明沿用月度 `3`。

## 样本边界

```text
development: 2015-01-01 ~ 2023-12-31
final holdout: 2024-01-01 ~ sealed data end
```

形成日窗口、特征定义、回归规格和 HAC lag 在查看 final holdout 结果前冻结。

## 稳定产物

```text
microcap_characteristics.csv
microcap_double_sorts.csv
microcap_cross_sectional_coefficients.csv
microcap_coefficient_summary.csv
microcap_decomposition_summary.json
```

完整运行入口：

```bash
uv run --project strategy-research python \
  strategy-research/experiments/style_factors/microcap_characteristic_decomposition_20260829.py \
  --data-root "$DATA_PLATFORM_ROOT" \
  --outdir /path/to/microcap_decomposition
```

## 解释边界

- size coefficient 在控制变量后缩小，说明部分 size 预测关系与这些可观察特征重合。
- size coefficient 仍显著，也不能自动解释为 size 风险溢价。
- bottom-30%、ILLIQ、MAX 或 IVOL 都是经验特征，不等同于壳价值、散户偏好或套利约束的直接测量。
- 2024 年以后 final holdout 不能在看过结果后继续用来调窗口和规格。
