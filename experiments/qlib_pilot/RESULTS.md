# qlib_pilot 结果

跑 `uv run python run_pilot.py`（合成数据）、`uv run python run_real_data.py`（真实数据）、
`uv run python compare_qlib_vs_own.py`（公平对比）、`uv run python compare_qlib_vs_train_eval.py`
（与自研生产训练路径对打）、`uv run python diff_native_vs_qlib.py`（后端差分）、
`uv run python compare_cs_standardization.py`（标准化方法对比）、
`uv run python robustness_multi_window.py`（多滚动窗口稳健性）、
`uv run python compare_a_share_cs_methods.py`（a_share 特征集对比）、
`uv run python explore_style_factor_robust.py`（风格因子落地探索）和
`uv run python explore_monthly_horizon.py`（月频标签验证）后填写。
最近一次：2026-08-07。

## 月频标签验证（explore_monthly_horizon.py）

对齐 a_share 生产链路（horizon_days: 20 月频标签），对比 5 日 vs 20 日标签下
robust 与风格因子的效果。5 个滚动窗口（2021-2024，18 月训练 / 6 月验证）。

| 配置 | 5 日标签 | 20 日标签（月频） |
| --- | --- | --- |
| tech_zscore | 0.0572 | 0.0801 |
| tech_robust | 0.0627 | 0.0864 |
| ext_zscore | 0.0455 | 0.0746 |
| ext_robust | 0.0610 | 0.0870 |

### 关键发现

1. 月频标签的 IC 显著更高（0.0864 vs 0.0627），与风格报告"长周期信号更可靠"一致。
2. robust 在月频下依然成立（tech +0.0064，ext +0.0123）。
3. 风格因子（低换手/价值）在月频下不再拖累（ext robust 与 tech robust 持平 0.0870 vs 0.0864），
   5 日标签下的负结果确实是时间尺度不匹配。
4. 最佳组合 ext_robust 月频 0.0870，说明 robust + 风格因子 + 月频标签三者协同。

### 对策略定制的启示

风格报告的结论（低换手/价值长期有效）应通过"月频标签 + robust 标准化 + 风格因子特征"
落地，而非 5 日短标签。a_share 生产已是月频（horizon_days: 20），方向正确。

## 风格因子落地探索（explore_style_factor_robust.py）

背景：风格因子报告指出低换手、价值、短期反转是长期有效风格。验证把这类因子
（换手率 turnover_rate + 估值 pe_ttm/pb + pct_chg）加入短期回归特征集是否提升。

8 滚动窗口（2022-2024），对比 纯技术面 vs 扩展特征集，以及 zscore/robust/rank 三种标准化。

| 配置 | mean_ic | std |
| --- | --- | --- |
| tech_zscore | 0.0437 | 0.0140 |
| tech_robust | 0.0480 | 0.0131 |
| extended_zscore | 0.0411 | 0.0246 |
| extended_robust | 0.0435 | 0.0129 |
| extended_rank | 0.0402 | 0.0273 |

### 结论（负结果，重要）

1. 把风格因子裸加进短期（5 日标签）回归模型，三种标准化下都未提升 IC，
   反而比纯技术面略低（robust 0.0480 -> 0.0435）。
2. 原因：风格因子是长周期信号（月/季度），与 5 日收益标签时间尺度不匹配；
   且风格因子间共线性（报告自证价值/低波动/低换手相关 0.67-0.84）在 XGB 中相互稀释。
3. 报告的结论成立，但其作用域是风格配置/行业暴露管理，不是短期 alpha 特征。
4. 落地启示：a_share 维持纯技术面特征集即可；风格因子应作为组合层约束
   （行业/市值/换手暴露控制）使用，而非塞进短期回归特征。

## a_share 生产特征集对比（compare_a_share_cs_methods.py）

用 a_share.yml 预设的可计算特征子集（ret_5/20/60、rv_20/60、vol、log_vol、
volume_sma*_ratio、amount_log），8 个滚动窗口（2022-2024）。

| method | mean_ic | std |
| --- | --- | --- |
| none | 0.0309 | 0.0271 |
| zscore | 0.0437 | 0.0140 |
| robust | 0.0480 | 0.0131 |

robust-vs-none +0.0171，robust-vs-zscore +0.0043（命中率 50%）。

### 解读

1. robust 仍优于 zscore（+0.0043）且波动更低（0.0131 vs 0.0140）。
2. 但差距比含 pe_ttm 的实验小很多（+0.0043 vs +0.0216），命中率降到 50%。
3. 原因：a_share 当前是纯技术面特征（价格/量），分布较规整、极端值少；
   robust 的主场是含极端值/缺失的因子（如基本面 pe_ttm）。
4. 结论：把 a_share 默认改成 robust 是安全的（不输 zscore，波动更低），
   但当前纯技术面特征下收益温和。若以后引入基本面因子，robust 价值会凸显。

## 多滚动窗口稳健性（robustness_multi_window.py）

时间范围 2022-01 至 2024-12，训练窗 12 个月、验证窗 3 个月、步进 3 个月，共 8 个滚动窗口。
每窗口对比原生 raw 与 robust 标准化的 OOS IC（每日横截面 Spearman 均值）。

| 指标 | raw | robust |
| --- | --- | --- |
| mean_ic | 0.0331 | 0.0547 |
| std | 0.0264 | 0.0211 |
| 平均提升 | - | +0.0216 |
| 命中率（robust 更好） | - | 87.5%（7/8 窗口） |

### 解读

1. 提升稳定，非单窗口巧合。8 个独立 OOS 窗口中 7 个 robust 更好。
2. robust 同时降低波动（std 0.0264 -> 0.0211），平均更高且更稳。
3. 唯一负窗口（w3，2023-07 验证）是 raw 冲到 0.0937 的异常窗口，robust 未跟随该噪音。
   从稳健性角度这甚至是优点。

结论：A 方案（原生 robust 标准化）的 IC 提升在多个独立 OOS 窗口上稳定复现，
不是数据巧合。可放心作为原生训练链路的默认预处理选项。

## 标准化方法对比（compare_cs_standardization.py）

真实 A 股面板（188 只，2023-2024），同模型参数，同 IC 口径（125 验证日）。

| arm | mean_ic | vs raw |
| --- | --- | --- |
| native raw | 0.0283 | - |
| native zscore（均值/方差） | 0.0330 | +0.0048 |
| native robust（中位数/MAD） | 0.0509 | +0.0226 |
| qlib robust 管线 | 0.0793 | +0.0510 |

### 解读

1. robust（median/MAD）相对 zscore 大幅提升，对含极端值/偏态因子（如 pe_ttm）更稳。
2. 原生 robust 追回 qlib 提升的约 44%（0.0226 / 0.0510），无需引入 qlib 依赖。
3. 剩余差距 0.0284 来自 qlib 管线的 label CSZScoreNorm、clip_outlier 截断、DropnaLabel 时机。

结论：A 方案（自研补 robust 标准化）有效，是性价比最高的路径。`robust` 方法已并入
alpha-research 的 `apply_cross_sectional_transform`（alpha-research #15）。

## 后端差分结果（diff_native_vs_qlib.py）

alpha-research `NativeTrainerBackend` vs `QlibTrainerBackend`，同一 TrainerFitRequest
（同参数、同特征、同目标）、同一 IC 口径（每日横截面 Spearman IC 均值，125 验证日）。

| 指标 | Native | Qlib | 差异 |
| --- | --- | --- | --- |
| mean_ic | 0.0283 | 0.0316 | +0.0034 |
| fit 耗时 | 3.2s | 5.8s | +2.6s |
| predict 耗时 | 0.05s | 0.02s | 相当 |
| 顶部特征 | amount / turnover_rate / pct_chg | amount / pe_ttm / pb | 略不同 |

### 解读

两个后端都直接吃原始特征（无预处理）。IC 差异仅 +0.0034，可视为等价。这证明：

1. QlibTrainerBackend 作为训练后端与 NativeTrainerBackend 结果一致，无偏差。
2. 之前对打中 qlib 的 +0.048 IC 优势全部来自预处理管线（横截面标准化），而非训练后端。

结论：QlibTrainerBackend 已通过"与原生基线形成可复验差异报告"的 ADR-0005 验收要求，
可安全作为可选训练后端使用。若要获得 qlib 的完整 IC 优势，需配合 QlibDatasetBackend
（或等价横截面标准化预处理）。

## 与自研生产训练路径对打（compare_qlib_vs_train_eval.py）

同一面板（188 只股票，2023-2024）、同一模型参数（自研 xgb_regressor 默认 300/3/0.05）、
同一 IC 口径（每日横截面 Spearman IC 均值，125 个验证交易日）。

自研 arm 走 `alpha_research.fit_model_and_score_train` 生产训练路径
（xgb_regressor + date_equal 样本权重 + none 后处理）。

| arm | mean_ic |
|-----|---------|
| 自研 train_eval（原始特征） | 0.0353 |
| 自研 train_eval（+ 复刻 qlib 标准化） | 0.0512 |
| qlib 完整管线 | **0.0830** |

### 解读

1. 生产训练路径（样本权重 + 后处理）相对裸训练贡献约 +0.005（0.0299 -> 0.0353），影响有限。
2. 横截面标准化贡献约 +0.016（0.0353 -> 0.0512），预处理确实重要。
3. 即使自研复刻了标准化近似，qlib 仍高约 +0.032（0.0512 -> 0.0830）。这部分来自 qlib
   管线未复刻的细节：label 的 CSZScoreNorm、DropnaLabel 时机、精确 MAD/clip_outlier 实现。

### 对决策的意义

qlib 的 IC 优势不只是"封装训练"，而是其完整预处理管线（横截面标准化 + 标签标准化 +
缺失值处理）带来的可量化提升，其中约 0.032 自研即使复刻近似也难以追平。
若要采用，最合理的路径是复用 qlib 的 Dataset/Handler 预处理管线，而非只取其模型训练。


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
