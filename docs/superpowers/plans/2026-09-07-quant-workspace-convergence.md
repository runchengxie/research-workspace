# Quant Workspace Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前同时挂载旧仓库和 `quant-*` 目标仓库的 `research-workspace` 收敛为“明确的目标仓库集合 + 1 个轻量集成层”，完成可审计的代码、文档、契约和运行时切换，并在回滚窗口结束后退役旧子模块。

**Architecture:** `quant-platform` 负责公开通用框架、公共 contracts、回测、组合、风险、执行模拟和可复用编排；`quant-research` 负责私有策略、alpha 私有边界、机器学习、实验、证据、策略应用和私有执行运行时；`quant-market-data-platform` 是否作为独立数据 owner 保留，必须先解决现有迁移文档与组件映射的冲突；`market-intel` 负责报告、投递和运营。`research-workspace` 只保留 gitlink 组合、跨仓契约冒烟、版本/发布治理、迁移导航和历史复现入口。

**Tech Stack:** Git submodules, Python 3.12+, `uv`, pytest, Ruff, `ty`, JSON/YAML migration manifests, shell-based production promotion and rollback checks.

## Execution ledger (updated 2026-09-07)

- Task 1 inventory/map: complete on isolated branch `chore/quant-workspace-convergence`; commits `3ceeae021`, `90cc25f80`, `e35fc0a0e`, `0393e57e2`, `0a842958b`, `c2c8fe469`, `6f2e5bf34`, `a30c9212f`.
- Current `strategy-research` parity: CSI 800 closure assets and the pipeline-boundary test are transferred to `quant-research`; target branch `chore/strategy-research-current-parity` ends at `0d9af526` and focused validation is `3 passed`.
- Current parity result: 510 exact paths, 289 exact hashes, 0 globally absent symbols; the remaining 166 absent paths are documented directory relocations for 38 docs paths and 128 tests paths.
- Market-data validation: local target fix `b0adf07` makes the full target suite `898 passed, 1 skipped`; it remains unpushed.
- Validation update: the main workspace recursive submodule checkout is clean; `quant-platform` full tests are `1162 passed, 3 skipped` with Ruff green. `quant-research` full tests reached 100% with no failures and changed-file Ruff/format checks are green, while its full-repository Ruff/format/ty gates remain red on pre-existing debt (1601 / 182 / 1034 diagnostics respectively).
- Provenance update: the two staged public portfolio files have matching SHA-256 hashes, but `portfolio-backtester` has no `LICENSE`, `LICENSE.md` or `COPYING`; the map now records `PUBLICLY_EXCLUDED_PRIVATE_TARGET_REQUIRED` pending independent authorization.
- Ownership update: `strategy-research` is now recorded as `REVIEW_REQUIRED` with `quant-research` as owner; its “review” means retirement/cutover approval, not an outstanding source-code transfer.
- Ownership matrix update: every legacy component now has an explicit owner/decision and evidence pointer; the inventory test enforces this invariant (`3 passed` with release-manifest coverage).
- Cutover preparation: added `migration/target-release-manifest-20260907.json` with target revisions, all legacy rollback gitlinks, a 14-day window, and `current_switch=false`; its consistency test passes (`3 passed` including inventory).
- Promotion rehearsal: fixed `scripts/promote-production.sh` so a fresh-root `--dry-run` does not execute submodule operations or fail while pruning a nonexistent releases directory; shell syntax, production-maintenance tests (`5 passed`) and a real temporary-root dry-run now pass.
- Local target composition: the isolated workspace branch pins `quant-research` to candidate commit `80c7524` and `market-data-platform` to candidate `b0adf07`, while retaining every legacy submodule for rollback.
- Candidate composition update: the interrupted clone state was recovered, governance metadata was regenerated, and `workspace_doctor.py` reports `errors=0, warnings=5`; the latest candidate workspace commit is `69d4e9fdc` and remains unpromoted.
- Candidate validation update: `python scripts/run_workspace_tests.py` passes with `512 passed`; the remaining doctor warnings are environment/debt warnings and are recorded in the evidence ledger.
- Readiness update: shared pre-push hooks are installed and pass `--check` across all 12 managed repositories; the candidate doctor result is now `errors=0, warnings=5`. The remaining strategy-pipeline warning is real: its local remote has no `origin/main` ref.
- Still open: portfolio provenance/license ruling, closure of target quality debt, external integration of the local target branches, production cutover, 14-day rollback observation, and legacy submodule retirement. No deletion or remote push is authorized by this ledger.

**Spec:** `research-workspace/docs/migration/quant-repo-migration.md` and `research-workspace/migration/supersession-component-map.json`

## Global Constraints

- 新代码不得继续把 `research-workspace` 或旧 submodule 当作新的权威实现位置。
- 私有策略、因子、机器学习、实验和研究证据进入 `quant-research`。
- 通用数据接口、回测、组合构造、风险、执行模拟和公共 contracts 进入 `quant-platform`。
- `research-workspace` 只维护迁移导航、历史复现、跨仓版本锁定和未完成迁移的兼容边界。
- 不迁移大型数据、缓存、运行产物、凭证、API 密钥或交易审计日志。
- 任何生产切换必须保留旧 `current`、不可变 release 和至少一个可验证回滚版本。
- 只有完成生产者、消费者、contract、测试和回滚证据后，才可以删除旧 submodule gitlink。
- 跨仓库改动按“目标子仓库先合并，顶层最后更新 gitlink”的顺序进行。
- 文档迁移后旧路径只保留短兼容指针，使用 `status: superseded` 和 `superseded_by`，不得复制正文。

---

## 当前盘点结论

当前 `research-workspace` 的 `main` 已同时挂载 8 个旧链路 submodule、`quant-platform`、`quant-research` 和 `market-intel` 三个目标 submodule。`.gitmodules` 中 `market-data-platform` 的目录名仍是旧名，但远端已经指向 `quant-market-data-platform`。因此当前状态是迁移基线，不是最终收口状态。

已存在的迁移证据显示：

- `quant-platform/migration/alpha-public-parity.json`、`execution-parity.json`、`microstructure-public-parity.json` 和 `orchestration-parity.json` 已证明若干公共子集转移完成。
- `quant-research/migration/alpha-research-parity.json`、`market-data-parity.json`、`microstructure-parity.json` 和 `execution-private-parity.json` 已证明若干私有子集转移完成。
- `quant-platform/migration/provenance.json` 仍为 `local-staging-only`，portfolio-backtester 公共组合内核的历史/许可证归档尚未完成最终确认。
- `research-workspace/migration/supersession-component-map.json` 仍把大部分组件标为 `REVIEW_REQUIRED`，把 `strategy-research` 标为 `TRANSFER_REQUIRED`，根工作区标为 `RETAIN_IN_WORKSPACE`。
- `docs/migration/quant-repo-migration.md` 将 `market-data-platform` 定义为独立 owner，而 `supersession-component-map.json` 又将它拆成 `quant-platform:public-data` 与 `quant-research:market_data_platform`，两者必须在删除旧 gitlink 前形成一个有 owner、依赖和回滚证据的统一决定。
- `research-workspace/README.md` 与 `ARCHITECTURE.md` 已声明 sunset，但当前文档仍按旧 8 个子模块描述运行链路，需要在切换前统一。

## 文件结构和职责

| 文件或目录 | 迁移后的职责 |
| --- | --- |
| `migration/supersession-component-map.json` | 唯一组件级迁移状态和目标路径清单 |
| `docs/migration/quant-repo-migration.md` | 人类可读的边界、迁移顺序、回滚和阅读入口 |
| `src/research_contracts/` | 仅保留仍由集成层拥有的跨仓 contract；可复用公共 contract 转入 `quant-platform/packages/research-contracts/` |
| `scripts/workspace_doctor.py`、`scripts/run_submodule_checks.py`、`scripts/run_workspace_tests.py` | 集成层健康检查和委托检查，不复制目标仓库内部质量逻辑 |
| `scripts/submodule_checks.json`、版本矩阵和发布脚本 | 目标 gitlink、兼容组合、production promotion 和 rollback 证据 |
| `docs/contracts.md`、`docs/version-matrix.md`、`docs/release-checklist.md` | 跨仓交接、版本锁定和发布治理 |
| `docs/archive/`、`docs/evidence/` | 历史结论和带提交/哈希的证据，不作为当前实现入口 |
| `quant-platform/migration/*.json` | 公共代码 parity、许可证、历史和排除项证据 |
| `quant-research/migration/*.json` | 私有代码 parity、策略资产、运行时和回滚证据 |

---

### Task 1: Freeze the post-adjustment migration inventory

**Files:**
- Create: `research-workspace/migration/2026-09-07-convergence-inventory.json`
- Modify: `research-workspace/migration/supersession-component-map.json`
- Test: `research-workspace/tests/test_migration_inventory.py`

**Interfaces:**
- Consumes: current `.gitmodules`, `git submodule status`, each repository HEAD, branch, remote and worktree status.
- Produces: machine-readable source/target commit map, ownership decision, parity evidence path, rollback dependency and cutover gate for every component.

- [ ] **Step 1: Record the exact current state**

  Capture `git submodule status`, `git -C <repo> status --short --branch`, `git -C <repo> remote -v`, `git -C <repo> log -1 --format=...`, tracked file counts and current production revision manifests. Store only repository metadata, not credentials or data paths.

- [ ] **Step 2: Normalize the component map**

  Add explicit entries for `market-data-platform → quant-market-data-platform` or the split target only after resolving the ownership conflict; `deep-learning-tick-data-prediction → quant-platform:microstructure-public + quant-research:ticknet`; `alpha-research → quant-platform:alpha-public + quant-research:alpha_research`; `strategy-research → quant-research`; `strategy-app → quant-research:strategy_app`; `strategy-pipeline → quant-platform:orchestration + quant-research:private adapters`; `portfolio-backtester → quant-platform`; and `quant-execution-engine → quant-platform:public + quant-research:private`.

- [ ] **Step 3: Add a failing inventory consistency test**

  Assert that every legacy component has exactly one status from `TRANSFER_REQUIRED`, `REVIEW_REQUIRED`, `PUBLICLY_EXCLUDED_PRIVATE_TARGET_REQUIRED`, `DOCUMENTATION_RELOCATE`, `HISTORICAL_ARCHIVE` or `RETAIN_IN_WORKSPACE`; every target path exists or is explicitly excluded; and no target points to a credential/data directory.

- [ ] **Step 4: Run the inventory test and commit the baseline**

  Run: `uv run pytest research-workspace/tests/test_migration_inventory.py -q`

  Commit: `docs: freeze quant workspace convergence inventory`

### Task 2: Close public/private parity and provenance gaps

**Files:**
- Modify: `quant-platform/migration/provenance.json`
- Modify: `quant-platform/migration/alpha-public-parity.json`
- Modify: `quant-platform/migration/execution-parity.json`
- Modify: `quant-platform/migration/microstructure-public-parity.json`
- Modify: `quant-platform/migration/orchestration-parity.json`
- Modify: `quant-research/migration/alpha-research-parity.json`
- Modify: `quant-research/migration/market-data-parity.json`
- Modify: `quant-research/migration/microstructure-parity.json`
- Modify: `quant-research/migration/execution-private-parity.json`
- Test: `quant-platform/tests/test_migration_provenance.py`
- Test: `quant-research/tests/test_migration_parity.py`

**Interfaces:**
- Consumes: frozen inventory and legacy source commits.
- Produces: file-level or counted parity receipts, explicit exclusions, license ruling, and rollback commit for each transferred slice.

- [ ] **Step 1: Verify public transfers against their recorded legacy commits**

  For each parity manifest, compare the listed source file count, target file count, exported file hashes and test scope. Any missing file must be classified as private, obsolete, archived or still requiring transfer; it must not be silently ignored.

- [ ] **Step 2: Resolve portfolio provenance**

  In `quant-platform/migration/provenance.json`, replace `local-staging-only` only after recording the source license file, approved history/import decision, exact target commit and hash of every public file. If the source license or history cannot be legally/technically accepted, classify the affected public slice as `PUBLICLY_EXCLUDED_PRIVATE_TARGET_REQUIRED` and keep it in `quant-research` or the legacy repository.

- [ ] **Step 3: Verify private strategy and runtime transfers**

  Compare `strategy-research`, `strategy-app` and private `quant-execution-engine` paths against `quant-research/src`, `research`, `registry`, `tests` and `docs`. Keep strategy lifecycle and evidence in `quant-research`; keep reusable mechanics out of the private strategy package.

- [ ] **Step 4: Run target-repository gates**

  Run in `quant-platform`: `uv sync --locked --all-groups`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`.

  Run in `quant-research`: `uv sync --locked --extra dev`, `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`.

  Commit each repository’s evidence independently before updating the superproject.

### Task 3: Transfer strategy-research and strategy-app ownership completely

**Files:**
- Modify: `quant-research/catalog.json`
- Modify: `quant-research/registry/`
- Modify: `quant-research/research/strategies/`
- Modify: `quant-research/research/experiments/`
- Modify: `quant-research/docs/strategy-research/`
- Modify: `quant-research/docs/strategy-app/`
- Modify: `research-workspace/strategy-research/` only for compatibility pointers and source commit references
- Modify: `research-workspace/strategy-app/` only for compatibility pointers and source commit references
- Test: `quant-research/tests/`

**Interfaces:**
- Consumes: old strategy identity, experiment, evidence, application and lifecycle paths.
- Produces: one authoritative private research tree, stable strategy catalog, no runtime dependency on old `strategy-research` or `strategy-app` source paths.

- [ ] **Step 1: Build the file-level strategy transfer manifest**

  Enumerate every tracked Python, JSON, YAML, Markdown and test file under the two legacy repositories. Assign it to `quant-research/research`, `src/strategy_app`, `docs`, `legacy` or `archive`, with source commit and deletion/retirement rule.

- [ ] **Step 2: Migrate current strategy identity and evidence first**

  Transfer `catalog.json`, promotion profiles, strategy READMEs, cases, evidence, judgment ledgers and experiment configs. Keep lifecycle and production eligibility only in the target catalog.

- [ ] **Step 3: Migrate strategy-app runtime and tests**

  Transfer the public strategy application entrypoints and tests into `quant-research/src/strategy_app` and `quant-research/tests`, preserving `strategy_app.*` imports and artifact schemas. Remove only duplicated implementation after target tests pass.

- [ ] **Step 4: Rewrite internal links and dependency pins**

  Replace active references to old repository paths with `quant-research` paths or published contracts. Historical records may retain old names only when marked historical and linked to the target.

- [ ] **Step 5: Run strategy-specific validation**

  Run: `uv run pytest -q tests/strategy_app tests/strategy_research tests/research` from `quant-research`.

  Run: `python scripts/strategy_evidence_gate.py --strict` and verify that known research gaps remain explicitly recorded rather than being converted into production eligibility.

### Task 4: Split and cut over strategy-pipeline and execution boundaries

**Files:**
- Modify: `quant-platform/packages/orchestration/`
- Modify: `quant-platform/packages/execution/`
- Modify: `quant-research/src/quant_execution_engine/`
- Modify: `quant-research/src/strategy_app/pipeline/`
- Modify: `research-workspace/docs/contracts.md`
- Modify: `research-workspace/scripts/submodule_checks.json`
- Test: `quant-platform/tests/orchestration/`
- Test: `quant-platform/tests/execution/`
- Test: `quant-research/tests/quant_execution_engine/`
- Test: `research-workspace/tests/test_execution_semantic_parity.py`

**Interfaces:**
- Consumes: `strategy-pipeline` CLI/publication behavior, `quant-execution-engine` public/private behavior, `targets.json` and execution evidence contracts.
- Produces: public orchestration/execution APIs in `quant-platform`, private adapters/runtime in `quant-research`, and a versioned artifact boundary between them.

- [ ] **Step 1: Classify every pipeline and execution module**

  Mark each module as public reusable control-plane, private strategy adapter, provider/broker integration, credential boundary, historical tool or obsolete facade. Do not move broker SDKs or credentials into the public platform.

- [ ] **Step 2: Lock the artifact contract before code removal**

  Verify that `targets.json`, lineage sidecars, execution state and receipts have producer, consumer, schema version, content hash and rollback semantics in `docs/contracts.md` and the target repository tests.

- [ ] **Step 3: Cut over callers to target APIs**

  Update active callers to `quant_platform` orchestration/execution APIs and `quant_research` private adapters. Keep old CLI names only as tested compatibility wrappers with an explicit retirement date.

- [ ] **Step 4: Run parity and dry-run validation**

  Run the public orchestration/execution suites, private execution suite, workspace artifact contract tests, and a no-submit qexec dry run. Confirm no test or command reads old source paths directly.

### Task 5: Move root contracts, governance scripts and documentation into their final owners

**Files:**
- Modify: `research-workspace/src/research_contracts/`
- Modify: `quant-platform/packages/research-contracts/`
- Modify: `research-workspace/scripts/`
- Modify: `research-workspace/docs/contracts.md`
- Modify: `research-workspace/docs/version-matrix.md`
- Modify: `research-workspace/docs/workspace-maintenance.md`
- Modify: `research-workspace/docs/README.md`
- Create: compatibility pointer files under `research-workspace/docs/`
- Test: `research-workspace/tests/test_docs_links.py`
- Test: `research-workspace/tests/test_documentation_entrypoints.py`
- Test: `research-workspace/tests/test_namespace_contracts.py`

**Interfaces:**
- Consumes: root contracts, doctor scripts, quality delegation, architecture manifests and current documentation.
- Produces: a thin integration layer with no strategy-specific implementation and target-owned public contracts where reuse is required.

- [ ] **Step 1: Classify root Python code**

  Keep only cross-repository orchestration, gitlink/version checks, contract smoke checks, release/rollback governance and compatibility validation in the root. Move reusable artifact logic to `quant-platform`; move strategy-specific readiness and evidence logic to `quant-research`; archive historical-only utilities under dated evidence/archive entries.

- [ ] **Step 2: Establish one contract owner per schema**

  For each schema in `src/research_contracts`, record producer, consumer, canonical package, compatibility window and test. Package reusable contracts from `quant-platform`; retain root wrappers only while the migration manifest requires them.

- [ ] **Step 3: Reduce workspace scripts to delegation**

  `run_submodule_checks.py` must dispatch registered commands from `scripts/submodule_checks.json`; it must not reimplement target-repository lint or test logic. `workspace_doctor.py` must validate gitlinks, paths, forbidden files, contract pointers and rollback metadata.

- [ ] **Step 4: Reorganize active documentation**

  Keep root docs limited to cross-repository architecture, contracts, version matrix, release governance and migration navigation. Move implementation details to the owning target repository. Convert superseded root pages to short pointers containing `status: superseded` and `superseded_by`.

- [ ] **Step 5: Run documentation and root gates**

  Run: `python scripts/workspace_doctor.py`, `python src/research_contracts/smoke_contracts.py`, `python scripts/run_workspace_tests.py`, `python scripts/run_quality_checks.py --profile hard`, `python scripts/run_submodule_checks.py --profile smoke`.

### Task 6: Make the target-only workspace composition explicit

**Files:**
- Modify: `research-workspace/.gitmodules`
- Modify: `research-workspace/README.md`
- Modify: `research-workspace/ARCHITECTURE.md`
- Modify: `research-workspace/AGENTS.md`
- Modify: `research-workspace/pyproject.toml`
- Modify: `research-workspace/uv.lock`
- Modify: `research-workspace/scripts/submodule_checks.json`
- Modify: `research-workspace/tests/test_gitmodules.py`
- Modify: `research-workspace/tests/test_workspace_architecture.py`

**Interfaces:**
- Consumes: completed target parity manifests and root ownership classification.
- Produces: one explicit final submodule model: `quant-platform`, `quant-research`, `market-intel`, plus the integration-layer root; no ambiguous duplicate owner paths.

- [ ] **Step 1: Define the final submodule set and path policy**

  Use stable target paths and URLs. Decide explicitly whether `quant-market-data-platform` remains an independent data-platform submodule, and separately decide whether `quant-code-quality`, `quant-data-maintenance` and `quant-intel-deploy` are target submodules or external support repositories. Keep `market-data-platform` as an explicit compatibility alias only if the 14-day rollback window requires it; otherwise rename the gitlink path to `quant-market-data-platform` in one coordinated commit with all path consumers.

- [ ] **Step 2: Update all path-sensitive checks**

  Synchronize `.gitmodules`, doctor checks, version matrix generation, submodule check dispatch, production manifests, dependency source pins and documentation links. Add assertions that old paths occur only in migration/archive/compatibility records.

- [ ] **Step 3: Validate a clean recursive checkout**

  In a fresh temporary checkout, run `git clone --recurse-submodules`, `git submodule sync --recursive`, `git submodule update --init --recursive`, then run the workspace doctor and smoke contract check without relying on local path overrides.

### Task 7: Execute production cutover and close the rollback window

**Files:**
- Modify: `research-workspace/docs/release-checklist.md`
- Modify: `research-workspace/docs/production-update.md`
- Modify: `research-workspace/docs/version-matrix.md`
- Modify: `research-workspace/migration/2026-09-07-convergence-inventory.json`
- Modify: `research-workspace/migration/supersession-component-map.json`
- Modify: `research-workspace/scripts/promote-production.sh`
- Modify: target repository production manifests and lock files only where the cutover evidence requires it
- Test: `research-workspace/tests/test_production_maintenance.py`
- Test: `research-workspace/tests/test_private_research_config_boundary.py`

**Interfaces:**
- Consumes: target release tags, artifact contract evidence, clean recursive checkout evidence and parity manifests.
- Produces: immutable target releases, updated production `current` links, revision manifest, rollback tag and a dated decision to retire old submodules.

- [ ] **Step 1: Create immutable target releases**

  Tag the validated commits of `quant-platform`, `quant-research` and `market-intel`. Record tag, commit, dependency lock hash, artifact schema versions and test results in the root version matrix.

- [ ] **Step 2: Run a no-side-effect cutover rehearsal**

  Execute `bash scripts/promote-production.sh --repo all --dry-run`, workspace contract smoke, target test suites and qexec no-submit dry run. Confirm the old production `current` remains unchanged during rehearsal.

- [ ] **Step 3: Promote atomically**

  Promote target releases using the existing production script. Record the parent commit, all submodule revisions, production revision manifest and resulting artifact consumer revisions. Keep the prior release and `current` rollback path intact.

- [ ] **Step 4: Observe the 14-day rollback window**

  During the window, verify scheduled reports, research artifact publication, target handoff, data freshness, execution dry runs and recovery procedures. No old submodule is deleted during this window.

- [ ] **Step 5: Close or extend the window with evidence**

  Close it only when all producers and consumers pass the recorded gates. If a gate fails, preserve the old pins, document the failing contract and extend the window; do not delete the source repository.

### Task 8: Retire old submodules and archive the migration

**Files:**
- Modify: `research-workspace/.gitmodules`
- Modify: `research-workspace/README.md`
- Modify: `research-workspace/ARCHITECTURE.md`
- Modify: `research-workspace/AGENTS.md`
- Modify: `research-workspace/migration/supersession-component-map.json`
- Create: `research-workspace/docs/evidence/2026-09-<actual-close-date>-quant-workspace-convergence.md`
- Test: `research-workspace/tests/test_gitmodules.py`
- Test: `research-workspace/tests/test_workspace_architecture.py`

**Interfaces:**
- Consumes: closed rollback window and production revision manifest.
- Produces: target-only workspace composition, archived source references and a reproducible rollback record.

- [ ] **Step 1: Confirm old submodule deletion targets**

  Resolve the exact gitlink paths and verify they contain no unique files classified as `TRANSFER_REQUIRED` or `DOCUMENTATION_RELOCATE`. Preserve all source commit IDs in the convergence evidence before removal.

- [ ] **Step 2: Remove obsolete gitlinks in one reviewed change**

  Remove only the retired old gitlink entries and their `.gitmodules` records. Do not delete `/home/richard/code/production`, `~/data`, release snapshots, credentials, tags or external repositories.

- [ ] **Step 3: Update root documentation to post-migration language**

  Change the root from sunset-transition wording to lightweight integration-layer wording. Keep migration navigation and historical links, but remove old implementation instructions from the recommended path.

- [ ] **Step 4: Run the final full gate**

  Run `git diff --check`, `python scripts/workspace_doctor.py`, `python src/research_contracts/smoke_contracts.py`, `python scripts/run_workspace_tests.py`, `python scripts/run_quality_checks.py --profile hard`, `python scripts/run_submodule_checks.py --profile full --dry-run`, and the target repository locked test suites.

- [ ] **Step 5: Commit and archive the final evidence**

  Commit the root closeout as `chore: retire superseded quant workspace submodules`, publish the closeout evidence, and update the component map so every entry is `TRANSFERRED`, `ARCHIVED` or `RETAIN_IN_WORKSPACE` with a concrete evidence link.

## Verification Matrix

| Gate | Pass condition |
| --- | --- |
| Inventory | Every legacy component has a source commit, target path, status, parity evidence and rollback rule |
| Code parity | Every transferred source/test/documentation slice is counted or hash-verified; exclusions are explicit |
| Ownership | No active strategy implementation lives in `quant-platform`; no reusable platform implementation is duplicated in `quant-research` or root |
| Contract | `targets.json`, lineage, research artifacts and execution state pass producer/consumer schema tests |
| Documentation | Root pages describe only integration concerns; target repositories own implementation docs; old pages are pointers or archives |
| Dependencies | Locked installs resolve target repositories or approved package sources, never an untracked staging checkout |
| Production | Target releases are immutable, promoted atomically, and the previous release remains rollback-capable |
| Cleanup | Old gitlinks are removed only after the 14-day window and final evidence are complete |

## Rollback Procedure

If any cutover gate fails, restore the previous production `current` link and revision manifest, restore the previous workspace gitlink commit, and stop deleting old submodules. Keep the target repositories and migration manifests intact for diagnosis. Re-run the failed producer/consumer contract in isolation, correct the owning target repository, publish a new immutable release, and restart the observation window.

## Self-review checklist

- [ ] Every component in `supersession-component-map.json` is covered by Tasks 1–8.
- [ ] Portfolio provenance remains blocked until license/history evidence is recorded.
- [ ] `strategy-research` is explicitly handled as `TRANSFER_REQUIRED`, not treated as already complete.
- [ ] Root contracts, scripts and docs are classified separately from strategy code.
- [ ] Public/private exclusions and credential/data boundaries are explicit.
- [ ] No task authorizes deletion before the rollback window and final verification.
- [ ] All commands reference actual paths and existing workspace gates.
