# A 股长期基本面选股 v2 实施计划

> 面向智能体的执行说明：建议使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`，逐项执行本计划。使用复选框跟踪进度。

目标：建立一套满足点时条件、仅用于研究的 v2 方案，用于识别持续的经营质量、过滤价值陷阱，在数据可用时加入盈利预期变化，并评估低换手季度组合的成熟收益表现。

架构：数据获取和版本来源由 `market-data-platform` 负责，可复用的目标和分数由 `alpha-research` 负责，研究组合由 `strategy-research` 负责。第一版使用明确的目标契约和简单基线，不推动策略发布，也不增加生产接线。

技术栈：Python、pandas、NumPy、Parquet、pytest，以及现有的 alpha 和 `portfolio-backtester` API。

规格依据：`strategy-research/research/experiments/fundamental_state_forecasting/README.md`

## 全局约束

- 每个特征和标签都必须满足点时条件，并携带可用性语义。
- 稳定复合增长者标签在通过样本外测试前只能用于描述。
- 季度调仓和存量持仓缓冲必须使用一套明确的成本和样本外日历。
- 在通过多区间样本外、成本、暴露和数据血缘检查前，不得推动生产发布。
- 使用分析师预测或修订数据前，必须证明其当时可用。无法证明时，记录数据缺口结果。

## 任务 1：冻结 v2 研究规格

文件：

- 创建：`strategy-research/research/experiments/long_term_fundamental_v2/README.md`
- 测试：`strategy-research/tests/test_long_term_fundamental_v2_spec.py`

- [ ] 在 README 中定义稳定复合增长者的宽松和严格标签、价值陷阱排除条件、季度更新规则和失败门槛。
- [ ] 增加测试，确认规格记录仅用于研究、点时要求和不具备生产资格。
- [ ] 运行专项测试，确认在加入实现契约前测试失败。
- [ ] 实现最小规格加载器和校验器，再次运行专项测试。

## 任务 2：增加经营质量持续性和价值陷阱研究函数

文件：

- 修改：`strategy-research/research/experiments/long_term_fundamental_v2/quality.py`
- 测试：`strategy-research/tests/test_long_term_fundamental_v2_quality.py`

- [ ] 测试标签只能使用建仓日可见的观测值，需要三年年度观测，并区分宽松和严格标签。
- [ ] 测试价值陷阱过滤器能够依据明确阈值排除盈利为负、增长恶化、杠杆极高和估值极端的股票。
- [ ] 实现按日期确定性的标签构造和诊断。
- [ ] 运行专项测试并记录标签覆盖范围。

## 任务 3：增加经营质量持续性目标

文件：

- 修改：`alpha-research/src/alpha_research/fundamental_state.py`
- 测试：`alpha-research/tests/test_fundamental_state.py`

- [ ] 在源数据存在相应列时，增加未来 ROA 恶化、利润率持续性、正增长持续性和现金转化恶化目标。
- [ ] 保留目标报告期、目标可用日期和标签结束日期。
- [ ] 只在相同的严格样本外折中比较持续性模型、Ridge 和 XGB。
- [ ] 运行 alpha 专项测试并保存目标覆盖诊断。

## 任务 4：审计盈利预期变化的数据可用性

文件：

- 创建：`strategy-research/research/experiments/long_term_fundamental_v2/expectations_audit.py`
- 测试：`strategy-research/tests/test_long_term_fundamental_v2_expectations.py`

- [ ] 检查可用的点时预测、表达、分析师修订和盈利惊喜数据资产。
- [ ] 如果存在公告时间的修订历史，增加满足修订时点安全要求的特征契约和测试。
- [ ] 如果数据不可用，生成明确的数据缺口回执，不得使用未来才知道的值替代。

## 任务 5：运行季度低换手组合评估

文件：

- 修改：`strategy-research/research/experiments/fundamental_state_forecasting/four_arm_backtest.py`
- 创建：`strategy-research/research/experiments/long_term_fundamental_v2/run_quarterly_research.py`
- 测试：`strategy-research/tests/test_long_term_fundamental_v2_quarterly.py`

- [ ] 根据声明的日历生成季度调仓日期，并应用新进入持仓和存量持仓退出缓冲。
- [ ] 在同一成本条件下比较仅质量、质量加价值、质量加预期以及 DailyWatch20 控制组。
- [ ] 保存收益成熟度覆盖、换手率、回撤、规模、行业和估值暴露回执。
- [ ] 运行专项测试和有界的真实数据 smoke 检查，再进行更大范围回放。

## 任务 6：发布研究报告并做准入判断

文件：

- 创建：`strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`
- 修改：`strategy-research/research/experiments/fundamental_state_forecasting/20260902_four_arm_recent_diagnostic.md`

- [ ] 分开记录严格可比结果、诊断结果和数据缺口。
- [ ] 记录每个准入条件的通过、失败或尚未验证状态。
- [ ] 只有在所有必需证据通过后，才允许该策略继续保持研究状态之外的资格。
- [ ] 运行相关完整测试套件，并根据生成的回执核对最终报告。
