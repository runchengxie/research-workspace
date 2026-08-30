# Cross-Repository Boundary Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收紧 strategy-pipeline、deep-learning-tick-data-prediction、strategy-research 和 market-intel 的职责边界，在不破坏现有运行时契约的前提下迁移重复实现、保留薄入口，并用文档记录不适合进入生产主线的探索代码。

**Architecture:** 先建立跨仓边界清单与禁止依赖测试，再按 owner API 迁移调用方。strategy-pipeline 只保留 CLI、编排、运行目录和发布控制；market-data-platform 负责可复用 canonical 数据资产；Deep Learning 只消费 published asset 并保留模型专属窗口、label、tensor 和评估；strategy-research 将复用逻辑放入 `src/`，实验入口保持薄化。

**Tech Stack:** Python 3.12/3.13, uv, pytest, ruff, ty, Git submodules, JSON/YAML/Markdown governance manifests.

**Spec:** 用户提供的跨仓职责边界审计说明，以及 `docs/market-intel-owner-boundary.md`、`market-intel/docs/boundary-contract.md`、`docs/submodule-boundary-refactor-checklist.md`。

## Global Constraints

- 不直接大规模移动文件，先建立 owner API、调用方测试和迁移清单。
- 不把一次性研究 runner 强行变成生产 API。
- 不让 market-intel import research-workspace、strategy-pipeline 或其他 owner 的内部 Python 模块。
- Deep Learning 只能消费 market-data-platform 的 published asset、schema、receipt 或显式 adapter。
- 任何删除旧实现的提交必须同时保留迁移记录、测试覆盖和恢复入口。
- 每个子项目独立测试通过后才能更新顶层 submodule gitlink。

---

### Task 1: 建立跨仓边界盘点与机器可读清单

**Files:**
- Create: `docs/boundary-refactor-inventory-20260831.json`
- Create: `tests/test_boundary_refactor_inventory.py`
- Modify: `docs/submodule-boundary-refactor-checklist.md`
- Test: `tests/test_boundary_refactor_inventory.py`

**Interfaces:**
- Produces a stable inventory schema with `repo`, `path`, `owner`, `classification`, `target`, and `status` fields.
- Classifications are exactly `runtime-owner`, `research-reusable`, `experiment-entry`, `consumer-bridge`, or `deprecated-duplicate`.

- [x] **Step 1: Write the failing inventory schema test**

  Test that the inventory contains the currently identified families: strategy-pipeline DailyWatch20/Hotsector modules, pipeline accounting/liquidity modules, Deep Learning eventstream/nextday data modules, strategy-research experiments, and market-intel tushare jobs/bridges.

- [x] **Step 2: Run the inventory test**

  Run: `uv run --project strategy-pipeline --extra dev python -m pytest tests/test_boundary_refactor_inventory.py -q`

  Expected: FAIL because the inventory file does not exist.

- [x] **Step 3: Add the inventory and checklist links**

  Record each candidate with its current owner, proposed owner, migration risk, and whether it is eligible for deletion. Do not claim migration completion until a later task lands the replacement API and tests.

- [x] **Step 4: Run the inventory test again**

  Run: `uv run --project strategy-pipeline --extra dev python -m pytest tests/test_boundary_refactor_inventory.py -q`

  Expected: PASS.

- [x] **Step 5: Commit**

  ```bash
  git add docs/boundary-refactor-inventory-20260831.json docs/submodule-boundary-refactor-checklist.md tests/test_boundary_refactor_inventory.py
  git commit -m "docs: inventory cross-repository boundary candidates"
  ```

### Task 2: Add strategy-pipeline boundary guards before moving code

**Files:**
- Create: `strategy-pipeline/tests/test_research_boundary_contract.py`
- Modify: `strategy-pipeline/src/strategy_pipeline/` only when a guard requires a public facade
- Modify: `docs/boundary-refactor-inventory-20260831.json`

**Interfaces:**
- The guard scans tracked Python sources and rejects imports from owner packages that are not allowed in pipeline orchestration.
- The initial allowlist permits CLI, runner, publication, receipt, and orchestration modules, while flagging research algorithms, backtest accounting, and raw data loaders for review.

- [x] **Step 1: Write tests for forbidden ownership imports and flagged module families**
- [x] **Step 2: Run the focused pipeline tests and capture the baseline findings**
- [x] **Step 3: Classify each finding as move, facade, or accepted orchestration code**
- [x] **Step 4: Add only the smallest guard and documentation needed for the classified baseline**
- [x] **Step 5: Run pipeline tests, ruff, and ty**
- [x] **Step 6: Commit the boundary guard separately from any migration**

### Task 3: Separate Deep Learning published-data consumption from model preprocessing

**Files:**
- Modify: `deep-learning-tick-data-prediction/src/ticknet/eventstream/canonical_adapter.py`
- Modify: `deep-learning-tick-data-prediction/src/ticknet/eventstream/storage_readiness.py`
- Modify: `deep-learning-tick-data-prediction/src/ticknet/eventstream/materialized.py`
- Modify: `deep-learning-tick-data-prediction/src/ticknet/nextday/raw_snapshot.py`
- Modify: `deep-learning-tick-data-prediction/src/ticknet/nextday/snapshot_io.py`
- Create: `deep-learning-tick-data-prediction/src/ticknet/data_boundary.py`
- Create: `deep-learning-tick-data-prediction/tests/test_data_boundary_contract.py`
- Modify: `deep-learning-tick-data-prediction/docs/architecture/data-boundary.md`

**Interfaces:**
- `load_published_event_asset(path: Path, receipt: Path | None = None) -> pd.DataFrame` validates published schema and receipt metadata without owning raw ingestion.
- `build_model_window(events: pd.DataFrame, *, window_size: int, horizon: int) -> np.ndarray` remains model-owned.
- `build_horizon_labels(frame: pd.DataFrame, *, horizon: int) -> pd.Series` remains model-owned.

- [x] **Step 1: Add tests proving published asset loading is separate from model windows and labels**
- [x] **Step 2: Run the tests and record the current import/path violations**
- [x] **Step 3: Implement the explicit adapter boundary without importing market-data-platform business modules**
- [x] **Step 4: Move only shared schema, receipt, timestamp, and identifier validation to market-data-platform if the inventory confirms reuse**
- [x] **Step 5: Update Deep Learning docs and compatibility notes**
- [x] **Step 6: Run Deep Learning focused tests, full tests, ruff, and ty**
- [x] **Step 7: Commit and push the submodule main branch**

### Task 4: Make strategy-research reusable code explicit and experiment entries thin

**Files:**
- Create: `strategy-research/src/strategy_research/experiments.py`
- Create: `strategy-research/src/strategy_research/diagnostics.py`
- Modify: `strategy-research/experiments/*/run*.py` only for duplicated reusable logic
- Create: `strategy-research/tests/test_reusable_research_api.py`
- Modify: `strategy-research/docs/README.md`

**Interfaces:**
- `ExperimentSpec(name: str, lifecycle: str, owner: str, required_inputs: tuple[str, ...])` describes an experiment without running it.
- `load_experiment_spec(path: Path) -> ExperimentSpec` validates experiment metadata.
- `summarize_diagnostics(frame: pd.DataFrame, *, group_by: tuple[str, ...]) -> pd.DataFrame` contains reusable diagnostic aggregation.

- [x] **Step 1: Identify duplicated helpers used by at least two experiments**
- [x] **Step 2: Add failing public API tests for only those helpers**
- [x] **Step 3: Move the minimal shared logic into `src/strategy_research/`**
- [x] **Step 4: Replace experiment-local copies with imports from the public package**
- [x] **Step 5: Add per-experiment README/config/lifecycle metadata where absent**
- [x] **Step 6: Run strategy-research tests and quality gates**
- [x] **Step 7: Commit and push the submodule main branch**

### Task 5: Close market-intel data-owner and bridge boundaries

**Files:**
- Modify: `market-intel/src/tushare_jobs/*.py`
- Modify: `market-intel/src/a_share_daily/*bridge*.py`
- Modify: `market-intel/src/a_share_daily/*delivery*.py`
- Create: `market-intel/tests/test_owner_boundary_contract.py`
- Modify: `market-intel/docs/boundary-contract.md`
- Modify: `docs/market-intel-owner-boundary.md`

**Interfaces:**
- `market-intel` consumers read published assets through documented paths or CLI receipts.
- Report-side jobs may create report-specific snapshots, but may not define canonical market-data schemas or silently publish shared assets.
- Bridge modules may call public CLIs and consume artifact/receipt contracts, but may not import private research or pipeline packages.

- [x] **Step 1: Add tests for forbidden internal imports, hard-coded sibling paths, and unreceipted canonical writes**
- [x] **Step 2: Run the tests and produce a concrete finding list for `tushare_jobs` and bridge modules**
- [x] **Step 3: Replace duplicate canonical reads/writes with published-asset or receipt consumption**
- [x] **Step 4: Delete only code proven to be duplicate after tests cover the replacement**
- [x] **Step 5: Update boundary documentation and migration records**
- [x] **Step 6: Run market-intel full tests and quality gates**
- [x] **Step 7: Commit and push market-intel main**

### Task 6: Integrate submodule pins and remove superseded compatibility code

**Files:**
- Modify: `research-workspace/<submodule gitlinks>`
- Modify: `docs/version-matrix.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/maintainability-refactor-roadmap.yml`
- Modify: relevant deprecated/compatibility files only after Tasks 2–5 pass

- [x] **Step 1: Update each submodule gitlink only after its own main is pushed**
- [x] **Step 2: Run workspace consistency, namespace, ownership, contract, evidence, and doctor checks**
- [x] **Step 3: Remove old implementation only when the inventory marks it `deprecated-duplicate` and the replacement test passes**
- [x] **Step 4: Run the complete root and submodule test suites**
- [x] **Step 5: Push the top-level main branch**
- [x] **Step 6: Verify all main branches are clean, synchronized, and have no open PRs**
