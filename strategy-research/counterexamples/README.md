# 反例驱动稳健性记录

本目录保存 `counterexample.v1` 记录。它们把“在哪些压力条件下某个研究判断明显变弱或失效”
提升为机器可检查的一等对象，并引用已有证据产物。这里不实现回测、优化器或压力计算。
计算仍由 `alpha-research`、`portfolio-backtester`、`strategy-app` 等职责仓完成。

## 工作流

```text
claim
  ↓
正常 OOS / CPCV / 成本 / 容量证据
  ↓
寻找最能伤害该判断的时间窗、市场状态或参数扰动
  ↓
counterexample.v1
  ↓
case.counterexamples
  ↓
逻辑 / 证据评审
  ↓
维持、降级、拒绝或补充研究判断
```

反例不是自动否决。它记录压力条件、基准与压力后的同口径指标、失效条件和证据引用，
由研究案例结合 claim 的 `critical_assumptions`、`invalidation_conditions` 与其他证据判断影响。

## 支持的 scenario_type

- `time_window`：最差年份、滚动窗口、特定样本外路径
- `market_regime`：高低波动、趋势、宽度、利率等市场状态
- `cost`：手续费、滑点、冲击成本压力
- `liquidity`：成交额、可交易性、停牌或涨跌停语义
- `capacity`：participation cap、容量上限等
- `exposure`：行业、size、low-vol、风格暴露等去混淆或限制
- `signal_perturbation`：分数噪声、排名扰动、预测误差
- `correlation`：相关性上升或协方差结构变化
- `custom`：其他已预注册且可复现的压力情景

## 约束

- `claim_id` 必须指向现有 `judgment-ledger/<claim_id>.json`。
- `baseline_metrics` 与 `stressed_metrics` 必须使用相同 metric 名称，禁止跨口径比较。
- metric value 必须是有限数值。
- `stress_dimensions`、`failure_conditions` 和 `evidence_refs` 必须非空。
- 不在本目录制造为了填 schema 而生成的合成研究证据。
- `resolved` 只表示该反例已被重新设计、额外证据或策略边界处理，不代表删除历史记录。

校验入口：

```bash
python scripts/decision_governance_check.py
python scripts/decision_governance_check.py \
  --counterexample strategy-research/counterexamples/<id>.json
```

schema 位于 `strategy-research/schemas/counterexample.v1.schema.json`。
