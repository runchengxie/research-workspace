# qlib 极速验证

评估 qlib 训练/评估层对当前自研 alpha-research 管线的替代性价比。
**不**评估整体引入，只测一件核心事实：用自己的 A 股数据跑通 qlib 的 XGBModel 要多久。

## 背景与结论

自研 workspace 约 340K 行 Python。qlib 舒适区（训练/评估/特征/CPCV/集成）在
alpha-research 里约 4.6K 行，占总量 ~1.4%，且其中不少是 A 股 PIT 特化逻辑。

因此本实验的目标不是"替换 train_eval"，而是回答：

> 如果未来 ML 研究量扩大，用 qlib 的模型库/特征库省下的新代码，是否值得付数据接入成本？

## 验证方法

用 qlib 官方 pipeline（`qrun` 或 Python API）复跑一个已知结论的实验：

1. 把自己的数据整理成 qlib 的 bucket 格式（`features` + `calendars` + `instruments`）
2. 用 `XGBModel`（`qlib.contrib.model.xgb`）训练
3. 用 qlib 的 `SignalRecord` / `PortAnaRecord` 出评估
4. 记录关键耗时

## 判断标准

| 指标 | 结论 |
|------|------|
| 数据接入（csv -> qlib bucket）耗时 | 超过 1 天 = 不划算 |
| 首次跑通 XGBModel 耗时 | 作为参考 |
| 与自研链路结果一致性 | 用于校准可信度 |

## 结论占位（跑完填）

_待补充_

## 运行方式

```bash
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
uv run python run_pilot.py
```
