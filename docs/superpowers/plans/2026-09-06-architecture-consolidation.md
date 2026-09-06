# 量化研发架构与仓库整合实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留选择性公开、public GitHub Actions、策略 IP 隔离和 `market-intel` 独立运行能力的前提下，把当前八个 submodule 从“每个职责一个仓库”逐步调整为“公开/私有边界由仓库承担，代码职责由 package 和契约承担”。

**Architecture:** 最终采用三个代码层和一个集成层：`quant-platform` 提供可公开分享的通用量化能力，`quant-research` 保存策略和研究 IP，`market-intel` 独立消费已发布 artifact 并负责报告、看板、投递和运维；`research-workspace` 保留为薄集成仓库，锁定版本组合、维护跨仓契约和发布清单。迁移采用增量方式，先建立契约和上下文边界，再按实际共同变更频率决定哪些仓库合并。

**Tech Stack:** Git submodule、GitHub Actions、Python/uv、现有 `research_contracts`、JSON Schema、公开 CLI、版本化文件 artifact、`AGENTS.md`、worktree + PR 流程。

**Spec:** `research-workspace/ARCHITECTURE.md`、`research-workspace/AGENTS.md`、`market-intel/docs/boundary-contract.md`、`market-intel/README.md`。

## Global Constraints

- 不把凭证、真实 provider 配置、私有数据、生产参数、策略 edge 或交易审计日志放入 public 仓库。
- `market-intel` 只能通过公开 CLI 和版本化 artifact 消费研究系统，不直接 import 研究仓库内部实现。
- `targets.json`、研究 snapshot、A 股当前资产契约等跨仓产物必须由生产方、消费方、顶层契约文档和测试一起变更。
- `research-workspace` 的 `main` 受保护；所有改动使用 `/home/richard/code/.worktrees/` 下的独立 worktree 和 PR。
- 在完成边界盘点和迁移演练前，不删除旧仓库、不删除旧 submodule、不批量重命名远端仓库。
- 每个阶段都必须有可独立运行的检查和明确的回滚方式。
- `market-intel` 继续作为独立应用仓库，不并入 `quant-platform` 或 `quant-research`。

---

## 目标结构

```text
quant-platform       public
  通用数据接口、研究框架、回测、编排、执行公共能力

quant-research       private
  策略身份、策略逻辑、专有 alpha、实验、模型选择、真实配置

market-intel         private / 独立应用
  市场上下文、报告、dashboard、飞书投递、调度、恢复

research-workspace   public / 薄集成层
  版本组合、跨仓契约、doctor、集成 smoke test、发布 manifest
```

第一阶段不要求立刻创建两个新仓库。先把现有仓库按上述四个盒子标注清楚；只有确认共同变更频繁、公开性一致、发布生命周期一致后，才执行真实合并。

| 当前仓库 | 第一阶段处理 | 目标归属 |
| --- | --- | --- |
| `market-data-platform` | 保持独立，列出公共接口和私有 provider | platform 的公共 data package + 私有运行配置 |
| `deep-learning-tick-data-prediction` | 区分通用模型与专有实验 | platform 公共部分 + research 私有部分 |
| `alpha-research` | 保持可独立测试 | platform 的 alpha/research package |
| `portfolio-backtester` | 先保持独立发布能力 | platform package，必要时长期独立 |
| `strategy-research` | 候选名 `strategy-registry` | research/registry |
| `strategy-app` | 候选名 `strategy-logic` | research/strategies |
| `strategy-pipeline` | 候选名 `strategy-orchestrator` | platform/orchestration |
| `quant-execution-engine` | 先保持审计和部署边界 | platform/execution 或长期独立 |
| `market-intel` | 保持独立，消费 artifact | 独立应用层 |
| `research-workspace` | 减薄职责 | 集成与发布层 |

## Phase 0：冻结当前基线

### Task 1：建立迁移 worktree 和基线记录

**Files:**
- Create: `docs/superpowers/plans/2026-09-06-architecture-consolidation.md`
- Create: `docs/evidence/architecture-migration-baseline-2026-09-06.md`

- [x] **Step 1: 创建 worktree**

```bash
cd /home/richard/code/research-workspace
git fetch github
git worktree add /home/richard/code/.worktrees/architecture-consolidation -b feat/architecture-consolidation github/main
```

- [x] **Step 2: 记录版本和 dirty 状态**

```bash
cd /home/richard/code/.worktrees/architecture-consolidation
git submodule status --recursive
git status --short --branch
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
```

- [x] **Step 3: 建立基线表**

记录每个仓库的：当前 commit、remote、public/private、owner、入口命令、生产方、消费方、真实数据/凭证情况和回滚方式。

- [x] **Step 4: 提交**

```bash
python scripts/run_workspace_tests.py
python scripts/run_quality_checks.py --profile hard
git add docs/superpowers/plans/2026-09-06-architecture-consolidation.md docs/evidence/architecture-migration-baseline-2026-09-06.md
git commit -m "docs: add architecture consolidation baseline"
```

**完成标准:** 当前八个 submodule、`market-intel` 和顶层工作区的版本状态可以从一份文档恢复。

### Task 2：建立 public/private 内容清单

**Files:**
- Create: `docs/governance/public-private-boundary-matrix.md`
- Modify: `docs/README.md`
- Modify: `docs/superpowers/plans/2026-09-06-architecture-consolidation.md`

本计划的 Task 2 验证命令已按执行时的可用 profile 规则修正：将不受支持的
`python scripts/run_quality_checks.py --profile docs` 更正为现有的
`python scripts/run_quality_checks.py --profile governance`。该修正是授权的执行裁定，保留实际执行命令。

- [x] **Step 1: 分类每个关键目录**

每项标记为 `PUBLIC_CORE`、`PRIVATE_RESEARCH`、`PRIVATE_RUNTIME` 或 `INTEGRATION_ONLY`。无法确认的内容暂按 `PRIVATE_RESEARCH` 处理。

- [x] **Step 2: 固定判定规则**

```text
公开后只暴露机制、不暴露 edge → PUBLIC_CORE
真实策略、特征组合、标签、模型选择、生产参数、provider → PRIVATE_RESEARCH / PRIVATE_RUNTIME
只负责锁版本、契约、集成检查 → INTEGRATION_ONLY
```

- [x] **Step 3: 验证并提交**

```bash
python scripts/run_quality_checks.py --profile governance
python scripts/workspace_doctor.py
git add docs/governance/public-private-boundary-matrix.md docs/README.md docs/superpowers/plans/2026-09-06-architecture-consolidation.md
git commit -m "docs: define public and private boundaries"
```

## Phase 1：先解决 AI 上下文和跨模块契约

### Task 3：建立任务级上下文 manifest

**Files:**
- Modify: `AGENTS.md`
- Create: `docs/governance/agent-context-boundaries.md`
- Modify: `docs/governance/README.md`
- Modify: `docs/evidence/maintainability/baseline-20260719-ty.json`
- Create: `scripts/context_manifest.py`
- Create: `tests/test_context_manifest.py`
- Modify: `docs/superpowers/plans/2026-09-06-architecture-consolidation.md`

- [x] **Step 1: 写失败测试**

```python
def test_alpha_manifest_includes_direct_contracts():
    result = build_manifest("alpha")
    assert "alpha-research" in result.repositories
    assert "portfolio-backtester" in result.direct_consumers
    assert "market-intel" not in result.default_context
```

- [x] **Step 2: 实现最小接口**

```python
def build_manifest(area: str) -> ContextManifest:
    """Return the explicit context manifest for one work area."""

def render_manifest(manifest: ContextManifest) -> str:
    """Render the manifest as agent-readable Markdown."""
```

初始区域为 `data`、`microstructure`、`alpha`、`portfolio`、`strategy`、`orchestration`、`execution`、`market-intel`。映射必须来自显式配置，不递归读取全仓库。

- [x] **Step 3: 补充各区域局部说明**

为 `alpha-research`、`portfolio-backtester`、`strategy-research`、`strategy-app`、`strategy-pipeline`、`market-intel` 写清职责、允许依赖、禁止依赖、契约文件和最小测试命令。

- [x] **Step 4: 验证并提交**

```bash
pytest tests/test_context_manifest.py -q
python scripts/context_manifest.py --task alpha
python scripts/context_manifest.py --task strategy
git add AGENTS.md docs/governance/agent-context-boundaries.md docs/governance/README.md \
  docs/evidence/maintainability/baseline-20260719-ty.json \
  scripts/context_manifest.py tests/test_context_manifest.py \
  docs/superpowers/plans/2026-09-06-architecture-consolidation.md
git commit -m "feat: add task-scoped agent context manifests"
```

**完成标准:** AI 小任务默认只读取一个区域；跨契约任务能列出 producer、contract、consumer 和测试。

### Task 4：登记跨仓 artifact owner

**Files:**
- Modify: `src/research_contracts/README.md`
- Modify: `src/research_contracts/__init__.py`
- Create: `src/research_contracts/contract_ownership.py`
- Modify: `src/research_contracts/smoke_contracts.py`
- Modify: `docs/contracts/README.md`
- Create: `docs/contracts/contract-ownership.yml`
- Modify: `docs/artifact-contracts.yml`
- Modify: `docs/evidence/maintainability/baseline-20260719-ty.json`
- Modify: `tests/test_artifact_contract_manifest.py`
- Create: `tests/test_contract_ownership.py`
- Modify: `docs/superpowers/plans/2026-09-06-architecture-consolidation.md`

执行裁定：`docs/artifact-contracts.yml` 和 `tests/test_artifact_contract_manifest.py` 是现有跨仓
artifact 明细的权威 registry 和契约测试。新增 ownership registry 作为覆盖文件 artifact 与
类型化输入的治理索引，由 `research_contracts` loader/validator 和现有 smoke 入口校验；两个 registry
重叠的 artifact 必须校验 producer、schema 和 consumers 一致。该扩展只登记 metadata，不修改
producer、consumer、artifact payload 或私有仓库行为。

Fix round 1 裁定：严格类型校验新增的 validator 和测试属于 Task 4 Python surface，必须同步现有
权威 maintainability baseline。该同步只更新生成统计，不改变治理阈值或其他仓库内容。

- [x] **Step 1: 登记至少这些 artifact**

`targets.json`、研究 snapshot、A 股当前资产清单、L2/alpha 信号产物、回测输入、`market-intel` 消费的正式策略产物。

- [x] **Step 2: 为每项登记字段**

`name`、`schema`、`producer`、`consumers`、`versioning`、`compatibility`、`test_command`、`rollback`。

- [x] **Step 3: 添加完整性测试并验证**

```python
def test_every_contract_has_one_producer_and_consumer():
    contracts = load_contract_ownership()
    assert all(item.producer for item in contracts)
    assert all(item.consumers for item in contracts)
```

```bash
python src/research_contracts/smoke_contracts.py
python scripts/run_workspace_tests.py
cd /home/richard/code/market-intel && uv run pytest -k contract
```

- [x] **Step 4: 提交**

```bash
git add src/research_contracts docs/contracts docs/artifact-contracts.yml \
  docs/evidence/maintainability/baseline-20260719-ty.json \
  tests/test_artifact_contract_manifest.py tests/test_contract_ownership.py \
  docs/superpowers/plans/2026-09-06-architecture-consolidation.md
git commit -m "docs: register cross-repository artifact ownership"
```

## Phase 2：命名和共同变更分析

### Task 5：冻结旧名到新名的迁移字典

**Files:**
- Create: `docs/governance/repository-naming-map.md`
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`

- [x] **Step 1: 固定候选名但不改远端**

```text
strategy-research → strategy-registry
strategy-app → strategy-logic
strategy-pipeline → strategy-orchestrator
deep-learning-tick-data-prediction → microstructure-models
```

`alpha-research`、`portfolio-backtester`、`quant-execution-engine`、`market-intel` 暂不改名。

- [x] **Step 2: 明确不同时改 namespace 和 CLI**

仓库名变化不等于 Python namespace 或 CLI 变化。先保留 `strategy_pipeline`、`strategy_app`、`ticknet`，namespace/CLI 迁移另建任务。

- [x] **Step 3: 搜索引用并分类**

```bash
rg -n "strategy-research|strategy-app|strategy-pipeline|deep-learning-tick-data-prediction" .
```

结果分成 URL、路径、文档、import、CLI、生产配置和历史记录；历史记录只加迁移说明，不改写事实。

- [x] **Step 4: 提交**

```bash
git add docs/governance/repository-naming-map.md README.md ARCHITECTURE.md
git commit -m "docs: define repository naming migration map"
```

### Task 6：分析策略仓库共同变更

**Files:**
- Create: `docs/evidence/strategy-repository-change-coupling.md`
- Create: `scripts/analyze_repository_coupling.py`
- Create: `tests/test_analyze_repository_coupling.py`
- Create: `tests/fixtures/strategy-commits.json`

执行裁定：示例测试通过 `fixtures("strategy-commits.json")` 读取确定性输入，因此测试 fixture
属于 Task 6 的必要文件。该文件只保存合成 Git 元数据，不保存研究数据、凭证或仓库内容。

- [x] **Step 1: 定义输出字段**

`repositories`、`period`、`co_change_count`、`contract_change_count`、`release_independence_count`、`recommended_action`、`evidence`。

- [x] **Step 2: 写解析器测试并实现**

```python
def test_report_separates_contract_and_local_changes():
    report = analyze_commits(fixtures("strategy-commits.json"))
    assert report[("strategy-research", "strategy-app")].contract_change_count == 2
```

```bash
python scripts/analyze_repository_coupling.py \
  --repositories strategy-research strategy-app strategy-pipeline \
  --since 12.months \
  --output docs/evidence/strategy-repository-change-coupling.md
pytest tests/test_analyze_repository_coupling.py -q
```

- [x] **Step 3: 按证据决策**

若共同变更主要是稳定 artifact 契约，继续独立仓并强化契约；若大量变更需要同一 PR 原子修改且公开性一致，才进入真实合并试点。

- [x] **Step 4: 提交**

```bash
git add scripts/analyze_repository_coupling.py tests/test_analyze_repository_coupling.py docs/evidence/strategy-repository-change-coupling.md
git commit -m "docs: measure strategy repository coupling"
```

## Phase 3：公共和私有仓库迁移试点

### Task 7：用 `portfolio-backtester` 做 `quant-platform` 公共试点

执行裁定（2026-09-06）：本任务只在当前 worktree 的普通目录 `quant-platform/` 中建立本地
staging tree，不创建新 Git 仓库、不配置 remote、不 push 或发布，也不更新 workspace gitlink。
由于普通目录不能承载独立仓库提交图，使用 `git fast-export` 对所选源码和测试做只读历史导出
演练，并在 staging tree 记录来源 commit、导出摘要和逐文件哈希；真正建仓时再 fast-import。
源仓当前 commit 没有 tag 且缺少 LICENSE，因此 tag 对比和公开发布保持阻塞，并在报告中记录。

**Files:**
- Create: 新仓库 `quant-platform/README.md`
- Create: 新仓库 `quant-platform/AGENTS.md`
- Create: 新仓库 `quant-platform/packages/`
- Create: 新仓库 `quant-platform/contracts/`
- Create: 新仓库 `quant-platform/.github/workflows/ci.yml`

- [x] **Step 1: 只迁移一个 vertical slice**

先迁移公共回测能力、一个最小 artifact contract 和合成示例数据，不同时搬 data、alpha、orchestration、execution。

- [x] **Step 2: 保留历史和 namespace**

使用历史保留迁移工具；迁移后用旧仓 tag 对比文件、测试、许可证和公开 API。Python namespace 暂不改变。

- [x] **Step 3: 配置无私有依赖的 public CI**

```yaml
name: public-ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv sync --locked --all-groups
      - run: uv run ruff check .
      - run: uv run pytest
```

- [x] **Step 4: 双轨验证**

旧仓和新仓运行同一组契约、回归和示例测试；比较公开 API、artifact schema、CLI 和报告结果。

- [x] **Step 5: 通过后才更新 workspace**

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
python scripts/run_workspace_tests.py
```

**完成标准:** 有一个未发布的本地 public CI 迁移样板，旧仓仍可作为回滚源；远端建仓、
fast-import、tag 和许可证确认不属于本地试点完成声明。

### Task 8：用一个真实策略做 `quant-research` 私有试点

执行裁定（2026-09-06）：先在 `/home/richard/code/.private-staging/quant-research` 建立本地
私有 Git staging tree，不创建 GitHub remote、不 push、不更新 workspace gitlink。选择
`DailyWatch20` 作为纵切面，保留现有 `strategy_app.daily_watch20` namespace，并记录
`strategy-research` 与 `strategy-app` 的源 commit。该试点已完成 source slice、私有目录、
provenance 和 rollback 记录；artifact 导出、`market-intel` 消费验证和远端私有仓创建仍是
后续门禁，不能据此宣称迁移完成。证据见
`docs/evidence/private-research-staging-2026-09-06.md`。

**Files:**
- Create: 新仓库 `quant-research/README.md`
- Create: 新仓库 `quant-research/AGENTS.md`
- Create: 新仓库 `quant-research/strategies/`
- Create: 新仓库 `quant-research/registry/`
- Create: 新仓库 `quant-research/experiments/`

- [x] **Step 1: 迁移一个完整策略纵切面（本地 staging）**

一起迁移 registry、策略逻辑、配置、实验索引和一个可审计 artifact，不先搬整个 `strategy-research`。

- [x] **Step 2: 固定私有目录（本地 staging）**

真实 feature 组合、label、universe、模型选择、production config、provider 配置、实验结果和失败实验记录必须留在 private repo。

- [ ] **Step 3: 只依赖 platform 稳定 API 和契约**

禁止 `market-intel` 直接 import `quant-research`；只把带有 schema 和 producer commit 的 artifact 交给它。

- [ ] **Step 4: 本地门禁和消费验证**

```bash
uv run pytest
python scripts/export_research_artifact.py \
  --strategy daily_watch20 \
  --output /tmp/daily_watch20-artifact
cd /home/richard/code/market-intel
uv run pytest -k contract
uv run a-share-daily doctor
```

**完成标准:** 一个真实策略可以从私有研究仓生成版本化 artifact，并被 `market-intel` 消费，研究实现没有进入 public platform。

## Phase 4：固定 market-intel 和 workspace 边界

### Task 9：把 `market-intel` 固定为 artifact consumer

**Files:**
- Modify: `market-intel/docs/boundary-contract.md`
- Modify: `market-intel/docs/contracts.md`
- Modify: `market-intel/AGENTS.md`
- Create: `market-intel/tests/test_research_artifact_boundary.py`
- Modify: `research-workspace/docs/contracts/contract-ownership.yml`

- [ ] **Step 1: 写边界测试**

```python
def test_market_intel_does_not_import_private_research():
    assert no_imports_from("quant_research")
    assert boundary_documented("versioned artifact")
```

- [ ] **Step 2: 补齐 artifact manifest**

每份产物必须有 `artifact_type`、`schema_version`、`producer_commit`、`strategy_id`、`as_of`、`created_at`、`quality_status` 和 `source_manifest`。

- [ ] **Step 3: 验证缺失、过期和不兼容版本 fail closed**

```bash
cd /home/richard/code/market-intel
uv run pytest tests/test_research_artifact_boundary.py -q
uv run pytest -k "contract or freshness or recovery"
```

- [ ] **Step 4: 先合并 market-intel，再更新 workspace**

遵守先子仓库、后顶层工作区的顺序。

### Task 10：把 `research-workspace` 减薄为集成层

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `ARCHITECTURE.md`
- Modify: `.gitmodules`
- Modify: `scripts/workspace_architecture.py`
- Modify: `scripts/workspace_doctor.py`
- Modify: `scripts/run_submodule_checks.py`
- Modify: `tests/test_workspace_architecture.py`
- Modify: 版本矩阵、release manifest 和相关文档

- [ ] **Step 1: 只保留四项职责**

版本组合、契约验证、集成 smoke test、生产发布 manifest。策略身份归 research，报告实现归 market-intel。

- [ ] **Step 2: 更新 doctor 和 architecture model**

检查 required repositories、commit manifest、契约版本兼容性和 market-intel 消费入口。

- [ ] **Step 3: 迁移完成后才减少 submodule**

新仓先通过原有 smoke checks，旧仓保留回滚 tag 和迁移说明，再更新 `.gitmodules`。

- [ ] **Step 4: 运行完整集成门禁**

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
python scripts/run_workspace_tests.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
```

**完成标准:** workspace 不再成为业务实现的第二份 owner，只记录可一起工作的版本。

## Phase 5：逐个 rename 和收尾

### Task 11：执行仓库 rename

**Files:**
- Modify: 各仓库 URL、路径、CI、生产配置和文档引用
- Modify: `research-workspace/.gitmodules`
- Create: 旧名称路径下的兼容指针文档

- [ ] **Step 1: 一次只 rename 一个**

建议顺序：`strategy-research`、`strategy-pipeline`、`deep-learning-tick-data-prediction`，最后评估 `strategy-app`。每次 rename 后等待 URL 重定向和 CI 稳定。

- [ ] **Step 2: 只改 repository name**

先不要同步改 Python namespace、CLI 或 artifact schema。

- [ ] **Step 3: 同步并验证**

```bash
git submodule sync --recursive
git submodule update --init --recursive
python scripts/workspace_doctor.py
python scripts/run_workspace_tests.py
rg -n "strategy-research|strategy-pipeline|deep-learning-tick-data-prediction" .
```

- [ ] **Step 4: 提交和回滚**

每个 rename 独立 PR、独立 commit；旧仓 README 保留指向新仓的短说明，失败时回到上一个已发布名称。

### Task 12：完成关闭清单和回滚演练

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `AGENTS.md`
- Modify: `docs/quality-governance.md`
- Modify: `docs/version-matrix.md`
- Modify: `docs/release-checklist.md`
- Modify: `market-intel/README.md`
- Create: `docs/evidence/architecture-migration-closure.md`

- [ ] **Step 1: 更新最终架构说明**

明确一句话：`platform 提供能力，research 保存研究 IP，market-intel 展示和投递，workspace 锁定可工作的版本组合`。

- [ ] **Step 2: 记录 AI 上下文策略**

默认按 package/任务 manifest 读取；只有公共 API、artifact contract、下游失败或用户明确要求时才扩大到 producer/consumer。

- [ ] **Step 3: 演练 artifact 和 production manifest 回滚**

确认旧版本仍可被 `market-intel` 消费，且 `/home/richard/code/production/current` 不会被失败发布切换。

- [ ] **Step 4: 运行最终门禁**

```bash
cd /home/richard/code/research-workspace
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
python scripts/run_workspace_tests.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
cd /home/richard/code/market-intel
uv run pytest
uv run ruff check .
uv run ty check
```

- [ ] **Step 5: 只有满足删除条件才移除旧 submodule**

新仓已有稳定 tag、所有消费者已切换、旧仓回滚 tag 已记录、doctor 不再依赖旧路径、market-intel contract 通过、生产 manifest 已切换并完成回滚演练。

## 推荐执行顺序

1. 基线和回滚安全网。
2. public/private 内容清单。
3. AI 上下文 manifest。
4. artifact owner 和契约目录。
5. 命名迁移字典。
6. 共同变更分析。
7. `portfolio-backtester` 的 `quant-platform` 公共迁移试点。
8. 一个真实策略的 `quant-research` 私有迁移试点。
9. 固定 `market-intel` 的 artifact consumer 边界。
10. 减薄 `research-workspace`。
11. 逐个执行仓库 rename。
12. 回滚演练和关闭旧边界。

## 明确不做

- 不为了控制 AI 上下文而继续拆更多仓库。
- 不把 `market-intel` 并入公共框架。
- 不在同一变更中同时改 repository name、Python namespace、CLI 和 artifact schema。
- 不把真实策略、provider、凭证、生产配置或失败实验搬进 public `quant-platform`。
- 不一次性迁移所有历史；先用一个公共 vertical slice 和一个私有策略 vertical slice 验证流程。
