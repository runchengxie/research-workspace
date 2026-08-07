# ADR-0005：Qlib 预处理管线引入 alpha-research 训练后端

- 状态：accepted
- 日期：2026-08-07
- 决策范围：`alpha-research` 的 backends 适配层
- 关联：ADR-0001（Qlib 集成边界）、[`framework-support-matrix.md`](../framework-support-matrix.md)

## 背景

`experiments/qlib_pilot` 用真实 A 股日线（188 只股票，2023-2024，200 只抽样窗口内）完成
qlib 与自研训练路径的对打。同一面板、同一模型参数、同一 IC 口径下：

| arm | mean_ic |
| --- | --- |
| 自研 train_eval（原始特征） | 0.0353 |
| 自研 train_eval（+ 复刻 qlib 横截面标准化） | 0.0512 |
| qlib 完整管线（RobustZScoreNorm + Fillna + CSZScoreNorm + XGBModel） | 0.0830 |

结论：qlib 的 IC 优势主要来自完整预处理管线，而非模型训练本身。横截面标准化贡献约
0.016，qlib 管线其余细节（label 标准化、DropnaLabel 时机、精确 MAD 截断）再贡献约 0.032。

ADR-0001 已定义 Qlib 为可选研究后端，且 `alpha-research.backends` 保留了
`DatasetBackend` / `TrainerBackend` 协议和 native 实现。本决策推进该边界内的具体实现。

## 决策

1. `alpha-research` 新增 `backends/qlib.py`，提供 `QlibTrainerBackend` 和 `QlibDatasetBackend`，
   实现既有 `TrainerBackend` / `DatasetBackend` 协议。
2. `QlibDatasetBackend` 复用 qlib 的 DataHandlerLP 预处理管线（横截面标准化、缺失填充、
   标签标准化），这是对打中 IC 优势的来源。
3. `QlibTrainerBackend` 使用 `qlib.contrib.model.xgboost.XGBModel` 训练与预测，与自研
   `xgb_regressor` 同一模型族。
4. qlib 通过 pyproject 的 `qlib` extra 安装（可选依赖）。未安装 qlib 时：
   - `backends/qlib.py` 可导入（qlib 延迟加载）
   - native 路径可导入、可测试、可运行
5. qlib 对象不得写入跨仓库 artifact（signals / positions / targets），遵守 ADR-0001。
6. 首期仅验证训练与预处理管线，不接 qlib 的 Recorder / 实验管理。实验记录仍走
   `ExperimentRecorder` 原生路径。

## 不做的事

- 不整体迁移到 qlib，不把数据资产权威、PIT 治理或晋升边界绑定到 qlib 对象。
- 不引入 qlib 作为顶层 superproject 依赖。只有需要时在 alpha-research 内安装。
- native 路径在 parity evidence 被接受前保持默认，不替换。

## 验收标准

- `backends/qlib.py` 在未安装 pyqlib 时 import 不报错，适配器构造或调用时给出清晰提示。
- 安装 `qlib` extra 后，`QlibTrainerBackend.fit` 能训练并在 `predict` 上返回结果。
- 新增测试覆盖：未安装 qlib 的导入/跳过路径、安装后的确定性训练与预测。
- `framework-support-matrix.md` 中 alpha-research 的 Qlib 状态更新为"已实现，条件化验证"。

## 后果

- alpha-research 代码量小幅上升，但通用预处理逻辑保留在适配器边界内。
- 后续若要提升 qlib 到默认后端，需要确定性数据集等价、PIT 和泄漏边界、训练预测、
  实验记录、产物序列化测试，并单独提交 ADR。
- 外部框架升级只影响适配器，跨仓库产物和职责仓接口保持兼容。
