# Map Legacy Data Paths Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立现有数据目录到统一生命周期目录的可审查映射，并只执行已经有兼容入口和完整凭证支持的安全迁移。

**Architecture:** 映射文档是跨仓库的语义来源，数据根目录 README 保留实际物理布局和操作说明。第一阶段只记录混合目录的逻辑拆分与迁移状态，不批量重命名或删除数据；后续迁移必须逐项通过引用、凭证、锁和 retention 检查。

**Tech Stack:** Markdown、Git worktree、现有 data README、market-data-platform lifecycle inventory。

**Spec:** `docs/data-lifecycle-terminology.md`

## Global Constraints

- 不直接改写 `current`、`latest`、`rollback` 或生产读取路径。
- 未完成的 `staging` 任务不得迁移或删除。
- 混合目录必须先按子目录或资产类型拆分，不能仅按父目录名称判断。
- 外部 `/home/richard/data` 只更新说明或已确认安全的归档，不纳入 Git。
- 顶层 `main` 只能通过 worktree 和 PR 更新。

### Task 1: Inventory current and legacy paths

**Files:**
- Create: `docs/data-path-migration-map.md`

- [x] **Step 1: Record canonical mappings for existing physical paths**
- [x] **Step 2: Mark mixed paths as review-required instead of renaming them wholesale**
- [x] **Step 3: Record owners, consumers, and migration gates**

### Task 2: Align the external data-root instructions

**Files:**
- Modify: `/home/richard/data/README.md`

- [x] **Step 1: Link the versioned mapping document**
- [x] **Step 2: Add the current mapping status and no-delete rule**
- [x] **Step 3: Preserve existing production/current/staging warnings**

### Task 3: Validate and publish

**Files:**
- Modify: `docs/README.md`

- [x] **Step 1: Add the mapping document to the documentation index**
- [x] **Step 2: Run documentation and governance checks**
- [ ] **Step 3: Commit, push, open and merge a PR**
- [ ] **Step 4: Remove the temporary worktree and branch**
