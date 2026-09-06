# Workspace Documentation Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the top-level workspace and all eight submodule documentation systems around task-oriented navigation, lifecycle boundaries, AI context limits, and compatible legacy paths.

**Architecture:** Each repository remains the owner of its internal documentation. The top-level repository owns cross-repository rules and links only. Documentation bodies move into semantic directories, old paths become short `superseded` pointers, and each repository is validated and committed independently before the superproject updates its gitlinks.

**Tech Stack:** Markdown, Git submodules, Python/pytest documentation checks, repository-local quality commands, `rg`, and `git worktree`.

**Spec:** `docs/superpowers/specs/2026-09-06-workspace-documentation-information-architecture-design.md`

## Global Constraints

- Root `README.md` contains only positioning, quick start, boundaries, and shortest documentation routes.
- Every repository keeps one `docs/README.md` as its documentation navigation entry.
- Current facts have one authoritative source; Markdown explains and links to machine-readable facts.
- Moved documents retain short compatibility pointers at their old paths.
- Do not change public APIs, schemas, `catalog.json`, `targets.json`, production paths, evidence hashes, or historical semantics.
- Do not copy private strategy content or real data into public `strategy-pipeline`.
- Active navigation must not recursively enumerate archive, evidence, design, or plan materials.
- All repository changes happen in isolated worktrees and repository-specific branches.

---

### Task 1: Add shared documentation migration rules and validation contract

**Files:**
- Modify: `docs/documentation-lifecycle.md`
- Modify: `docs/documentation-style.md`
- Modify: `AGENTS.md`
- Modify: `tests/test_docs_links.py`
- Modify: `tests/test_documentation_entrypoints.py`
- Create: `docs/templates/superseded-document.md`

**Interfaces:**
- Produces the canonical metadata fields, pointer format, active-navigation rules, and validation expectations consumed by all later repository migrations.
- The pointer template must use `status: superseded`, `source_of_truth: no`, and `superseded_by`.

- [ ] **Step 1: Write failing tests for the shared pointer and navigation rules**

Add tests that discover Markdown files under the top-level active documentation set and assert that a superseded pointer contains a relative replacement link, does not contain a second long-form body, and has the required metadata fields. Add a test that each active category index is linked from `docs/README.md`.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py -q`

Expected: FAIL because the shared template and category indexes do not yet exist.

- [ ] **Step 3: Add the template and update lifecycle/style rules**

Document the common metadata block, pointer shape, directory meanings, maximum recommended page scope, and AI reading order. Keep the rules repository-neutral so submodules can link to them without inheriting top-level ownership.

- [ ] **Step 4: Update top-level validation**

Make link checks cover nested documentation directories while excluding submodule working trees. Add checks for broken relative links, missing replacement targets, and active indexes that point into lifecycle-only directories without an explicit reason.

- [ ] **Step 5: Run focused tests and inspect the diff**

Run: `pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py -q`

Expected: PASS for the new shared contract and no unrelated test changes.

- [ ] **Step 6: Commit the shared contract**

```bash
git add AGENTS.md docs/documentation-lifecycle.md docs/documentation-style.md docs/templates/superseded-document.md tests/test_docs_links.py tests/test_documentation_entrypoints.py
git commit -m "docs: define shared documentation migration rules"
```

### Task 2: Reorganize top-level `research-workspace` documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/README.md`
- Move/rewrite: top-level architecture, operations, contracts, governance, research, and reference pages according to the spec
- Create: `docs/architecture/README.md`
- Create: `docs/operations/README.md`
- Create: `docs/contracts/README.md`
- Create: `docs/governance/README.md`
- Create: `docs/research/README.md`
- Create: `docs/reference/README.md`
- Create: short superseded pointers at every moved active path

**Interfaces:**
- Consumes the rules from Task 1.
- Produces the canonical top-level navigation used by all submodule entrypoints and AI agents.

- [ ] **Step 1: Build a source-to-target migration map**

Use `rg --files docs -g '*.md'` and link extraction to classify each active page. Record each source path, target path, lifecycle, owner, audience, and replacement target in the plan branch before moving files.

- [ ] **Step 2: Rewrite the root and top-level indexes**

Reduce root `README.md` and `AGENTS.md` to positioning, repository boundaries, shortest checks, documentation reading order, and links. Make `docs/README.md` a task table with links only to category indexes and a small set of cross-repository authorities.

- [ ] **Step 3: Move and rewrite active top-level pages**

Place architecture and ADR navigation under `docs/architecture/`, setup and release workflows under `docs/operations/`, cross-repository contracts under `docs/contracts/`, quality/version/lifecycle pages under `docs/governance/`, research methodology and evidence gates under `docs/research/`, and stable terminology/framework references under `docs/reference/`. Replace repeated status tables with links to manifests, catalogs, and scripts.

- [ ] **Step 4: Add compatibility pointers**

At each old path that remains externally referenced, replace the old body with a short pointer using the shared metadata and replacement link. Do not modify archived evidence or hash-bound records.

- [ ] **Step 5: Run top-level documentation validation**

Run: `pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py tests/test_workspace_doctor.py -q`

Expected: PASS with all active links resolving and no old path containing a duplicate body.

- [ ] **Step 6: Commit the top-level migration**

```bash
git add README.md AGENTS.md docs tests
git commit -m "docs: reorganize workspace documentation"
```

### Task 3: Reorganize `strategy-research` documentation and research navigation

**Files:**
- Repository: `/home/richard/code/strategy-research`
- Modify: `README.md`, `AGENTS.md`, `docs/README.md`
- Move/rewrite: `docs/architecture.md`, lifecycle, evidence, experiment, artifact, and governance pages into semantic subdirectories
- Modify/create: `research/strategies/*/README.md`, `research/experiments/*/README.md`, and local archive/evidence indexes where needed
- Create: category README files and superseded pointers

**Interfaces:**
- Keeps `catalog.json` as the sole lifecycle authority.
- Keeps strategy identity under `research/strategies/` and experiment identity under `research/experiments/`.

- [ ] **Step 1: Create a strategy-research worktree from `origin/main`**

Run: `git -C /home/richard/code/strategy-research fetch origin && git -C /home/richard/code/strategy-research worktree add /home/richard/code/.worktrees/strategy-research-docs -b feat/docs-reorganization origin/main`

- [ ] **Step 2: Inventory all 282 Markdown files and classify default context**

Use `rg --files -g '*.md'` and classify files into current docs, strategy identity, experiment records, evidence, archive, and superpowers. Do not move lifecycle directories into lifecycle-named folders.

- [ ] **Step 3: Rewrite the repository entrypoints**

Make `README.md`, `AGENTS.md`, and `docs/README.md` point to `catalog.json`, the strategy and experiment indexes, and one relevant category page per task. Remove duplicated strategy lifecycle prose from secondary pages.

- [ ] **Step 4: Move current docs and add pointers**

Use `docs/architecture/`, `docs/governance/`, `docs/guides/`, `docs/reference/`, and `docs/research/` for current documentation. Keep strategy and experiment identity in `research/`; archive historical research under `research/archive/` and evidence under `research/evidence/`. Keep old paths as short pointers.

- [ ] **Step 5: Validate strategy ownership and links**

Run: `uv run --project strategy-research --extra dev python -m pytest tests -q`

Also run the repository’s documentation/link check if present and `rg -n "catalog.json|strategy-lifecycle|evidence-profiles" README.md AGENTS.md docs research` to confirm every lifecycle reference resolves to the authority.

- [ ] **Step 6: Commit and merge the submodule change**

```bash
git -C /home/richard/code/.worktrees/strategy-research-docs add README.md AGENTS.md docs research
git -C /home/richard/code/.worktrees/strategy-research-docs commit -m "docs: reorganize strategy research documentation"
```

Push and merge this submodule branch before updating the top-level gitlink.

### Task 4: Reorganize data and research producer documentation

**Repositories:** `market-data-platform`, `deep-learning-tick-data-prediction`, `alpha-research`

**Files:**
- Each repository’s `README.md`, `AGENTS.md`, and `docs/README.md`
- Each repository’s current docs moved into `architecture/`, `concepts/`, `guides/`, `operations/`, `reference/`, `research/`, `archive/`, or `evidence/` as applicable
- Superseded pointers for moved pages

**Interfaces:**
- `market-data-platform` remains the authority for data asset production and data contracts.
- `deep-learning-tick-data-prediction` separates FI-2010 archive from real-data next-day research.
- `alpha-research` remains the authority for alpha features, models, signals, and robustness evidence.

- [ ] **Step 1: Create one isolated worktree per repository**

Use each repository’s `origin/main` and branches named `feat/docs-reorganization` under `/home/richard/code/.worktrees/`.

- [ ] **Step 2: Reorganize `market-data-platform`**

Separate asset contracts and data terminology from ingestion/publication operations, quality audits, provider integration, and historical migration records. Keep manifests and schema files as authoritative facts. Update its local entrypoints and add compatibility pointers.

- [ ] **Step 3: Validate `market-data-platform`**

Run the repository’s documented lint, typecheck, test, and documentation checks. Confirm that all commands in the rewritten docs match `--help` output or tests.

- [ ] **Step 4: Reorganize `deep-learning-tick-data-prediction`**

Place project status and operational run instructions under `operations/`, model/data boundaries under `architecture/` and `concepts/`, next-day guides under `guides/nextday/`, active experiments under `research/`, and papers/FI-2010/retired notebooks under reference or archive. Keep current numerical conclusions in the project status authority only.

- [ ] **Step 5: Validate `deep-learning-tick-data-prediction`**

Run: `pre-commit run --all-files` and `python scripts/check.py`

Confirm that tests do not require real data and that archived FI-2010 material is not linked as current next-day evidence.

- [ ] **Step 6: Reorganize `alpha-research`**

Keep research methods under `concepts/`, templates under `guides/`, artifact contracts under `reference/`, and testing/development under `operations/`. Move migration history to archive/reference pointers. Remove repeated orchestration, portfolio, and execution descriptions.

- [ ] **Step 7: Validate and commit all three repositories**

Run each repository’s documented full or release-quality check. Commit each repository separately with a message scoped to its documentation migration, push and merge each branch, and record the resulting commit IDs for Task 7.

### Task 5: Reorganize portfolio, application, and pipeline documentation

**Repositories:** `portfolio-backtester`, `strategy-app`, `strategy-pipeline`

**Files:**
- Each repository’s `README.md`, `AGENTS.md`, and `docs/README.md`
- Current docs moved into semantic category directories
- Superseded pointers for moved pages

**Interfaces:**
- `portfolio-backtester` owns general portfolio accounting, costs, capacity, risk, and execution simulation.
- `strategy-app` owns strategy-specific pure calculations and frozen contracts.
- `strategy-pipeline` owns generic orchestration, artifacts, publication, receipts, and `targets.json`.

- [ ] **Step 1: Create isolated worktrees**

Create one worktree per repository from `origin/main`, using separate branches under `/home/richard/code/.worktrees/`.

- [ ] **Step 2: Reorganize `portfolio-backtester`**

Split concepts for accounting, portfolio construction, costs, capacity, risk, and execution semantics. Put onboarding and run procedures in guides/operations, API/config/artifact details in reference, and completed roadmaps or audit snapshots in archive/reference.

- [ ] **Step 3: Reorganize `strategy-app`**

Separate application catalog and owner boundaries, operational quality gates and weekly division of labor, playbooks, and strategy-specific publication documents. Keep historical migrations and legacy replay records out of active navigation.

- [ ] **Step 4: Reorganize `strategy-pipeline`**

Separate control-plane concepts, owner integration guides, run/output operations, and API/config/CLI reference. Remove any strategy-specific or private-provider material from public active docs. Preserve generic `targets.json` and publication contract authority.

- [ ] **Step 5: Validate and commit each repository**

Run the documented checks for each repository. For `strategy-pipeline`, run `uv run --with pytest pytest`, `uv run ruff check src tests scripts`, `python scripts/dev/public_surface_export.py --output /tmp/strategy-pipeline-public`, and `python scripts/dev/public_readiness.py --strict`. Push and merge each submodule branch and record commit IDs.

### Task 6: Reorganize execution documentation

**Repository:** `quant-execution-engine`

**Files:**
- `README.md`, `AGENTS.md`, `docs/README.md`
- Current execution, broker, CLI, configuration, targets, audit, readiness, and migration pages
- New category indexes and superseded pointers

**Interfaces:**
- High-risk operations must retain explicit dry-run, safety switch, credential, rollback, and audit requirements.
- Current capability status is separate from historical readiness evidence.

- [ ] **Step 1: Create an isolated worktree**

Create `/home/richard/code/.worktrees/quant-execution-engine-docs` from `origin/main` on `feat/docs-reorganization`.

- [ ] **Step 2: Move and rewrite execution docs**

Place execution model, target resolution, and audit boundaries under architecture/concepts; local preview, broker smoke, release, and recovery under operations; CLI, configuration, targets, and capability matrix under reference. Archive completed readiness and migration records.

- [ ] **Step 3: Validate safety-critical instructions**

Run the repository’s documented tests, lint/type checks, and CLI `--help` checks. Verify every live-trading instruction includes the required protection and rollback language.

- [ ] **Step 4: Commit, push, and merge**

Commit with `docs: reorganize execution documentation`, push the branch, and record the merged commit ID for the superproject update.

### Task 7: Update the superproject gitlinks and cross-repository navigation

**Files:**
- Modify: submodule gitlinks in the top-level repository
- Modify: `README.md`, `AGENTS.md`, `docs/README.md`
- Modify: top-level cross-repository documentation links and version evidence
- Modify: relevant top-level documentation tests

**Interfaces:**
- Consumes the merged commit IDs from Tasks 3–6.
- Produces a top-level checkout whose documentation links target the new submodule entrypoints.

- [ ] **Step 1: Fetch merged submodule revisions**

Run `git submodule sync --recursive` and `git submodule update --init --recursive`, then verify each gitlink points to the merged documentation commit rather than an unmerged branch.

- [ ] **Step 2: Update top-level links and summaries**

Remove stale direct links to moved submodule pages from top-level active docs. Link to each submodule’s `README.md` or `docs/README.md`, and keep cross-repository contract links only where the top level is the authority.

- [ ] **Step 3: Run cross-repository link and entrypoint checks**

Run: `python scripts/workspace_doctor.py`

Run: `pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py tests/test_gitmodules.py -q`

Run: `python scripts/run_workspace_tests.py`

Expected: all links and entrypoint tests pass, and no top-level test collects submodule internal Markdown as top-level docs.

- [ ] **Step 4: Commit the gitlink update**

```bash
git add README.md AGENTS.md docs .gitmodules alpha-research deep-learning-tick-data-prediction market-data-platform portfolio-backtester quant-execution-engine strategy-app strategy-pipeline strategy-research
git commit -m "docs: sync reorganized submodule documentation"
```

### Task 8: Perform final context and duplicate-content audit

**Files:**
- Modify: any entrypoint or pointer found to violate the design
- Create: `docs/evidence/2026-09-06-documentation-reorganization-audit.md`

- [ ] **Step 1: Audit default reading paths**

Starting from each root `README.md`, follow only the recommended links and verify that the path reaches the relevant current page without entering archive, evidence, plans, or specs unless the task asks for them.

- [ ] **Step 2: Detect duplicate authority claims**

Use `rg` for repeated phrases such as lifecycle authority, module responsibility, current capability, `targets.json`, `catalog.json`, and current asset paths. For every repeated claim, retain one authoritative explanation and convert the others to short context plus a link.

- [ ] **Step 3: Check pointer quality**

Verify every superseded page has a valid target, no duplicated long-form content, and no active index link that still treats it as authoritative.

- [ ] **Step 4: Record audit evidence**

Write the audit with repository commit IDs, commands run, counts of active/category/archive pages, broken-link count, and any accepted exceptions. Do not copy full document contents into the audit.

- [ ] **Step 5: Run final verification**

Run: `git diff --check`

Run: `pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py tests/test_workspace_doctor.py -q`

Run: `python scripts/workspace_doctor.py`

Expected: zero broken links, zero unresolved superseded targets, and passing top-level documentation and workspace checks.

- [ ] **Step 6: Commit the audit**

```bash
git add docs/evidence/2026-09-06-documentation-reorganization-audit.md
git commit -m "docs: record documentation reorganization audit"
```

