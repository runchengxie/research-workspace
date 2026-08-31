# Implement Data Path Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将旧路径映射落实为可重复执行的只读审计工具、机器可读清单和安全迁移前检查报告。

**Architecture:** 顶层脚本只扫描指定数据根目录，不修改文件，不推断删除权限。它根据固定映射表输出每个路径的规范语义、状态、文件数、字节数以及迁移动作；清单写入数据根目录的生命周期 metadata，文档继续说明人工复核门禁。

**Tech Stack:** Python 标准库、JSON、pytest、Markdown。

**Spec:** `docs/data-path-migration-map.md`

## Global Constraints

- 默认只读扫描，禁止脚本执行移动、删除或修改 alias。
- 不跟踪 `/home/richard/data` 中的生成清单和大型数据。
- `current`、`latest`、`rollback` 和存在活动 receipt 的路径必须标为保护或复核。
- 混合目录只能报告为 `拆分待审`，不能自动改名。
- 所有代码改动使用独立 worktree 和 PR 合入 `main`。

### Task 1: Define audit behavior with tests

**Files:**
- Create: `tests/test_data_path_audit.py`
- Create: `scripts/data_path_audit.py`

- [x] **Step 1: Write tests for canonical, mixed, and missing paths**
- [x] **Step 2: Run the focused tests and verify they fail because the scanner is absent**
- [x] **Step 3: Implement the read-only scanner and JSON output**
- [x] **Step 4: Run focused tests and verify they pass**

### Task 2: Generate the current data-root inventory

**Files:**
- Create outside Git: `/home/richard/data/market-data-platform/metadata/lifecycle/path-audit-20260831.json`
- Modify: `/home/richard/data/README.md`

- [x] **Step 1: Run the scanner against the actual data root**
- [x] **Step 2: Verify counts and byte totals against `du`**
- [x] **Step 3: Document the generated inventory and its read-only nature**

### Task 3: Publish and verify

**Files:**
- Modify: `docs/README.md`
- Modify: `docs/data-path-migration-map.md`

- [x] **Step 1: Link the audit tool and generated inventory contract**
- [x] **Step 2: Run focused tests, diff checks, and hard quality checks**
- [ ] **Step 3: Commit, push, open and merge a PR**
- [ ] **Step 4: Remove the temporary worktree and branch**
