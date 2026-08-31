# Unify Data Lifecycle Terminology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一的数据生命周期、研究目录和代码目录术语，并在不破坏历史路径的前提下同步顶层与外部 data README。

**Architecture:** 第一阶段只统一文档语义和迁移规则，不批量重命名大型数据目录。父仓库文档作为跨仓规范，`/home/richard/data/README.md` 作为数据根目录操作说明；现有 manifest、receipt、current alias 和 retention planner 继续作为实际控制面。

**Tech Stack:** Markdown、Git worktree、现有 market-data-platform retention planner。

**Spec:** `docs/data-lifecycle-terminology.md`

## Global Constraints

- 不直接重命名或删除 current、rollback、published、staging 或 archive 下的大型数据。
- 数据删除必须以 manifest、receipt、引用检查和 retention 报告为依据。
- 历史路径在消费者迁移前必须保留兼容入口或明确迁移说明。
- 文档正文使用中文标点，命令、路径、配置键和 API 名称保持原样。
- 顶层 `main` 只能通过独立 worktree、PR 合并更新。

### Task 1: Add the cross-repository terminology specification

**Files:**
- Create: `docs/data-lifecycle-terminology.md`

- [x] **Step 1: Write the lifecycle definitions and deletion guardrails**
- [x] **Step 2: Verify the document covers data, research, code, and legacy migration terms**
- [x] **Step 3: Commit the specification**

### Task 2: Align the external data-root README

**Files:**
- Modify: `/home/richard/data/README.md`

- [x] **Step 1: Add the canonical vocabulary table**
- [x] **Step 2: State that names do not grant deletion authority**
- [x] **Step 3: Document the current SCLT archive and archived replacement campaign locations**
- [x] **Step 4: Check that existing current/staging/retention warnings remain intact**

### Task 3: Add navigation and verify documentation consistency

**Files:**
- Modify: `docs/README.md`

- [x] **Step 1: Add the terminology document to the documentation index**
- [x] **Step 2: Run Markdown link and repository documentation checks**
- [x] **Step 3: Review the diff for accidental path or API changes**
- [x] **Step 4: Commit the documentation integration**

### Task 4: Publish through the normal parent-repository workflow

**Files:**
- No additional source files.

- [x] **Step 1: Run `python scripts/workspace_doctor.py`**
- [x] **Step 2: Run `python scripts/run_quality_checks.py --profile hard`**
- [ ] **Step 3: Push the feature branch and open a PR**
- [ ] **Step 4: Merge the PR and remove the temporary worktree**
