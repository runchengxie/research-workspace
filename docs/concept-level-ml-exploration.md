# 概念级截面排名 ML 探索路线图（Path C）

> 状态：待探索 · 优先级：低 · 成功概率估计：30-40%
>
> 目标：用同花顺热榜和概念板块数据构建概念级 ML 截面排名能力，替代当前的硬编码概念频率规则。最终要回答的问题是：给定历史热点模式，明天哪些概念更可能跑赢。

## 前置约束（必须先验证的假设）

| 编号 | 假设 | 验证方式 | 通过标准 |
| --- | --- | --- | --- |
| H1 | 热榜概念有持续性信号（连续多天上榜的概念，次日成分股仍有正超额） | 计算连续上榜 N 天和首次上榜概念的后续收益率差异 | 连续上榜组的平均超额 > 0 且显著 |
| H2 | 热榜排名变化包含预测信息（排名上升的概念次日跑赢排名下降的） | 计算 rank_momentum vs 次日概念成分股等权收益率的相关性 | Spearman rank IC > 0.03 |
| H3 | 概念成分股的截面特征（市值中位数、换手率、波动率）能区分概念质量 | 用概念成分股的中位数特征做截面排名，看 IC | Mean rank IC > 0.02 |
| H4 | kpl 概念成分股列表的日频变动是可管理的（变动率 < 5%/天） | 统计连续 30 天概念成分股名单的重叠率 | 日均变动 < 5% |

探索阶段必须先验证 H1-H4，再进入建模。如果 H1 和 H2 都不成立，热榜就不具备概念级预测信号的基本前提。

## 阶段 1：数据工程（前提条件）

### 1.1 概念名称归一化
- 问题：同花顺概念名不稳定，例如 AI 算力、AI 算力概念、算力概念可能指向同一主题。
- 方案：建立 `concept_alias` 映射表，结合模糊匹配和人工审核。
- 产出：`concept_id_mapping.csv`，每个 `concept_id` 对应一个标准名。

### 1.2 概念成分股日频快照
- 问题：`kpl_concept_cons` 只覆盖 394 天（2024-10 至 2026-05）。
- 方案：整合 `kpl`、`dc_concept_cons`（74 天）和 `ths_hot` 概念字段，做三方校验。
- 产出：`concept_constituents_daily.parquet`，记录每天每个概念的成分股列表。

### 1.3 概念级收益率标签
- 方案：用概念成分股等权的 T+1 open 至 T+2 open 收益率，并取中位数降低异常值影响。
- 对比：用市值加权、流通市值加权做敏感性分析。
- 产出：`concept_daily_returns.parquet`。

### 1.4 概念归因穿透
- 方案：对概念收益率做 Barra 风格因子归因，分离出纯概念 alpha。
- 理由：一个概念可能只是因为暴露于动量因子而跑赢，这类收益不能直接归因于概念信号。
- 产出：`concept_residual_returns.parquet`。

## 阶段 2：特征工程（核心创新）

### 2.1 概念时序特征

| 特征类别 | 具体特征 | 窗口 |
| --- | --- | --- |
| 持续性 | consecutive_days_on_hot_list | 回溯 20 天 |
| 热度动量 | hot_rank_change_1d/3d/5d, hot_score_acceleration | 1/3/5 天 |
| 上榜股票数量 | on_list_stock_count, stock_count_change | 当日/3日变化 |
| 概念内动量 | mean_return_1d/5d/20d, median_return_1d/5d/20d | 成分股均值/中位数 |
| 概念内波动 | vol_20d, dispersion_20d | 成分股截面离散度 |
| 概念内资金 | mean_turnover_5d, mean_amount_5d | 成分股均值 |
| 概念宽度 | unique_stocks_1m, breath_change | 上榜股票多样性 |
| 涨停/跌停比例 | limit_up_ratio, limit_down_ratio | 当日 |

### 2.2 概念间特征（联动效应）

| 特征类别 | 具体特征 | 说明 |
| --- | --- | --- |
| 关联概念热度 | related_concept_hot_score | 同行业/同主题概念的当日热力值 |
| 概念轮动方向 | rotation_vector_similarity | 与前 5 天轮动方向的余弦相似度 |
| 概念簇热度 | cluster_avg_hot_rank | 同一行业簇的概念平均热度 |

### 2.3 市场环境特征

| 特征类别 | 具体特征 |
| --- | --- |
| 市场宽度 | advance_decline_ratio, up_volume_ratio |
| 市场波动 | market_vol_20d, market_dispersion |
| 行业轮动速度 | sector_rotation_speed_5d/20d |
| 流动性环境 | total_market_turnover, margin_balance_change |

## 阶段 3：模型设计

### 3.1 模型选型（按优先级）

| 方案 | 优点 | 缺点 | 适用条件 |
| --- | --- | --- | --- |
| LinearRank (ridge) | 和 rotation-v3 一致，可解释性强 | 只学线性关系 | 特征量 < 50 |
| LightGBM ranker | 非线形、交互项自动学习 | 样本量需求高 | 样本 > 10000 |
| XGBoost ranker | 和 LightGBM 类似，不同 bias | 同上 | 作为对照 |
| SimpleTransformer | 时序建模能力强 | 过拟合风险极高 | 样本 > 50000 |

建议先用 LinearRank，因为它假设少、解释性好。特征工程证明有效后，如果线性模型容量不够，再升级到 LightGBM。

### 3.2 标签选择

| 标签 | 定义 | 优点 | 缺点 |
| --- | --- | --- | --- |
| raw_return | 概念成分股等权 T+1 至 T+2 收益 | 直接可解释 | 受市场 beta 影响 |
| residual_return | 去 Barra 风格后的残余收益 | 纯 alpha | 需要额外归因层 |
| cross_sectional_rank | 当天横截面排名 | 天然截面比较 | 损失收益量级信息 |

建议先用 `raw_return`。如果 beta 污染严重，再切到 `residual_return`。

### 3.3 验证框架

```
训练集：2024-10 至 2025-06（walk-forward，step=20 天）
测试集：2025-07 至 2026-05

每折：
  1. 用截止到 train_cutoff 的数据训练模型
  2. 对未来 20 天做样本外预测
  3. 计算日频 rank IC 和 ICIR
  4. 模拟 top-N 概念等权组合的样本外收益
```

通过标准：
- Mean rank IC > 0.03
- ICIR > 0.3
- 样本外 top-3 概念组合跑赢全 A 等权基准（年化超额 > 3%）
- Walk-forward 所有折的 Sharpe 中位数 > 0

## 阶段 4：执行层（从概念到股票）

### 4.1 概念到股票映射精度提升

当前问题：概念名到 `kpl name` 列的匹配只做简单 substring 匹配。

改进方案：
- 用概念成分股的截面量价特征做子排序，把 `strategy-pipeline` 的能力下沉到概念内。
- 每个概念取 top N 只股票（按量价因子得分），而非 random 等权
- 考虑流动性过滤（剔除日均成交额 < 5000 万的股票）

### 4.2 组合构建

| 参数 | 候选值 | 说明 |
| --- | --- | --- |
| top_concepts | 3/5/8 | 持有概念数 |
| stocks_per_concept | 5/10/15 | 每个概念取几只股票 |
| rebalance_freq | 1d/3d/5d | 调仓频率 |
| max_weight_per_stock | 5%/10%/15% | 单票权重上限 |
| turnover_constraint | 0.2/0.5/1.0 | 换手率约束 |

## 阶段 5：与现有管线的集成

```
目标架构：

  ths_hot + dc_concept + kpl_concept_cons
          │
          ▼
  ┌──────────────────────┐
  │ Concept Feature Engine│  ← 新模块
  │ (概念时序特征计算)     │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ Concept Rank Model    │  ← 新模块
  │ (截面排名 prediction)  │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ hotspot-universe      │  ← 现有模块改造
  │ (topic → concept →    │     不再用 LLM topic classification
  │  stock, 但改用 ML     │     改用概念 ML 排名结果
  │  排名结果代替硬编码)   │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ strategy-pipeline │  ← 现有模块，不改
  │ (概念内股票量价排名)   │
  └──────────────────────┘
```

## 里程碑和时间估计

| 里程碑 | 内容 | 估计工时 |
| --- | --- | --- |
| M1 | H1-H4 假设验证 | 4-6h |
| M2 | 概念名称归一化 + 数据管道 | 8-12h |
| M3 | 概念特征工程 v1 | 8-12h |
| M4 | LinearRank 训练 + 回测 | 4-6h |
| M5 | 结果分析和迭代 | 8-16h |
| M6 | 概念到股票执行层对接 | 8-12h |

总计：40 至 64 小时（2 到 3 周全职）。

## Go / No-Go 决策点

| 决策点 | 触发条件 | Go 条件 |
| --- | --- | --- |
| D1 | H1+H2 验证完成 | 至少一个假设通过验证 |
| D2 | M3 特征工程完成 | rank IC > 0.02 的特征 ≥ 5 个 |
| D3 | M4 回测完成 | 样本外 rank IC > 0.03, ICIR > 0.3 |
| D4 | M6 集成完成 | 模拟组合跑赢全 A 等权基准 |

## 已知风险和缓解

| 风险 | 概率 | 缓解 |
| --- | --- | --- |
| 概念名称不稳定导致数据断裂 | 高 | 建立 alias 映射 + 模糊匹配 + 人工审核 |
| 概念成分股变动频率过高 | 中 | 用 3 日平滑 + 对变动率设定阈值 |
| 样本量不足以支撑 ML | 高 | 先从 LinearRank 开始，只用少量稳健特征 |
| 热榜信号衰减过快 | 高 | 缩短持有期到 T+1 open 至 close，不做隔夜 |
| 概念间相关性导致过拟合 | 中 | 用 walk-forward + purge/embargo 严格防控 |
