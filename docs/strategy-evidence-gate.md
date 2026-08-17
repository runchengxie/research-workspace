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
`outcome` 还可以是 `partial`、`pending`、`substitute` 或 `missing`，这些都不算通过，
必须进入证据包的顶层 `known_gaps` 列表登记，否则严格门禁会判定为未登记缺口并阻断。

## 已知缺口登记与严格门禁

证据包顶层 `known_gaps` 是一个字符串数组，每条以 `"<检查键>:"` 开头（例如
`"cost: 长窗口成本压力证据 pending"`）。门禁在 `--strict` 模式下的判定规则：

- 未登记缺口（unregistered_gaps）：缺失且未出现在 `known_gaps` 的检查，无论策略是否生产级都使 `--strict` 退出码为 1，阻断推送。这防止缺口被静默漏记。
- 已知缺口豁免（known_gaps_waived）：缺失项全部出现在 `known_gaps` 中，且策略在 `catalog.json` 的 `production_eligible` 为 `false` 时，门禁不阻断（退出码 0），但在报告中标注「已知缺口豁免」。
- 生产策略：`production_eligible` 为 `true` 的策略必须关闭全部必需检查，任何缺失（无论是否登记）都保持硬失败。

每个策略的证据包放在 `strategy-research/evidence/<策略id>.json`。截至 2026-08-17，
已将五个策略的既有 A 股研究证据（`docs/evidence/a-share-*.json`、strategy-app 回执）
如实组装为证据包，并把 `daily_watch20` 从 `operational` 校正为 `research_shadow`
（`production_eligible` 改为 `false`），消除其证据门禁结果（`present: []`）与治理声明
（`operational + production_eligible`）之间的不一致。

## 使用命令

查看全部策略的当前证据状态：

```bash
python scripts/strategy_evidence_gate.py
```

以失败即退出码 1 的方式检查全部策略（仅阻断未登记缺口）：

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

证据门禁的 `--strict` 已接入 pre-push 自动门禁（`scripts/run_pre_push_checks.py` 的
`strategy-evidence-gate` 命令）。它只阻断未登记的缺口，因此日常推送不会被已知且
显式登记的缺口冻结。任何缺失检查若未写入 `known_gaps`，推送会被拦截。

## 与已有治理的关系

- 策略身份、生命周期与评审结论以 [catalog.json](../strategy-research/catalog.json) 为准
- 升格门槛和自包含约定见 [strategy-research/README.md](../strategy-research/README.md)
- 长期窗口证据计划见 [a-share-long-window-evidence-plan-20260601.json](evidence/a-share-long-window-evidence-plan-20260601.json)
