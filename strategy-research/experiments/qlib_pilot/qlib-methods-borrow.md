# qlib 方法借鉴：改进 D11-H5 OOS 泛化

> 日期：2026-08-09
> 针对问题：OOS 过拟合（train IC 0.14 vs OOS ~0）、6月+27%/7月-32% 风格摇摆

## 可借鉴能力（qlib 已安装于 experiments/qlib_pilot venv）

### 1. DropnaLabel / 样本清洗
qlib 的 DropnaLabel 处理器按日期清洗 label 噪声样本。对应发现：流动性好的
股票 OOS IC 0.07 vs 全市场 ~0。借鉴：训练前按流动性/样本质量过滤，而非
全市场直接训练。

### 2. double_ensemble（集成降过拟合）
qlib 的 DEnsembleModel 用多模型集成平滑单模型噪声拟合，直接对症
train IC 0.14 vs OOS ~0 的过拟合。base_model 可配（gbm 等）。
借鉴：XGB 多模型集成或 bagging。

### 3. 严格 walk-forward + PIT
qlib 标准做法：train/valid 严格时间隔离 + 固定窗重训 + PIT 对齐数据。
借鉴：a_share 的 walk-forward 对齐 qlib 的 n_windows/step 语义，确保
训练不接触验证期信息。

### 4. 三层结构（数据处理/模型/组合回测分离）
qlib 强调三层分离 + 每层标准验证。你的策略把模型信号直接变 top_k 持仓，
缺少组合构建校验层。风格约束应放在这个中间层。

## 落地优先级

1. 样本过滤（对应流动性质量）——最快，直接改善 OOS
2. 集成模型（double_ensemble 思路）——降低过拟合
3. 组合层风格约束（max_abs_style_cap）——控制回撤

## 关联

- D11-H5 回撤根因：风格暴露失控
- 全市场 OOS IC ~0：小盘信号不可靠
- 抽样 500 只 OOS IC 0.07：流动性质量决定信号可靠性
