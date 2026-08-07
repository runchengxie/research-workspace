# qlib_pilot 结果

跑 `uv run python run_pilot.py` 后填写。最近一次：2026-08-07。

## 阶段耗时

| 阶段 | 耗时 |
|------|------|
| 样例数据构建 | 0.0s |
| panel -> csv -> qlib bucket（官方 dump_bin） | 1.7s |
| qlib train + eval（XGBModel + SigAnaRecord） | 22.1s |
| 总计 | 23.8s |

样例规模：20 只股票 × 400 交易日，6 特征 + 1 标签。

## 接入要点记录（真实成本）

1. **qlib 无 PyPI 正式版**，需从 GitHub 安装：`git+https://github.com/microsoft/qlib.git@main`。
2. **数据格式是 `.bin`**（`features/<inst>/<field>.day.bin`），内容为 `[start_index, 值...]` float32。
   手写 bin 容易错，正确路径是官方 `scripts/dump_bin.py`（已下载为 `tools_dump_bin.py`）。
3. **instrument 目录全部小写**（`code_to_fname`），大写在读取时会找不到文件。
4. 新版 `DataHandlerLP` 不再接收 `conf`，用位置参数 + `data_loader` dict。
5. `RobustZScoreNorm` 等 processor 的 `fit_start_time/fit_end_time` 需放进 **processor 自己的 kwargs**，不能放 handler 顶层。
6. `QlibDataLoader` 的 config 用 **dict 分组形式**：`{"feature": (feats, feats), "label": (["$LABEL"], ["LABEL"])}`。
7. XGBModel 模块路径是 `qlib.contrib.model.xgboost`（不是 `.xgb`）。
8. MLflow 新版本文件后端需要 `MLFLOW_ALLOW_FILE_STORE=true`。
9. `XGBModel.fit` 需要 dataset 里同时有 **train 和 valid** 两个 segment。

## 结论

- [x] 数据接入成本可接受（< 1 天能灌真实数据，样例仅 1.7s）
- [x] XGBModel 训练/评估能跑通（原生支持，用户熟悉的模型）
- [ ] 值得继续评估 qlib 引入（写 ADR）
- [ ] 不值得，自研继续（原因：_____）

## 备注

- 本实验只验证了训练/评估一段的可行性，未评估与自研 PIT 数据体系的完整迁移成本。
- 样例数据是合成数据，未验证与真实 A 股数据的结果一致性。
- 下一步可选：用真实数据 + 与自研 train_eval 结果对比，再决定是否写 ADR。
