# 实验说明书（ResearchSpec）

> status: active
> owner: workspace
> last_verified: 2026-08-11
> source_of_truth: yes
> superseded_by: n/a

本页说明实验说明书的格式与校验方式。实验说明书解决一个问题：每个实验到底做了什么，
不用去翻散落在各处的结果文档和配置文件。

## 为什么需要实验说明书

量化研究的结论散落在实验结果、回测报告、配置和脚本里。只靠目录名或 README 很难回答：

- 用的什么股票池
- 预测几天后的什么目标
- 用什么模型、怎么训练
- 有没有构造组合、成本假设多少
- 样本外怎么测的，有没有预留最终样本外

实验说明书把这些问题固定成一个 `research_spec.json`，放在实验目录下，让"这次实验
到底做了什么"一眼能看懂，也能被脚本自动校验。

## 文件位置

每个实验在 `strategy-research/experiments/<实验id>/research_spec.json` 放一份说明书。
`experiment_id` 必须与目录名一致。当前已登记的示例见
[qlib_pilot](../strategy-research/experiments/qlib_pilot/research_spec.json)。

## 格式

schema 版本为 `research_spec.v1`，各字段如下：

| 字段 | 内容 |
| --- | --- |
| `schema_version` | 固定 `research_spec.v1` |
| `experiment_id` | 与目录名一致 |
| `title` | 一句话说明 |
| `market` | 市场，例如 `a_share` |
| `status` | `proposed`、`in_progress`、`complete`、`archived` 之一 |
| `universe` | 股票池描述与 membership，`pit` 是否时间点口径 |
| `data` | 数据来源、起止、是否 PIT 财务 |
| `prediction` | 预测目标、horizon（如 `h5`、`h5_h20`）、任务类型 |
| `model` | 模型名称与训练方式 |
| `portfolio` | 组合构造，`top_k`、`long_short`、`long_only`、`pairwise` 或不适用 |
| `cost` | 成本假设（基点列表）或不适用 |
| `benchmark` | 基准组列表或不适用 |
| `evaluation` | 样本外协议列表、是否预留最终样本外 |
| `evidence_refs` | 结果与结论的可追溯文件路径 |

不适用的字段显式写 `n/a`，不省略。`complete` 或 `archived` 的说明书必须给出非空的
`evidence_refs`，且引用的文件必须存在。

## 校验命令

扫描并校验全部实验说明书：

```bash
python scripts/research_spec_check.py
```

校验单个说明书：

```bash
python scripts/research_spec_check.py --spec strategy-research/experiments/qlib_pilot/research_spec.json
```

机器可读输出：

```bash
python scripts/research_spec_check.py --json
```

任一份说明书无效或引用缺失文件时，命令以退出码 1 结束。

## 与证据门禁的关系

- 实验说明书负责描述实验做了什么，见本页
- 策略证据门禁负责审查策略该信什么，见 [strategy-evidence-gate.md](strategy-evidence-gate.md)
- 两者共用 universe、horizon、cost、oos 等词汇，便于把说明书对应到门禁检查项

实验仍是快速试错的地方，写说明书不改变实验目录的规则，只要求结论能追溯。
