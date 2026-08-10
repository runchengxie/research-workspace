# 策略证据门禁

> status: active
> owner: workspace
> last_verified: 2026-08-11
> source_of_truth: yes
> superseded_by: n/a

本页说明策略生命周期对应的强制证据要求，以及如何用证据包校验策略是否达到当前或目标阶段的门槛。

## 为什么需要证据门禁

金融研究容易把单个漂亮的回测数字当成结论，例如只看一个 Sharpe。单独一个结果无法回答这些问题：

- 换股票池、换预测周期、换市场状态还有效吗
- 扣除交易成本以后还剩多少
- 是否只用了当时已公开的数据
- 是不是多次试验以后挑出来的最好结果
- 熊市和震荡市的表现如何
- 组合规模扩大以后还能不能维持

证据门禁把这些问题变成策略生命周期每个阶段必须检查的清单。清单由
[evidence_policy.json](../strategy-research/evidence_policy.json) 定义，机器可读，
由 [strategy_evidence_gate.py](../scripts/strategy_evidence_gate.py) 执行校验。

## 生命周期与必检证据

| 生命周期 | 必检证据 |
| --- | --- |
| `exploration` | 无，快速试错 |
| `pre_production` | 时间点数据、滚动样本外、统一考试表、交易成本 |
| `shadow` | 上一档全部，另加最终样本外、组合对称交叉验证、市场状态 |
| `research_shadow` | 与 `shadow` 相同 |
| `operational_research` | 与 `shadow` 相同 |
| `operational` | 上一档全部，另加回测过拟合概率、多重检验调整、容量、阴性对照、实盘偏差 |
| `external_research` | 无，主要实现在外部仓库 |

`operational` 是要求最严的阶段。`pre_production` 到 `operational` 的要求逐级累加，
不允许跳级减项。

## 统一考试表

`benchmark_matrix` 是本门禁特有的检查，对应论文 FinBENCH 的"统一考试"思路。
它要求同一模型在多个股票池、预测周期、市场状态和成本假设下报告一组成绩，
并至少覆盖其中两个维度。单个股票池加单个周期的单个 Sharpe 不能通过该检查。

成绩单元格建议包含以下字段：

| 字段 | 含义 |
| --- | --- |
| `universe` | 股票池 |
| `horizon` | 预测周期 |
| `regime` | 市场状态 |
| `cost_bps` | 交易成本 |
| `sharpe` 或 `metric` | 成绩 |

## 证据包格式

每个策略的证据放在 `strategy-research/evidence/<策略id>.json`，格式如下：

```json
{
  "schema_version": "strategy_evidence_bundle.v1",
  "strategy_id": "daily_watch20",
  "as_of": "2026-08-11",
  "checks": {
    "pit": {
      "outcome": "pass",
      "evidence": "docs/evidence/pit.json",
      "pit_universe": true
    },
    "benchmark_matrix": {
      "outcome": "pass",
      "evidence": "docs/evidence/benchmark_matrix.json",
      "cells": [
        {"universe": "csi300", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 0.7},
        {"universe": "csi500", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 1.1},
        {"universe": "csi500", "horizon": "h20", "regime": "bear", "cost_bps": 50, "sharpe": -0.2}
      ]
    }
  }
}
```

每条检查至少包含 `outcome` 和 `evidence`。`outcome` 为 `pass` 且 `evidence`
为可追溯的路径时才算通过。`benchmark_matrix` 额外要求 `cells` 覆盖至少两个维度。

## 使用命令

查看全部策略的当前证据状态：

```bash
python scripts/strategy_evidence_gate.py
```

以失败即退出码 1 的方式检查全部策略：

```bash
python scripts/strategy_evidence_gate.py --strict
```

升格门禁，检查某个策略是否满足目标生命周期的要求：

```bash
python scripts/strategy_evidence_gate.py --strategy daily_watch20 --require operational
```

机器可读输出：

```bash
python scripts/strategy_evidence_gate.py --json
```

## 接入范围

当前证据门禁作为策略评审与升格时的显式命令运行，尚未接入 pre-push 自动门禁。
补齐证据包以后，再按路线图把 `--strict` 接入发布检查，避免在证据缺失阶段阻断日常推送。

## 与已有治理的关系

- 策略身份、生命周期与评审结论以 [catalog.json](../strategy-research/catalog.json) 为准
- 升格门槛和自包含约定见 [strategy-research/README.md](../strategy-research/README.md)
- 长期窗口证据计划见 [a-share-long-window-evidence-plan-20260601.json](evidence/a-share-long-window-evidence-plan-20260601.json)
