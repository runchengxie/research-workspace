# 文档归集与去重清单

> status: active
> owner: workspace
> last_verified: 2026-08-17
> source_of_truth: yes
> superseded_by: n/a

本页登记当前说明文档的碎片化问题、权威入口和归集动作。目标是让每类事实只有一个状态来源，
同时保留子仓实现说明和带日期的历史证据。

## 归集原则

- 当前状态只保留一个权威入口。
- 机器可读事实留在 YAML 或 JSON，Markdown 负责解释和导航。
- 根工作区说明跨仓库边界，子仓说明本仓实现和操作方式。
- 带日期、哈希或评审结论的材料保留原文并进入 archive 或 evidence。
- README 只给定位和最短路径，不复制完整状态表、字段表和测试矩阵。
- 动态提交号、资产行数和测试数量优先由命令生成，减少手工静态副本。

## 碎片化清单

| 编号 | 主题 | 当前权威入口 | 重复或漂移来源 | 归集动作 | 状态 |
| --- | --- | --- | --- | --- | --- |
| DOC1 | 工作区路线图 | [roadmap.md](roadmap.md) | 策略边界路线图、框架账本、会计路线图、多个执行计划各自表达总状态 | 总状态归入 `roadmap.md`，专项文档只保留细节和机器记录 | 本轮完成 |
| DOC2 | 架构与模块边界 | [../ARCHITECTURE.md](../ARCHITECTURE.md) | 根 README、AGENTS、platform workflow、策略目录重复描述六仓职责 | ARCHITECTURE 保存完整边界，其他入口压缩为摘要和链接 | 待处理 |
| DOC3 | 发布与架构复核 | [release-checklist.md](release-checklist.md) | `architecture-split-closure-checklist.md` 与发布清单重复质量、契约和边界检查 | 唯一发布清单归入 `release-checklist.md`，旧架构清单降级为完成记录 | 本轮完成 |
| DOC4 | A 股资产与就绪度 | `a_share_current.json`、[data-transition-playbook.md](data-transition-playbook.md) | docs README、pipeline playbook、数据平台研究 profile 和带日期 evidence 重复静态覆盖数字 | current contract 保存事实，playbook 解释门槛，子仓页面只保留操作和消费方式 | 待处理 |
| DOC5 | 策略身份与生命周期 | [strategy-research/README.md](../strategy-research/README.md)、[catalog.json](../strategy-research/catalog.json) | 根 strategy catalog、pipeline strategy catalog、strategy-app application catalog 各自列策略状态 | catalog 独占生命周期，pipeline 只列 CLI，strategy-app 只列可执行研究应用 | 进行中 |
| DOC6 | 策略研究证据 | [strategy-evidence-gate.md](strategy-evidence-gate.md) | AFML rollout、benchmark matrix、research spec、A 股 playbook 和各策略 README 分散说明晋级门槛 | 证据门禁保存强制集合，方法页只解释单项方法，策略 README 链接 evidence bundle | 待处理 |
| DOC7 | 外部框架状态 | [framework-support-matrix.md](framework-support-matrix.md)、[framework-integration-ledger.yml](framework-integration-ledger.yml) | ARCHITECTURE、adoption assessment、历史 release 文件和子仓 ledger 重复表达当前能力 | support matrix 表达当前能力，机器账本表达进度，评估和历史候选降级为 reference 或 archive | 本轮校正状态，后续继续去重 |
| DOC8 | 跨仓库产物契约 | [artifact-contracts.yml](artifact-contracts.yml)、[contracts.md](contracts.md) | research-contracts README、pipeline outputs、alpha signal 文档、portfolio contract 文档、qexec targets 文档重复字段 | 根层保存 owner 和交接字段，生产方与消费方只保存本仓校验和操作细节 | 待处理 |
| DOC9 | 质量与维护债 | [maintainability-governance.md](maintainability-governance.md)、机器账本 | code health、code size、submodule refactor、noqa、R3 和 namespace migration 混合当前事实与历史计划 | 当前预算进入机器账本，完成的专项计划降级为 reference，审计快照进入 archive | 进行中（第二批完成维护性历史计划归集） |
| DOC10 | 工作区命令与检查 | [workspace-maintenance.md](workspace-maintenance.md) | README、bootstrap、quality governance、release checklist 重复命令 | maintenance 保存完整命令，bootstrap 只保留首次安装，release checklist 只保留发布顺序 | 待处理 |
| DOC11 | 版本组合 | `print_version_matrix.py`、[version-matrix.md](version-matrix.md) | 文档中的本次提交静态行容易落后于 gitlink | 脚本生成现场状态，文档只保存带证据的已验证组合 | 本轮校正当前组合 |
| DOC12 | 风格因子说明 | [style-factors.md](style-factors.md)、[style-factor-technical-reference.md](style-factor-technical-reference.md) | 方法页、技术页和 experiments 下多份结果页交叉重复样本与限制 | 方法页面向研究读者，技术页面向维护者，实验页只保存一次封存结果 | 待处理 |
| DOC13 | 执行能力 | [current-capabilities.md](../quant-execution-engine/docs/current-capabilities.md) | 根 platform workflow、targets 文档、多个 broker smoke 手册和旧 readiness evidence 重复成熟度结论 | qexec 能力页表达当前状态，根层只表达文件交接，smoke 页面只保存操作步骤 | 待处理 |
| DOC14 | 港股恢复归档 | [archive/hk/README.md](archive/hk/README.md) | 历史 freeze、handoff 和恢复记录数量较多 | 已通过统一 archive 入口归集，继续保持历史文件不改写 | 已完成 |

## 优先处理的具体页面

### 第一批：状态冲突

- `strategy-boundary-refactor-roadmap.md`：从活动总路线图降级为 R0 至 R6 完成记录。
- `framework-integration-ledger.yml`：同步 Qlib 研究适配和 pipeline thinning 的当前状态。
- `portfolio-backtester/docs/accounting_execution_roadmap.md`：统一阶段 0 至 6 已完成与后续增强项的表述。
- `version-matrix.md`：让最新验证组合与当前 gitlink 一致。
- `strategy-pipeline/docs/strategy-catalog.md`：删除已经迁走的 next-open-to-high 旧归属说明。

### 第二批：维护性历史计划

- `r3-facade-removal-plan.md`：保留为历史执行蓝图，当前状态由策略边界完成记录提供。已完成。
- `noqa-clearing-plan.md`：保留审计结论，删除对已合并分支和外部 worktree 的当前行动指引。已完成。
- `code-health-audit.md`、`code-size-review.md`、`submodule-refactor-plan.md`：移入 archive 或改成短 reference，具体热点由机器账本生成。已移入 archive，archive README 已登记导航。
- `governance-index.md`：删除已经不存在的 `dev-metrics-consolidation-plan.md` 条目。已完成。

### 第三批：动态事实去重

- `docs/README.md` 不再保存 A 股资产覆盖行数，只链接数据 playbook。
- `strategy-pipeline/docs/playbooks/a-share-baseline.md` 不再复制 current contract 的完整静态数字。
- `market-data-platform/docs/a-share-research-profile.md` 从 current contract 读取发布状态，页面只解释资产角色。
- `version-matrix.md` 的最新现场组合由脚本输出，人工表只记录已验证证据。

### 第四批：主题入口瘦身

- 将 README、AGENTS、ARCHITECTURE 和 platform workflow 中重复的模块职责压缩为一处完整表述。
- 将策略生命周期从 pipeline 和 strategy-app 目录中移除，只保留到 `catalog.json` 的链接。
- 将产物字段定义留在 owner 契约文档，根层只保存跨仓库交接所需的最小字段集合。

## 不合并的文档

- ADR 保存决策背景和当时约束，不与当前操作文档合并。
- `docs/evidence/` 保存机器证据，不改写为当前说明。
- `docs/archive/` 和各仓 archive 保存历史原貌，不参与正文去重。
- 券商 smoke 手册按后端分开保留，因为前置条件、保护开关和操作风险不同。
- 策略实验结果按独立研究问题保留，不与方法说明合并。

## 完成标准

- 每个主题在 `docs/README.md` 中只有一个推荐权威入口。
- 所有 active 文档都能说明自身范围、owner 和事实来源。
- 当前状态不再从 archive、历史分支或带日期证据反向推断。
- 文档链接测试、入口文档风格测试和相关事实测试全部通过。
