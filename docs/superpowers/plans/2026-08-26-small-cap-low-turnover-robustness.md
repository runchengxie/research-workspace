# 小市值低换手稳健性实施计划

> 面向智能体的执行说明：建议使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，逐项执行本计划。使用复选框跟踪进度。

目标：扩展小市值与低换手比较研究，增加换手定义、前期成交金额参与率和整数手数敏感性证据。

架构：研究保留在 `strategy-research`。为现有受约束模拟器增加可选的容量和目标权重取整输入，不改变默认行为。实验运行器复用一份已加载的市场契约，生成紧凑的稳健性矩阵。将 2015–2023 年作为开发期，将 2024–2026 年固定为仅用于报告的留出期。

技术栈：Python 3.12 及以上版本、pandas、NumPy、pytest、现有的 `robustness_execution` 模拟器，以及现有的 `strategy-research` 数据契约。

规格依据：`strategy-research/experiments/style_factors/small-cap-low-turnover-exploration-20260826.md`

## 全局约束

- 保持 `exploration_only`，不修改 `strategy-research/catalog.json` 或生产配置。
- 保持 `simulate_leg` 和所有现有稳健性调用方的默认行为。
- 使用 100 股的 A 股交易手数取整，并明确报告连续权重的限制。
- 将前期实际成交金额的 5%、10% 和 20% 作为参与率敏感性情形。
- 只使用滞后的换手率，回看窗口不能包含建仓交易日。
- 不能使用 2024–2026 年留出期选择参数。

## 任务 1：增加经过测试的执行敏感性

文件：

- 修改：`strategy-research/style_factors/robustness_execution.py`
- 修改：`strategy-research/style_factors/small_cap_low_turnover.py`
- 测试：`strategy-research/tests/test_small_cap_low_turnover_exploration.py`

接口：

- `simulate_leg(..., max_trade_weight: np.ndarray | None = None)`：传入该参数时限制每日每个标的的权重变化，传入 `None` 时保持现有行为。
- `round_target_weights_to_lots(targets, daily_clean, initial_capital, lot_size=100)`：返回按股数向下取整后的目标权重。
- `build_trade_capacity_matrix(daily_clean, returns, initial_capital, participation_rate)`：返回按日期和标的划分的最大交易权重矩阵。
- `build_lagged_turnover_panel(..., statistic="mean")`：生成 `turnover_lagged_<statistic>_<window>d`。

- [x] 步骤 1：为受限待成交订单、100 股目标取整、滞后换手率中位数和零容量矩阵行编写失败测试。
- [x] 步骤 2：运行专项测试文件，确认接口尚未存在时新测试失败。
- [x] 步骤 3：实现可选执行上限和两个小市值辅助函数，不改变默认模拟行为。
- [x] 步骤 4：为换手率辅助函数增加均值和中位数聚合，同时保留默认的 60 日均值输出。
- [x] 步骤 5：运行专项测试、代码检查和类型检查，确认全部通过。

## 任务 2：生成稳健性矩阵

文件：

- 修改：`strategy-research/experiments/style_factors/small_cap_low_turnover_exploration_20260826.py`
- 测试：`strategy-research/tests/test_small_cap_low_turnover_exploration.py`

接口：

- 增加运行器辅助函数，为每一行标注 `turnover_definition`、`participation_rate`、`lot_size` 和 `holdout_period`。
- 仅在敏感性矩阵中让原始复合信号复用 `simulate_long_only_candidates`，保留完整的七分支基准比较。
- 增加 `candidate_robustness_matrix.csv`，并在 Markdown 报告中加入开发期和留出期净收益。

- [x] 步骤 1：为开发期和留出期收益辅助函数编写失败测试。
- [x] 步骤 2：运行专项测试，确认辅助函数缺失时测试失败。
- [x] 步骤 3：实现 `mean_20`、`mean_60`、`median_60` 和 `mean_120` 换手定义，以及 `unconstrained`、`0.05`、`0.10` 和 `0.20` 参与率情形。
- [x] 步骤 4：在敏感性情形中应用 100 股取整，写入矩阵 CSV、报告章节和元数据。
- [x] 步骤 5：运行专项测试和小型合成运行器检查。

## 任务 3：运行、记录和验证

文件：

- 修改：`strategy-research/experiments/style_factors/small-cap-low-turnover-exploration-20260826.md`
- 外部生成：`/tmp/small_cap_low_turnover_exploration_20260826/*`

- [x] 步骤 1：运行完整的 2015–2026 年实验，输出写入 `/tmp`。
- [x] 步骤 2：检查稳健性矩阵中的成本或容量崩溃、换手敏感性和留出期表现。
- [x] 步骤 3：根据观测到的矩阵结果更新跟踪的研究结论，并明确限制。
- [x] 步骤 4：运行完整的 `strategy-research` 测试、Ruff、格式检查、类型检查和 `git diff --check`。
- [x] 步骤 5：在本地提交经过验证的扩展，不推送、不合并。
