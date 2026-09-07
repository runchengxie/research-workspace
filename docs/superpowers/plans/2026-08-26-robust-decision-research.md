# 稳健决策研究实施计划

> 面向智能体的执行说明：必须使用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development`，逐项执行本计划。使用复选框跟踪进度。

目标：增加由反例驱动的决策治理、可复用的组合不确定性基础能力，以及 `strategy-app` 中从预测到决策的评估回执，同时保持现有默认行为不变。

架构：工作区负责证据导航和校验，`portfolio-backtester` 负责通用的风险感知组合基础能力，`strategy-app` 负责策略特定的决策评估组合。此阶段不修改 Alpha 契约。

技术栈：Python 3.12 及以上版本、标准库、所属仓库已有的 NumPy/pandas、pytest，以及现有本地质量检查。

规格依据：`docs/superpowers/specs/2026-08-26-robust-decision-research-design.md`

## 全局约束

- 不修改生产目录或生命周期准入状态。
- 不增加第三方求解器依赖。
- 不宣称完整支持 DRO、MILP、C&CG 或 Benders。
- 保持现有文件和公开行为向后兼容。
- 不为了展示 schema 而制造虚假的研究证据。

## 任务 1：反例治理

文件：

- 创建：`strategy-research/schemas/counterexample.v1.schema.json`
- 创建：`strategy-research/counterexamples/README.md`
- 修改：`strategy-research/schemas/research_case.v1.schema.json`
- 修改：`scripts/decision_governance_check.py`
- 修改：`tests/test_decision_governance_check.py`
- 修改：`docs/research-decision-governance.md`

- [ ] 为反例校验、缺少 claim 引用和案例引用增加失败测试。
- [ ] 实现 `counterexample.v1` 校验和命令行扫描。
- [ ] 在没有 `counterexamples` 字段时，保持旧案例有效。
- [ ] 记录 DG8 反例驱动的稳健性要求。
- [ ] 在可执行的代码检出环境中，运行专项治理测试和完整工作区检查。

## 任务 2：组合不确定性基础能力

仓库：`runchengxie/portfolio-backtester`，分支 `feat/robust-portfolio-uncertainty`

文件：

- 创建：`src/portfolio_backtester/robust_uncertainty.py`
- 创建：`tests/test_robust_uncertainty.py`
- 修改：`src/portfolio_backtester/__init__.py`
- 修改：`docs/reference/public-api.md`
- 修改：`README.md`

- [ ] 为恒等情形、惩罚项、无效输入、多空最差收益和形状不匹配增加失败测试。
- [ ] 实现有限值、非负校验和区间不确定性基础能力。
- [ ] 导出公开 API，并记录功能限制。
- [ ] 在可执行的代码检出环境中，运行专项 pytest、代码检查、格式检查、类型检查、完整测试和可维护性检查。
- [ ] 创建所属仓库的 PR。

## 任务 3：面向决策的评估回执

仓库：`runchengxie/strategy-app`

文件：检查现有包结构后，在已有的通用 campaign 或 evidence 工具位置实现。

- [ ] 为方向感知差异、确定性序列化和无效指标增加失败测试。
- [ ] 实现不可变的类型化回执，不导入所属仓库的私有实现。
- [ ] 在现有应用或证据文档中增加公开导入和说明。
- [ ] 在可执行环境中运行 `strategy-app` 质量检查。
- [ ] 创建所属仓库的 PR。

## 任务 4：集成和 PR

- [ ] 将每个功能分支与 `main` 比较，逐个检查所有改动文件。
- [ ] 运行本地可执行的隔离测试，记录准确的命令和结果。
- [ ] 先创建 portfolio 和 strategy-app 所属仓库的 PR。
- [ ] 等所属仓库的 PR 合并后，再创建工作区治理 PR，不提前推进子模块 gitlink。
- [ ] 在 PR 说明中明确列出连接器环境无法运行的完整仓库检查。

## 按设计延后

- 完整的两阶段补救优化器
- MILP/MIQP 组合求解器
- 分布鲁棒优化或学习方法
- C&CG/Benders 求解器分解

这些内容应由具体的策略或规模需求触发，作为后续工作处理，不作为当前实现的占位功能。
