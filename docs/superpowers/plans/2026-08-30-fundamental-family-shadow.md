# 基本面家族影子实验实施计划

规格：`docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## 全局约束

- 不得改变生产预设、生产特征模式或自动晋升状态。
- Value、Quality、Growth、风格控制和基金背景属于相互独立的命名家族。
- Quality 和 Growth 必须复用现有严格 PIT 实现，不得增加重复计算路径。
- P0 是当前生产特征锚点。T0 是移除 `value_yield` 和 `earnings_yield` 后的 P0。
- 固定组合正好包括 P0、T0、V、Q、G、VQ、VG、QG、VQG 和 VQG_F。VQG_F 仅供辅助分析。
- 固定周期为 5 日诊断、20 日主周期和预注册的 60 日挑战周期。
- 所有周期专属切分保护必须使用匹配的标签成熟期。截止 2026-08-30 的历史数据标记为 `retrospective_diagnostic`，不能作为新的样本外数据。
- 缺失、非正、非有限、未来日期、重复或冲突的源数据必须失败关闭，或生成 blocked 凭证。
- 跨仓库代码只能使用公开 owner API 和稳定契约。不要导入供应商私有模块，也不要重新打开已经关闭的基金拥挤度分支。
- 所有新研究输出继续保持 `production_eligible=false` 和 `automatic_promotion_allowed=false`。

## 任务

### 任务 1：A1 market-data-platform 估值输入

检查当前公开 A 股和 DailyWatch20 加载器。如果已经提供 `ps_ttm`，在不创建第二个加载器的前提下补充缺失契约和回归测试。否则通过现有已发布数据 API 暴露它。测试缺失列、日期边界、股票与日期唯一性，以及 `pb`/`pe_ttm` 兼容性。不要改变生产资产语义。

### 任务 2：A2 alpha-research 家族契约

增加公开 alpha 模块，提供家族常量和元数据。实现 PB、PE_TTM 和 PS_TTM 的有限正值 Value 收益率，并保留现有生产收益率名称。复用规范 PIT Quality/Growth 特征常量和构建器。增加 P0/T0 辅助函数、精确的家族成员检查，以及不可变的 5/20/60 日周期配置。先增加针对性测试，并确保没有可选框架时仍可导入包。

### 任务 3：B strategy-research V/Q/G 消融

创建 `experiments/fundamental_family_shadow/`，包含冻结配置、排除基金背景的精确主组合矩阵、20 日主周期和 5 日诊断配置、统一评估键和交集检查、回溯证据分类，以及读取公开特征表的确定性运行器。可用时将模型和组合计算委托给现有公开 API。增加冻结组合、统一键、缺失家族列、周期语义、blocked 凭证和生产隔离测试。

### 任务 4：C 慢周期和基金辅助分析

为实验增加预注册的 60 日配置以及匹配的 purge/embargo。VQG_F 只能作为辅助组合。完整 vintage 梯度不可用时，必须明确记录基金来源，并标记为 `revision_safe=false`。增加测试，防止基金背景成为主组合或生产可用组合，也防止历史数据行被标记为新的 OOS。

### 任务 5：D 工作区集成

更新工作区导航、路线图和证据文档，指向已实现的实验及其当前仅供研究的生命周期。记录 owner 提交和验证命令，不要声称远端 CI 已通过。增加或更新路径、生产不可变性和跨仓库边界检查。不要推进目录生命周期或生产配置。

## 验证

- Run each owner repository's focused tests and its documented quality checks where dependencies permit.
- Run the strategy-research full test suite after Tasks 3–4.
- Run workspace doctor, relevant contract/boundary checks, and the workspace tests after Task 5.
- Report any unavailable command or pre-existing failure explicitly.
