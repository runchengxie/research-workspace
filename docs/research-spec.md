# 实验说明书（ResearchSpec）

> status: active
> owner: workspace
> last_verified: 2026-08-31
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
- 多候选搜索实际试过多少 trial，统计分母在哪里

实验说明书把这些问题固定成一个 `research_spec.json`，放在实验目录下，让这次实验到底做了什么一眼能看懂，也能被脚本自动校验。多候选搜索的真实执行历史由 Trial Ledger 记录，ResearchSpec 只保存可选链接。

## 文件位置

每个实验在 `strategy-research/research/experiments/<实验id>/research_spec.json` 放一份说明书。
`experiment_id` 必须与目录名一致。当前已登记的示例见
[qlib_pilot](../strategy-research/research/experiments/qlib_pilot/research_spec.json)。

基本面族级 shadow 的当前实现入口见
[fundamental_family_shadow](../strategy-research/research/experiments/fundamental_family_shadow/README.md)。
它固定 Value、Quality、Growth 的族级对照、20 日主周期、60 日慢基本面挑战周期和 5 日诊断周期。
该实验仍处于研究中，历史回放标记为 `retrospective_diagnostic`，不改变生产 preset，也不允许自动晋级。

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
| `trial_ledger` | 可选，多候选搜索的 Trial Ledger 路径和多重检验 family |

不适用的字段显式写 `n/a`，不省略。`complete` 或 `archived` 的说明书必须给出非空的
`evidence_refs`，且引用的文件必须存在。

### 可选 Trial Ledger

自动候选搜索、参数网格、遗传搜索、Agent 批量生成或其他系统性多候选实验，建议增加：

```json
{
  "trial_ledger": {
    "path": "trial-ledger/<experiment_id>.jsonl",
    "multiple_testing_family": "factor-search-v1"
  }
}
```

`path` 相对 `strategy-research/` 解析。顶层 checker 只验证跨对象链接：

- 文件存在且不能逃逸 `strategy-research/`
- 每行 `experiment_id` 与 ResearchSpec 一致
- `multiple_testing_family` 至少存在一个 `counted=true` 的 trial

Trial 的 parent 图、exact duplicate fingerprint、排除理由和 final OOS 污染规则由
`strategy-research/tools/scripts/trial_ledger_check.py` 管理。顶层不复制 owner 的统计记账逻辑。

一开始就在 ResearchSpec 中预留 final OOS，不代表训练 trial 已经读取 final OOS。只有某个 trial 真正执行该窗口时，Trial Ledger 才记录 `role=final_oos`。

单次探索性诊断没有参与候选筛选或显著性判断时可以不声明 Trial Ledger。历史实验也不要求一次性回填。

## 校验命令

扫描并校验全部实验说明书：

```bash
python scripts/research_spec_check.py
```

校验单个说明书：

```bash
python scripts/research_spec_check.py --spec strategy-research/research/experiments/qlib_pilot/research_spec.json
```

机器可读输出：

```bash
python scripts/research_spec_check.py --json
```

任一份说明书无效、引用缺失文件或声明了无效 Trial Ledger 链接时，命令以退出码 1 结束。

## 与证据门禁的关系

- 实验说明书负责描述实验做了什么，见本页
- Trial Ledger 负责记录多候选搜索实际做过什么、哪些 trial 进入统计分母
- 策略证据门禁负责审查策略该信什么，见 [strategy-evidence-gate.md](strategy-evidence-gate.md)
- 三者共用 universe、horizon、cost、oos 等词汇，便于把实验、搜索历史和晋级证据对齐

实验仍是快速试错的地方，写说明书和 Trial Ledger 不改变实验目录的规则，只要求研究过程能够追溯。
