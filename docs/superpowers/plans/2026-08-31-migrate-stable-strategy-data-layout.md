# 稳定策略数据布局迁移实施计划

> 面向智能体执行者：必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行本计划。步骤使用复选框（`- [ ]`）跟踪。

目标：将三个稳定策略数据命名空间移动到规范的 `published/` 位置，同时保留现有路径作为可逆的兼容别名。

架构：规范目录成为数据的物理 owner。观察期间，现有 `strategy_outputs/...` 和 `strategy_inputs/...` 路径继续作为符号链接，使当前生产读写方无需破坏性变更即可继续工作。迁移凭证记录源路径、目标路径、哈希、别名和回滚步骤。本任务不修改生产发布。

技术栈：Git、POSIX 符号链接、JSON 凭证、Markdown 契约和现有 Python 数据路径审计。

规格：`docs/data-path-breaking-change-register.md` 和 `docs/data-lifecycle-terminology.md`

## 全局约束

- 本次迁移保持 `market-intel` 和 `strategy-pipeline` 生产代码不变。
- 不删除旧路径，将其保留为兼容别名。
- 不改变任何 `latest` 目标或生产发布别名。
- 在 Git 之外的凭证中记录迁移前后的文件清单和 SHA-256 摘要。
- 后续代码默认值切换必须先完成一次完整影子周期、dry-run、契约检查和两个观察周期。

### 任务 1：扩展迁移契约

文件：
- Modify: `docs/data-path-breaking-change-register.md`
- Modify: `docs/data-path-migration-map.md`

- [x] 增加规范目标路径，并明确说明旧路径是兼容别名。
- [x] 记录回滚步骤，只有停止生产方后，才用记录的原始目录替换别名。
- [x] 增加观察门禁，并说明本任务不晋升生产代码。

### 任务 2：验证迁移凭证

**Files:**
- Create outside Git: `/home/richard/data/market-data-platform/metadata/lifecycle/migrations/stable-strategy-layout-20260831.json`

- [x] 记录源路径和目标路径、源和目标文件数量、字节总数、每棵目录树的文件列表 SHA-256、当前别名目标以及 `deletion_authorized: false`。
- [x] 迁移后重新运行只读数据路径审计，并记录输出路径。

### 任务 3：验证兼容性

**Files:**
- Test: existing `tests/test_data_path_audit.py`

- [x] 运行数据路径审计测试。
- [x] 解析每个旧别名，确认它与规范目标访问相同的 `latest` 和凭证文件。
- [x] 确认父仓库干净，生产发布目录未被修改。

### 任务 4：提交并发起评审

- [ ] 在 `feat/migrate-stable-strategy-data-layout` 上提交文档改动。
- [ ] 推送分支并创建 PR。本任务不要合并，也不要晋升生产。
