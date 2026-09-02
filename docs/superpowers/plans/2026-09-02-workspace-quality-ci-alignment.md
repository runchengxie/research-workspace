# Workspace Quality and CI Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正工作区测试入口和质量门禁中的已知错误，统一 public/private 仓库的 GitHub Actions 策略，并让说明文档、测试与实际仓库状态保持一致。

**Architecture:** 顶层继续作为跨仓库治理层，各子仓拥有自己的本地质量门禁。public 仓库默认运行轻量 GitHub Actions，private 仓库默认关闭远端 CI。顶层集成测试必须基于当前 gitlink 组合，独立仓库的 `[tool.uv.sources]` 继续服务 standalone 安装，但不得静默改变 workspace 集成测试的依赖版本。

**Tech Stack:** Python 3.12、pytest、Ruff、ty、uv、Git submodule、GitHub Actions、Bash。

**Spec:** `docs/quality-governance.md`、`docs/documentation-style.md`、本轮用户确认的方案 A。

## Global Constraints

- 中文说明使用中文标点和直接表达。
- 保留必要的命令、路径、配置键、包名和 API 名称。
- public 仓库默认启用 GitHub Actions。
- private 仓库默认关闭 GitHub Actions，例外需要说明原因、范围和资源成本。
- 本地 pre-push 继续承担完整门禁，公开 Actions 优先调用仓库自己的权威检查入口。
- 修改行为时先补回归测试，再修改实现。
- 历史 archive/evidence 不做机械润色。

---

### Task 1: 修正根仓质量脚本假绿

**Files:**
- Modify: `tests/test_run_submodule_checks.py`
- Modify: `scripts/run_submodule_checks.py`
- Create or modify: `tests/test_check_script.py`
- Modify: `scripts/check.sh`
- Modify: `docs/script-lifecycle.yml`

**Interfaces:**
- `run_planned_commands(..., fail_fast=True)` 只在第一条错误结果后停止。
- `scripts/check.sh` 任一门禁失败都返回非零，`full` 实际执行子模块完整门禁。

- [ ] 写 `fail_fast` 回归测试，覆盖成功后继续与失败后停止两种情况。
- [ ] 运行测试并确认当前实现失败。
- [ ] 修正 `run_planned_commands`。
- [ ] 写 `check.sh` 失败传播测试。
- [ ] 运行测试并确认当前脚本失败。
- [ ] 修正 `check.sh`，同步脚本生命周期说明。
- [ ] 运行聚焦测试。

### Task 2: 统一 GitHub Actions 政策和根仓事实

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/quality-governance.md`
- Modify: `docs/workspace-maintenance.md`
- Modify: `docs/README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `CODEOWNERS`
- Modify: `.github/pull_request_template.md`
- Modify: `tests/test_documentation_entrypoints.py`
- Modify: `tests/test_docs_links.py`
- Modify: `tests/test_root_quality.py`

**Interfaces:**
- 根仓文档明确 public/private 默认 Actions 策略。
- 根仓当前活动 workflow 与文档一致。
- 子模块数量统一为八个。

- [ ] 更新事实测试，移除所有 Actions 均停用的旧假设。
- [ ] 修正文档和导航中的六仓、七仓遗留。
- [ ] 扩大链接测试入口范围并加入 `strategy-research`。
- [ ] 更新 CODEOWNERS 和 PR 模板的八仓范围。

### Task 3: 把 CI 默认政策写入八个子仓

**Files:**
- Modify each submodule `AGENTS.md`
- Modify each available `docs/testing.md` or `docs/quality-governance.md`
- Modify entry README only where current CI status is useful to users
- Disable `alpha-research/.github/workflows/pr-light.yml`

**Interfaces:**
- public: `deep-learning-tick-data-prediction`、`portfolio-backtester`、`quant-execution-engine` 默认启用远端 CI。
- private: `market-data-platform`、`alpha-research`、`strategy-app`、`strategy-pipeline`、`strategy-research` 默认关闭远端 CI。

- [ ] 每个仓库的 `AGENTS.md` 加入统一默认政策。
- [ ] public 仓测试文档说明活动 workflow 与本地完整门禁的分工。
- [ ] private 仓测试文档说明远端 CI 默认关闭和例外登记要求。
- [ ] 关闭 alpha 当前活动 workflow，并同步其文档。

### Task 4: 收紧测试与静态检查盲区

**Files:**
- Modify: root `pyproject.toml`
- Modify: root quality tests
- Modify selected submodule `pyproject.toml` and quality docs

**Interfaces:**
- 根 Ruff target 与 Python 3.12 对齐。
- 根 `ty` 以目录范围为主，减少新增文件漏检。
- `strategy-pipeline` 逐步缩小整包 `Any`。
- `quant-execution-engine` 把 unresolved-import 例外缩到可选 broker 适配器。

- [ ] 先补配置行为测试。
- [ ] 对齐根仓 Ruff/ty 范围。
- [ ] 为 pipeline 和 qexec 建立更窄的类型例外。
- [ ] 保留必要的可选依赖运行路径。

### Task 5: 依赖审计、coverage 与非 Python 检查

**Files:**
- Modify quality scripts/configuration and corresponding docs/tests.

**Interfaces:**
- `pip-audit` 的文档只声明真实安装和真实执行状态。
- coverage 使用风险分层和 ratchet，不设置跨仓统一百分比。
- Bash 和 Actions YAML 变更可由 ShellCheck、shfmt、actionlint 检查。

- [ ] 修正 `pip-audit` 文档失真。
- [ ] 为缺失依赖审计能力的仓库补依赖或明确例外。
- [ ] 建立 coverage ratchet 入口。
- [ ] 为 Shell/YAML 增加轻量检查。

### Task 6: 版本组合与维护性收口

**Files:**
- Modify version-resolution checks and docs.
- Modify `docs/version-matrix.md`.
- Refactor only selected high-risk hotspots with focused tests.

**Interfaces:**
- workspace 集成测试必须明确使用当前 gitlink 组合。
- standalone pin 差异继续可见，但不得影响 workspace 集成测试。
- 维护性重构继续使用现有 ratchet。

- [ ] 增加 workspace 测试环境与 gitlink 组合一致性检查。
- [ ] 让版本矩阵展示八个 submodule，并显示关键 standalone pin 差异。
- [ ] 优先处理 `strategy-pipeline`、`market-data-platform`、`quant-execution-engine` 的高风险热点。
- [ ] 每次热点拆分都以现有聚焦测试和维护性 ratchet 为验收条件。
