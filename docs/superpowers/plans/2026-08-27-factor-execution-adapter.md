# 因子执行适配器实施计划

> 面向智能体的执行说明：建议使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，逐项执行本计划。使用复选框跟踪进度。

目标：让小市值低换手实验生成标准的 `portfolio-backtester` 持仓产物，并提供经过测试的执行入口，同时保持信号构造不变。

架构：数据准备、候选排名、资格判断和缓冲目标构造保留在 `strategy-research`。新增轻量适配器，将这些目标标准化为 `positions_by_rebalance` 契约，再通过专用研究辅助函数调用所属仓库的执行 API。第一版保留现有运行器，同时增加一条可并行测试的路径，避免历史输出被静默改变。

技术栈：Python 3.13、pandas、pytest、uv、`portfolio_backtester`。

规格依据：用户提出的复用 `research-workspace/portfolio-backtester` 进行小市值低换手回测的需求。

## 全局约束

- 本次迁移不修改信号定义、候选资格、目标数量、缓冲数量或历史输出语义。
- 使用 `portfolio_backtester.positions_by_rebalance` 契约和所属仓库的公开 API，不在运行时导入相邻源代码路径。
- 先写测试，再写生产代码，并在实现前确认预期的失败结果。
- 不将生成产物、凭证或本机绝对路径加入跟踪文件。

## 任务 1：修复并验证本地依赖环境

文件：

- 仅在锁文件确实过期时修改：`strategy-research/uv.lock`
- 测试：现有 `strategy-research/tests/test_small_cap_low_turnover_exploration.py`

接口：

- 输入：`strategy-research/pyproject.toml` 声明的本地路径依赖。
- 输出：能够导入当前 `ExecutionSimConfig` 的可复现环境。

- [x] 步骤 1：运行失败测试基线。命令为 `uv run --project strategy-research --extra dev python -m pytest strategy-research/tests/test_small_cap_low_turnover_exploration.py -q`，预期 26 个通过、3 个失败，失败原因是缺少 `liquidity_notional_multiplier` 构造字段。
- [x] 步骤 2：重新安装本地所属仓库包，运行 `uv sync --project strategy-research --locked --reinstall-package portfolio-backtester`。
- [x] 步骤 3：验证导入的接口，打印 `portfolio_backtester.__file__`，并断言 `ExecutionSimConfig.__dataclass_fields__` 包含 `liquidity_notional_multiplier`。
- [x] 步骤 4：再次运行专项测试文件。三个构造失败应消失，新增失败必须作为真实行为不一致单独调查。

## 任务 2：定义标准持仓适配器

文件：

- 创建：`strategy-research/style_factors/portfolio_backtester_adapter.py`
- 测试：`strategy-research/tests/test_portfolio_backtester_adapter.py`

接口：

- 输入：带缓冲的目标映射，或包含 `rebalance_date`、`entry_date`、`symbol` 和目标权重或名义金额的目标表。
- 输出：`to_positions_by_rebalance(targets, portfolio_value) -> pd.DataFrame`，列包括 `rebalance_date`、`entry_date`、`symbol` 和 `weight`。

- [x] 步骤 1：编写覆盖目标标准化、确定性排序、同一调仓日重复标的拒绝和空输入行为的失败测试。
- [x] 步骤 2：运行适配器测试，确认预期的缺少导入失败。
- [x] 步骤 3：实现最小适配器。校验必需列，标准化日期，接受 `weight` 或 `target_weight`，拒绝重复的 `(rebalance_date, symbol)` 行，保留明确的现金缺口，稳定排序，并调用所属仓库的契约校验器。
- [x] 步骤 4：运行适配器测试，确认全部通过。

## 任务 3：增加经过测试的所属仓库执行辅助函数

文件：

- 修改：`strategy-research/style_factors/portfolio_backtester_adapter.py`
- 测试：`strategy-research/tests/test_portfolio_backtester_adapter.py`

接口：

- 输入：标准持仓表、价格表和执行配置。
- 输出：`CanonicalBacktestResult` 或 `NativePositionReplayBackend` 返回的所属仓库执行结果。

- [x] 步骤 1：使用两个标的和多个日期的价格表编写失败的合成执行测试，断言辅助函数返回每日净值、订单和成交，并包含预期的标的和日期。
- [x] 步骤 2：运行测试，确认失败原因是缺少辅助函数。
- [x] 步骤 3：实现轻量辅助函数，构造所属仓库后端请求，将配置创建放在适配器外部，避免 `portfolio-backtester` 导入 `strategy_research` 内部实现。
- [x] 步骤 4：运行合成执行测试，确认当前 worktree 环境安装的所属仓库源码可以通过测试。

## 任务 4：增加并行研究入口

文件：

- 修改：`strategy-research/experiments/style_factors/small_cap_low_turnover_exploration_20260826.py`
- 测试：`strategy-research/tests/test_small_cap_low_turnover_exploration.py`

接口：

- 输入：现有 `formation_targets` 和价格数据。
- 输出：可选的所属仓库引擎执行结果，同时保留用于比较的旧矩阵。

- [x] 步骤 1：增加集成层失败测试，确认合成的缓冲目标可以经过适配器和所属仓库执行辅助函数，同时不改变现有信号面板。
- [x] 步骤 2：实现最小的并行入口，增加默认不写出产物的可选辅助函数或命令行参数，不替换历史运行路径。
- [x] 步骤 3：运行专项集成测试。
- [x] 步骤 4：运行完整的 `strategy-research` 测试套件，命令为 `uv run --project strategy-research --extra dev python -m pytest strategy-research/tests -q`。

## 任务 5：记录迁移边界和验证回执

文件：

- 修改：`strategy-research/experiments/style_factors/small-cap-low-turnover-exploration-20260826.md`
- 如果新入口面向用户，再修改：`strategy-research/README.md`

接口：

- 输入：经过验证的测试和执行结果。
- 输出：说明哪条路径为规范路径、哪条路径仅用于比较，以及冲击或滑点是否真正生效的文档。

- [x] 步骤 1：只根据已验证行为更新文档。
- [x] 步骤 2：运行相关文档和路径检查，以及完整专项测试套件。
- [x] 步骤 3：检查差异并记录剩余迁移缺口。
