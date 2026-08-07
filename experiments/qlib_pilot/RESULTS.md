# qlib_pilot 结果

跑 `uv run python run_pilot.py`（合成数据）、`uv run python run_real_data.py`（真实数据）和
`uv run python compare_qlib_vs_own.py`（公平对比）后填写。最近一次：2026-08-07。

## 公平对比结果（compare_qlib_vs_own.py）

同一面板（188 只股票，2023-2024）、同一模型参数（自研 xgb_regressor 默认 300/3/0.05）、
同一 IC 口径（每日横截面 Spearman IC 均值，125 个验证交易日）。

| arm | mean_ic | mean_rank_ic |
|-----|---------|--------------|
| 自研 XGB（原始特征直接训练） | 0.0299 | 0.0299 |
| 自研 XGB（+ 复刻 qlib 标准化预处理） | 0.0510 | 0.0510 |
| qlib XGB（完整管线） | **0.0830** | **0.0830** |

### 解读

1. 标准化预处理贡献约 0.021 提升（0.030 -> 0.051），预处理确实重要。
2. 自研做同款标准化后，qlib 仍高约 0.032（0.051 -> 0.083）。差异来自 qlib 管线细节：
   label 的 CSZScoreNorm、样本权重、MAD 精确实现、DropnaLabel 时机等。
3. 注意：此对比用最朴素 XGBRegressor 代表自研，不代表自研生产 train_eval 的完整
   walk-forward + 样本权重 + 后处理链路的真实水平。若要最终定论，需对比 qlib 与
   自研生产链路（run_train_eval_stage）在完全相同输入下的 IC。

### 对决策的意义

- qlib 的价值不是"封装训练"，而是其完整预处理管线带来的可量化 IC 提升。
- 若自研生产链路未包含同等级的标准化/加权处理，qlib 值得认真评估引入；
  若已包含，则 qlib 的增量有限，需对比生产链路才能定论。

## 真实数据结果（run_real_data.py）

数据源：`~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/`
（5796 只 A 股日线，2015-2026，45 列）

时间窗 2023-01-01 至 2024-12-31，抽样 200 只股票。因子：pct_chg / turnover_rate / pe_ttm / pb / vol / amount。标签：未来 5 日收益。

| 指标 | 值 |
|------|-----|
| IC（验证集） | 0.1309 |
| Rank IC（验证集） | 0.0808 |
| 验证样本数 | 22,104 |
| 真实面板加载 | 2.9s |
| dump_bin 数据接入（200 只） | 3.8s |
| XGBModel 训练 + 评估 | 14.0s |
| 总计 | 20.7s |

### 可信度判断

- IC 0.13 处于横截面收益预测的合理水平，非噪音，说明真实数据链路工作正常。
- pe_ttm 约 13.5% 缺失率被 qlib 的 Fillna/RobustZScoreNorm 正常处理，无报错。
- 数据接入 200 只约 4s，线性外推 5796 只约 2 分钟，成本可接受。
- 尚未与自研 alpha-research 的 train_eval 结果做同一数据同一口径的对比。

## 合成数据结果（run_pilot.py）

20 只股票 × 400 交易日（6 合成特征 + 1 标签）。

| 阶段 | 耗时 |
|------|------|
| 样例数据构建 | 0.0s |
| panel -> csv -> qlib bucket（官方 dump_bin） | 1.7s |
| qlib train + eval（XGBModel + SigAnaRecord） | 22.1s |
| 总计 | 23.8s |

## 接入要点记录（真实成本）

1. **qlib 无 PyPI 正式版**，需从 GitHub 安装：`git+https://github.com/microsoft/qlib.git@main`（包名 pyqlib）。
2. **数据格式是 `.bin`**（`features/<inst>/<field>.day.bin`），内容为 `[start_index, 值...]` float32。
   手写 bin 容易错，正确路径是官方 `scripts/dump_bin.py`（已下载为 `tools_dump_bin.py`）。
3. **instrument 目录全部小写**（`code_to_fname`），大写在读取时会找不到文件。
4. 新版 `DataHandlerLP` 不再接收 `conf`，用位置参数 + `data_loader` dict。
5. `RobustZScoreNorm` 等 processor 的 `fit_start_time/fit_end_time` 需放进 **processor 自己的 kwargs**，不能放 handler 顶层。
6. `QlibDataLoader` 的 config 用 **dict 分组形式**：`{"feature": (feats, feats), "label": (["$LABEL"], ["LABEL"])}`。
7. XGBModel 模块路径是 `qlib.contrib.model.xgboost`（不是 `.xgb`）。
8. MLflow 新版本文件后端需要 `MLFLOW_ALLOW_FILE_STORE=true`。
9. `XGBModel.fit` 需要 dataset 里同时有 **train 和 valid** 两个 segment。
10. 真实数据 trade_date 是 'YYYYMMDD' 字符串，需转 datetime；label 需基于 adj_close 计算未来收益。

## 结论

- [x] 数据接入成本可接受（200 只约 4s，全量约 2 分钟）
- [x] XGBModel 训练/评估能跑通，真实数据 IC 0.13 可信
- [ ] 值得继续评估 qlib 引入（写 ADR）
- [ ] 不值得，自研继续（原因：_____）

## 备注

- 下一步可选：用同一数据同一口径对比自研 train_eval 的 IC，量化替代收益。
- 抽样 200 只；全量 5796 只需确认 dump_bin 内存/时间是否线性可控。
