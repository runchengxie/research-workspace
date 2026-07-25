# AFML 方法落地与跨仓库版本组合

本页记录 AFML 方法组件在工作区中的 owner、交接产物和集成顺序。顶层仓库只锁定子模块版本、验证文件契约并运行轻量 smoke，不导入子模块内部 Python 实现。

## 仓库分工

| 仓库 | 本次能力 |
| --- | --- |
| `market-data-platform` | 分笔 K 线柱（tick bar）、成交量 K 线柱（volume bar）、金额 K 线柱（dollar bar），Parkinson、Corwin-Schultz、Amihud 等可由真实输入支持的研究特征 |
| `alpha-research` | 三重屏障（triple barrier）、元标签（meta-label）、事件窗口（event window）、唯一性加权（uniqueness weighting）、序贯自助法（sequential bootstrap）、样本外（OOS）概率校准、fracdiff、structural breaks |
| `portfolio-backtester` | calibrated sizing、active-bet averaging、discretization、分层风险平价（HRP）、概率夏普比（PSR）、return concentration、strategy failure probability、implementation shortfall |
| `strategy-pipeline` | exploratory/candidate/release 研究协议与机器可读 evidence report |
| `quant-execution-engine` | dynamic target/limit policy、participation cap、交接 hash audit。不读取研究指标改变订单 |
| `research-workspace` | 子模块安全哈希算法（SHA）、产物（artifact）契约、版本组合和跨仓库 smoke |

## 新增正式产物

- `label_events.parquet`
- `sample_weights.parquet`
- `sample_weights.receipt.json`
- `research_features.parquet`
- `sizing_receipt.json`
- `strategy_risk_report.json`
- `hrp_receipt.json`
- `research_protocol_report.json`
- `execution_policy_receipt.json`
- `handoff_audit_report.json`

完整字段和 owner 见 `docs/artifact-contracts.yml`。

## 交接顺序

```text
market-data-platform
  research_features.parquet
        ↓
alpha-research
  label_events.parquet
  sample_weights.parquet
  signals.parquet
        ↓
portfolio-backtester
  positions_by_rebalance.csv
  sizing_receipt.json
  strategy_risk_report.json
  hrp_receipt.json
        ↓
strategy-pipeline
  research_protocol_report.json
  targets.json + 目标血缘（lineage）
        ↓
quant-execution-engine
  handoff_audit_report.json
  execution_policy_receipt.json
  dry-run / paper / controlled live
```

## 研究和执行边界

- 一个 canonical event table 同时定义标签、数据剔除（purging）、隔离窗口（embargo）和重叠（overlap）。
- candidate/release 协议禁止事件窗口数据剔除（event-window purge）静默退回普通 gap。
- sizing 使用严格样本外校准结果。组合层拥有权重约束和换手限制。
- release protocol 决定是否允许研究候选交接，不参与目标权重计算。
- 交接审计（audit）验证 schema、路径和哈希（hash），不根据夏普比率（Sharpe）、信息系数（IC）、修正夏普比（DSR）或 回测过拟合概率（PBO） 修改订单。
- 动态执行策略必须显式启用，并先经过 dry-run 和 paper 证据。

## 合并顺序

建议先合并 owner 仓库，再合并工作区 Git 子模块指针（gitlink）：

1. `market-data-platform`
2. `alpha-research`
3. `portfolio-backtester`
4. `strategy-pipeline`
5. `quant-execution-engine`
6. `research-workspace`

工作区 拉取请求（PR） 在 owner PR 未合并前会指向其分支提交，因此审查和 smoke 可以使用准确版本组合。owner PR 如发生 rebase 或 squash，合并工作区前需要刷新对应子模块指针。
