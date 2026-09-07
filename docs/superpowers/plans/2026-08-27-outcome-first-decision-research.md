# 结果优先的决策研究实施计划

> 面向智能体的执行说明：建议使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，逐项执行本计划。使用复选框跟踪进度。

目标：增加机器可检查的结果画像、可复用的结果和路径指标、支持 Pareto 关系的决策回执，以及仅用于研究的 DailyWatch20 路径感知退出方案，同时保持生产行为不变。

架构：治理仍由顶层 `strategy-research` 负责，通用的已实现结果指标放在 `portfolio-backtester`，策略特定的比较和退出逻辑放在 `strategy-app`。三个 PR 可以独立审查。P4 通用路径和 barrier 基础设施暂不实现。

技术栈：Python 3.12 及以上版本、pandas、NumPy、JSON Schema、pytest、Ruff、ty、uv。

规格依据：`docs/superpowers/specs/2026-08-27-outcome-first-decision-research-design.md`

## 全局约束

- 预测、组合构造、策略逻辑和治理继续由当前所属仓库负责。
- 不从 Alpha 分数合成不确定性。
- 不创建单一效用分数或综合置信度分数。
- 不为退出方案增加参数网格搜索。
- 所有新增行为必须显式启用，当前生产输出保持不变。
- P4 通用路径和 barrier 基础设施不在本计划范围内。

## 任务 1：结果画像治理

文件：

- 创建：`strategy-research/schemas/outcome_profile.v1.schema.json`
- 修改：`strategy-research/schemas/research_case.v1.schema.json`
- 修改：`scripts/decision_governance_check.py`
- 修改：`tests/test_decision_governance_check.py`
- 修改：`docs/research-decision-governance.md`

接口：

- 输入：现有 `research_case.v1` 和治理校验约定。
- 输出：`outcome_profile.v1`、`check_outcome_profile()`，以及可选的 `research_case.v1.outcome_profiles` 引用。

- [ ] 编写失败测试，证明有效结果画像可以通过，重复指标名、约束不完整和缺失画像引用会失败。
- [ ] 运行 `python -m pytest tests/test_decision_governance_check.py -q`，确认失败来自缺少结果画像支持。
- [ ] 增加 JSON Schema，校验决策类型、状态、指标角色、方向和约束。
- [ ] 扩展 `decision_governance_check.py`，增加 `OUTCOME_PROFILE_SCHEMA_VERSION`、画像校验、文件名身份校验、案例引用校验、`--outcome-profile` 和全量扫描发现。
- [ ] 为 `research_case.v1.schema.json` 增加可选的 `outcome_profiles` 字符串引用。
- [ ] 更新 `docs/research-decision-governance.md`，说明偏好与预测的语义，以及经验可行性的表述方式。
- [ ] 运行专项治理测试和决策治理命令行扫描。

## 任务 2：通用已实现结果指标

文件：

- 创建：`portfolio-backtester/src/portfolio_backtester/outcome_metrics.py`
- 创建：`portfolio-backtester/tests/test_outcome_metrics.py`
- 修改：`portfolio-backtester/src/portfolio_backtester/__init__.py`
- 修改：`portfolio-backtester/tests/test_package_smoke.py`
- 修改：`portfolio-backtester/docs/reference/public-api.md`
- 修改：`portfolio-backtester/README.md`

接口：

- 输出：不可变的 `OutcomeDistributionReport` 和 `summarize_outcome_distribution()`。
- 输入：长度相同的已实现收益、MFE、MAE、峰值回撤和持有期序列。

- [ ] 为精确分位数、亏损概率、5% CVaR、MFE、MAE、峰值回撤和持有期汇总编写失败测试。
- [ ] 为输入为空、包含非有限值、持有期为负和长度不一致增加失败测试。
- [ ] 运行 `uv run --locked --extra dev python -m pytest tests/test_outcome_metrics.py -q`，确认测试失败。
- [ ] 实现 `OutcomeDistributionReport` 和 `summarize_outcome_distribution()`，采用失败即关闭的校验方式。
- [ ] 导出新的公开 API，并修复 `test_package_smoke.py` 中已有的稳健性不确定性导出不一致。
- [ ] 更新面向用户的 API 文档，不改变已有回测输出契约。
- [ ] 运行专项测试、包 smoke 测试、Ruff、格式检查、ty、可维护性检查和完整测试套件。

## 任务 3：支持 Pareto 关系的决策回执

文件：

- 修改：`strategy-app/src/strategy_app/decision_evaluation.py`
- 修改：`strategy-app/src/strategy_app/__init__.py`
- 修改：`strategy-app/tests/test_decision_focused_evaluation.py`

接口：

- 输出：`ParetoRelation`、`pareto_relation()` 和 `DecisionEvaluationReceipt.pareto_relation`。

- [ ] 为候选方案支配基线、基线支配候选、等价和混合权衡编写失败测试。
- [ ] 运行决策评估测试，确认测试失败。
- [ ] 实现方向标准化的 Pareto 比较，不使用容差或汇总评分。
- [ ] 为关系增加确定性序列化，同时保留现有构造器调用签名。
- [ ] 运行专项测试、代码检查和类型检查。

## 任务 4：DailyWatch20 路径感知退出研究覆盖层

文件：

- 创建：`strategy-app/src/strategy_app/daily_watch20/path_aware_exit.py`
- 修改：`strategy-app/src/strategy_app/daily_watch20/__init__.py`
- 创建：`strategy-app/tests/test_daily_watch20_path_aware_exit.py`
- 修改：`strategy-app/docs/application-catalog.md`

接口：

- 输出：`PathAwareExitPolicy`、`PathAwareExitResult`、`evaluate_path_aware_exit_episode()`、`evaluate_path_aware_exit_challenger()`。
- 输入：包含 `trade_id`、`trade_date`、`price`、`score`、`uncertainty` 的基准交易片段。
- 结果：每笔交易的基准和挑战方案退出结果，以及不可升级为生产方案的回执。

- [ ] 为峰值回撤触发、分数衰减或不确定性或持有期增加时收紧阈值、基准回退、无效标准化输入，以及重复或无序片段行编写失败测试。
- [ ] 增加失败测试，证明一次运行只接受一份不可变策略，并生成 `parameter_search_allowed=false`、`automatic_promotion_allowed=false` 和必需的校验名称。
- [ ] 运行新测试文件，确认测试失败。
- [ ] 实现不可变策略和带 `[min_drawdown, base_drawdown]` 截断的标量阈值计算。
- [ ] 使用第一行作为入场、最后一行作为基准退出评估交易片段。挑战方案只能在基准退出日当天或之前退出。
- [ ] 按 `trade_id` 分组评估，保持确定性顺序，并输出策略 SHA-256 和校验要求。
- [ ] 将该应用记录为仅用于研究，并明确说明提前退出后不会重新分配资金。
- [ ] 运行专项测试、除已记录的既有样式失败外的全部 `strategy-app` 测试、Ruff、格式检查、ty 和可维护性检查。

## 任务 5：准备 PR 和集成证据

文件：仅修改生成的分支元数据，或在所属仓库 PR 已准备好固定版本时修改顶层 gitlink。

- [ ] 检查每个仓库的差异，确认没有违反所属边界或混入无关改动。
- [ ] 运行各仓库要求的本地检查，将既有失败与功能失败分开记录。
- [ ] 使用范围明确的提交信息提交三个分支。
- [ ] 先推送所属仓库分支，创建 `portfolio-backtester` 和 `strategy-app` PR。
- [ ] 再推送顶层治理分支并创建 PR。除非明确标记为依赖 PR，否则不要固定尚未合并的所属仓库 gitlink。
- [ ] 请求审查，并报告准确的测试结果、已知基线失败和延后的 P4 范围。
