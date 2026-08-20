# qlib 极速验证

评估 qlib 训练/评估层对自研 alpha-research 管线的替代性价比。**不**评估整体引入，
只测核心事实：用自己的 A 股数据跑通 qlib 的 XGBModel 要多久。

## 背景与结论

自研 workspace 约 340K 行 Python。qlib 舒适区（训练/评估/特征/CPCV/集成）在
alpha-research 约 4.6K 行（占 ~1.4%），且不少是 A 股 PIT 特化逻辑。目标不是替换
train_eval，而是回答：未来 ML 研究量扩大时，用 qlib 模型库/特征库省下的新代码，
是否值得付数据接入成本。**最终结论：不引入 qlib**（详见 RESULTS.md）。

## 验证方法

用 qlib 官方 pipeline（`qrun` 或 Python API）复跑已知结论实验：整理数据为 qlib
bucket 格式 → 用 XGBModel 训练 → 用 SignalRecord/PortAnaRecord 评估 → 记录耗时。

## 判断标准

| 指标 | 结论 |
| --- | --- |
| 数据接入耗时 | 超过 1 天 = 不划算 |
| 首次跑通 XGBModel 耗时 | 参考 |
| 与自研结果一致性 | 校准可信度 |

## 运行方式

```bash
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
uv run python run_pilot.py          # 合成数据流程验证
uv run python run_real_data.py      # 真实 A 股数据验证
```

真实数据默认读 `~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data`，
可用 `A_SHARE_DAILY_DIR` 覆盖；`LIMIT_SYMBOLS` 控制抽样规模（默认 200）。完整逐实验
结果见 RESULTS.md。
