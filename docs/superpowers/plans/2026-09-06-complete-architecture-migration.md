# Complete Architecture Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transfer every required legacy capability, test, document, configuration, CI workflow, and runtime dependency into the public `quant-platform`, private `quant-research`, and independent `market-intel` architecture, then cut over `research-workspace` only after parity and rollback gates pass.

**Architecture:** `quant-platform` owns reusable public mechanisms and contracts; `quant-research` owns private strategies, experiments, evidence, and proprietary configuration; `market-intel` consumes versioned artifacts without importing research implementation; `research-workspace` remains a thin version-and-compatibility layer. Migration is performed repository-by-repository, preserving each legacy commit as a rollback source.

**Tech Stack:** Python 3.12+, `uv`, pytest, Ruff, ty, GitHub Actions, Git submodules during transition, versioned JSON/CSV artifact contracts, and atomic production release pointers.

**Spec:** `docs/migrations/repository-parity-inventory-2026-09-06.md`, `docs/migrations/architecture-cutover-runbook.md`, and `docs/evidence/target-repository-version-manifest-2026-09-06.json`.

## Global Constraints

- Do not delete, archive, rename, or make inaccessible any legacy repository until the 14-calendar-day rollback window is closed.
- Keep legacy commits pinned in the parity inventory and target version manifest.
- Do not copy credentials, raw provider data, proprietary strategies, or private runtime configuration into `quant-platform`.
- Preserve existing Python namespaces and CLI names until a separate compatibility migration is approved.
- Every migrated workstream must include code, tests, documentation, configuration, CI, runtime dependencies, and rollback evidence.
- A public repository release requires an explicit license and a clean public-content review.
- A private CI release requires authenticated access to private dependencies; credentials must exist only as GitHub Actions secrets or deployment secrets.
- `market-intel` may consume only versioned artifacts and public contract APIs; it must not import `strategy_app`, `alpha_research`, `market_data_platform`, or other research implementation packages directly.

## Current baseline

The first slice is complete and validated:

- `quant-platform`: portfolio source code transferred; 31 tests pass; Apache-2.0 added at `fb5612c`.
- `quant-research`: DailyWatch20 code, tests, evidence, and docs transferred; 122 tests pass; private CI green at `a77fb73`.
- `market-intel`: publication boundary and consumer CI green at `83172a3`.

The remaining gaps are not yet complete: portfolio tests/docs, data, alpha, microstructure, orchestration, execution, all remaining strategies, full workspace cutover, and the 14-day post-cutover rollback window.

---

### Task 1: Freeze migration manifests and public/private ownership

**Files:**
- Modify: `docs/migrations/repository-parity-inventory-2026-09-06.md`
- Modify: `docs/evidence/target-repository-version-manifest-2026-09-06.json`
- Modify: `docs/governance/public-private-boundary-matrix.md`
- Modify: `docs/governance/repository-naming-map.md`
- Test: `tests/test_workspace_architecture.py`, `tests/test_workspace_doctor.py`

**Interfaces:**
- Consumes: legacy repository HEAD commits and target repository commit SHAs.
- Produces: one row per legacy repository with source commit, target path, code/test/doc/config/CI/runtime status, owner, and rollback action.

- [ ] **Step 1: Record the exact source baseline**

  Run:

  ```bash
  for repo in market-data-platform deep-learning-tick-data-prediction alpha-research portfolio-backtester strategy-app strategy-pipeline strategy-research quant-execution-engine; do
    git -C "$repo" rev-parse HEAD
    git -C "$repo" ls-tree -r --name-only HEAD
  done
  ```

  Store each SHA and file-count baseline in the parity inventory.

- [ ] **Step 2: Classify every source path**

  For each repository, classify paths into public reusable code, private IP, runtime-only configuration, tests, documentation, CI, and historical/archive material. Record the target repository and target directory for each class.

- [ ] **Step 3: Add machine-checkable ownership rules**

  Extend `docs/architecture-model.yml` and the boundary rules so public packages cannot import private strategy or provider packages.

- [ ] **Step 4: Run the governance checks**

  ```bash
  PYTHONPATH=scripts:src uv run python scripts/run_quality_checks.py --profile hard
  PYTHONPATH=scripts:src uv run python scripts/workspace_doctor.py
  ```

  Expected: zero errors; warnings must be recorded in the inventory.

- [ ] **Step 5: Commit the baseline**

  ```bash
  git add docs/migrations docs/evidence docs/governance docs/architecture-model.yml
  git commit -m "freeze complete migration parity baseline"
  ```

### Task 2: Complete `quant-platform/portfolio` parity

**Files:**
- Create: `quant-platform/tests/` files mapped from `portfolio-backtester/tests/`
- Create: `quant-platform/docs/` files mapped from `portfolio-backtester/docs/`
- Modify: `quant-platform/pyproject.toml`, `quant-platform/uv.lock`
- Modify: `quant-platform/README.md`
- Test: all migrated `quant-platform/tests/`

**Interfaces:**
- Consumes: `portfolio-backtester` source commit `91a4fa4f1d57c074c991546c381a3d90a3b6adfb`.
- Produces: a public portfolio package with source parity, 97 legacy tests restored or explicitly excluded with evidence, 40 relevant docs migrated, and a stable install/test command.

- [ ] **Step 1: Build a path mapping manifest**

  Map `src/portfolio_backtester/*` to `packages/portfolio-backtester/src/portfolio_backtester/*`, `tests/*` to `tests/portfolio_backtester/*`, and `docs/*` to `docs/portfolio-backtester/*`. Preserve the existing public CLI and namespace.

- [ ] **Step 2: Write parity tests for the mapping**

  Add a test that compares the source-file manifest, SHA-256 content hashes, and target mapping for every migrated source file. The test must fail when a source file disappears from the target without an explicit exclusion record.

- [ ] **Step 3: Transfer the missing tests and fixtures**

  Restore the 97 legacy tests and fixtures under the target test namespace. Update only import paths and fixture roots required by the monorepo layout; do not weaken assertions.

- [ ] **Step 4: Transfer the documentation**

  Restore the 40 portfolio documents, including concepts, guides, API reference, testing, ownership, and migration records. Add a README index from public package entry points to those documents.

- [ ] **Step 5: Reconcile dependencies and package metadata**

  Make `quant-platform` own the `research-contracts` dependency from its public package path. Remove local absolute paths from committed lockfiles and ensure `uv sync --locked --all-groups` works in a clean checkout.

- [ ] **Step 6: Run the complete portfolio gate**

  ```bash
  uv sync --locked --all-groups
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest -q
  uv run python -m build
  ```

  Expected: all restored tests pass; public CI passes on its configured Python versions.

- [ ] **Step 7: Commit and publish**

  ```bash
  git add .
  git commit -m "complete public portfolio parity"
  git push origin main
  ```

### Task 3: Migrate reusable data capability and private providers

**Files:**
- Create: `quant-platform/packages/data/`
- Create: `quant-platform/tests/data/`
- Create: `quant-platform/docs/data/`
- Create: `quant-research/providers/`
- Create: `quant-research/config/providers/`
- Modify: `quant-platform/pyproject.toml`, `quant-platform/uv.lock`
- Modify: `quant-research/pyproject.toml`, `quant-research/uv.lock`
- Test: migrated data contract and provider-boundary tests

**Interfaces:**
- Consumes: `market-data-platform` source commit `0f1c4ce2554ad4961a8f130ce953b5d18ea52a0d`.
- Produces: public schemas, interfaces, PIT/quality/lineage checks, and private provider adapters/configuration with no credentials or raw data in Git.

- [ ] **Step 1: Separate public and private paths**

  Use the source manifest to classify the 290 source files and 110 tests. Public target paths may contain schemas, interfaces, quality checks, and deterministic fixtures; provider credentials, vendor-specific runtime adapters, local data roots, and raw snapshots must go to private target paths or remain deployment-only.

- [ ] **Step 2: Add an import boundary test**

  Fail if any public `quant_platform.data` module imports a provider credential module, private config path, or raw-data location.

- [ ] **Step 3: Transfer and run public tests**

  Restore public-safe tests and fixtures, then run them with no external data access. Record exclusions by path and reason.

- [ ] **Step 4: Transfer private provider behavior**

  Move provider adapters and configuration templates into `quant-research/providers/`. Replace every credential value with an environment-variable reference and add a missing-credential failure test.

- [ ] **Step 5: Validate clean environments**

  Run public CI without provider credentials and private CI with `PRIVATE_REPO_READ_TOKEN` plus provider secrets absent. Expected: public deterministic tests pass; private provider tests skip or fail closed without secrets.

- [ ] **Step 6: Record rollback evidence**

  Pin the legacy data commit and previous production data manifest in the workspace release manifest before any consumer switches.

### Task 4: Migrate `alpha-research` into public mechanisms and private edge

**Files:**
- Create: `quant-platform/packages/alpha/`
- Create: `quant-platform/tests/alpha/`
- Create: `quant-platform/docs/alpha/`
- Create: `quant-research/alpha/`
- Create: `quant-research/experiments/alpha/`
- Modify: `quant-platform/pyproject.toml`, `quant-research/pyproject.toml`
- Test: alpha contract, diagnostics, and private-feature boundary tests

**Interfaces:**
- Consumes: `alpha-research` source commit `631ee150d5125917baebbbb31a673696d1d29230`.
- Produces: public feature/diagnostic/training APIs; private feature selections, labels, model choices, experiment configs, and promotion evidence.

- [ ] **Step 1: Inventory the 155 source files, 84 tests, and 33 docs**

  Classify each path by whether it exposes reusable methodology or trading edge. Record every exclusion.

- [ ] **Step 2: Transfer public APIs and tests**

  Move generic transforms, walk-forward/CPCV/PBO utilities, signal schemas, diagnostics, and deterministic fixtures into `quant-platform/packages/alpha` with tests under `quant-platform/tests/alpha`.

- [ ] **Step 3: Transfer private research records**

  Move proprietary feature lists, labels, experiment configurations, failed trials, and promotion evidence into `quant-research/alpha` and `quant-research/experiments/alpha`.

- [ ] **Step 4: Enforce the edge boundary**

  Add a secret/content scan and import test ensuring public modules cannot import `quant_research.alpha` or private experiment paths.

- [ ] **Step 5: Run the two release gates**

  Public gate: deterministic tests, Ruff, type checking, package build, and public CI. Private gate: full private alpha tests with no raw data or secrets committed.

### Task 5: Migrate microstructure models

**Files:**
- Create: `quant-platform/packages/microstructure/`
- Create: `quant-platform/tests/microstructure/`
- Create: `quant-research/microstructure/experiments/`
- Create: `quant-research/microstructure/config/`
- Create: `quant-research/microstructure/evidence/`
- Modify: `docs/migrations/repository-parity-inventory-2026-09-06.md`
- Test: model architecture, dataset interface, and private-label boundary tests

**Interfaces:**
- Consumes: `deep-learning-tick-data-prediction` source commit `2dd47012487c6fcdb66ef3ca4d4fbf7ca585d203`.
- Produces: public event-stream/model abstractions and private labels, universes, configurations, results, and promoted-model evidence.

- [ ] **Step 1: Separate model machinery from research edge**

  Public code may include model architectures, dataset interfaces, event representations, and synthetic fixtures. Private code must contain actual labels, universe construction, data manifests, experiment results, and selection decisions.

- [ ] **Step 2: Transfer tests and references with the same split**

  Public tests must be offline and synthetic. Private tests may use private fixtures but must not publish raw L2 data.

- [ ] **Step 3: Verify model reproducibility**

  Record Python, Torch, CUDA/CPU, seed, model, and dataset-contract versions in an experiment manifest. Run a deterministic smoke training job on synthetic data.

- [ ] **Step 4: Publish only generic artifacts**

  Ensure public documentation and CI do not contain promoted-model results or trading conclusions.

### Task 6: Migrate orchestration and execution boundaries

**Files:**
- Create: `quant-platform/packages/orchestration/`
- Create: `quant-platform/packages/execution/`
- Create: `quant-platform/tests/orchestration/`, `quant-platform/tests/execution/`
- Create: `quant-research/strategies/adapters/`, `quant-research/runtime/`
- Modify: `quant-platform/pyproject.toml`, `quant-research/pyproject.toml`
- Test: CLI compatibility, run-manifest, publication, execution-interface, and secret-boundary tests

**Interfaces:**
- Consumes: `strategy-pipeline` commit `87175c67531f0be29f78aeb078046708dbf38ee4` and `quant-execution-engine` commit `2f0675a4b8946ff4134194e7dd12dc1169fd2be4`.
- Produces: public run control, artifact publication, execution interfaces, and private strategy adapters, broker configuration, credentials, and live runtime.

- [ ] **Step 1: Preserve public CLI names**

  Add compatibility tests for existing `strategy`/`strategy-pipeline` and `qexec` commands before moving implementations. The tests must compare help output and exit behavior.

- [ ] **Step 2: Transfer generic control-plane code**

  Move run manifests, target handoff, quality gates, artifact publication, and deterministic orchestration into `quant-platform/packages/orchestration`.

- [ ] **Step 3: Transfer execution interfaces only**

  Move order/target schemas, simulation interfaces, and deterministic execution contracts to public code. Keep broker adapters, credentials, audit storage, and live runtime private.

- [ ] **Step 4: Keep strategy adapters private**

  Move DailyWatch20 and future strategy-specific policies into `quant-research/strategies/adapters`, importing only public orchestration contracts.

- [ ] **Step 5: Run compatibility and secret scans**

  Run CLI help smoke, artifact contract smoke, public CI, private CI, and the workspace secret scanner. No command may require a legacy checkout after the target package is selected.

### Task 7: Complete remaining `quant-research` strategy families and records

**Files:**
- Create: `quant-research/registry/`
- Create: `quant-research/strategies/` with one directory per catalog strategy
- Create: `quant-research/experiments/` with one directory per catalog strategy
- Create: `quant-research/evidence/` with one directory per catalog strategy
- Modify: `quant-research/migration/provenance.json`
- Test: per-strategy migrated regression suites and registry/evidence gates

**Interfaces:**
- Consumes: `strategy-research` commit `087b5dfdabed70a629ff6ed44fc52609fe966c5f` and `strategy-app` commit `f6f58bf7bbd623318189ab4ab7acf49b331be4a2`.
- Produces: complete private strategy registry, logic, experiments, evidence, configs, and runtime dependencies while preserving `strategy_app` compatibility imports.

- [ ] **Step 1: Enumerate all strategy families**

  Extract strategy identities from `catalog.json`, source package paths, campaign specs, research cases, experiment configs, evidence ledgers, and tests. Store a strategy-by-strategy manifest with source commit and target path.

- [ ] **Step 2: Migrate one strategy family at a time**

  For each family, transfer implementation, tests, docs, configs, evidence, and required dependency pins together. Do not mark a family migrated when only its source code is present.

- [ ] **Step 3: Run the evidence gate**

  ```bash
  uv run python scripts/strategy_evidence_gate.py --strict
  uv run pytest -q
  ```

- [ ] **Step 4: Record rollback and promotion state**

  Keep each legacy strategy commit and production artifact manifest in the private migration manifest. A strategy remains `research_shadow` unless its existing evidence gate says otherwise.

### Task 8: Complete `market-intel` production-shaped consumer validation

**Files:**
- Modify: `market-intel/tests/test_platform_publication_consumer.py`
- Create: `market-intel/tests/fixtures/publications/daily_watch20/`
- Modify: `market-intel/docs/platform-publication.md`
- Modify: `docs/evidence/formal-daily-watch20-market-intel-handoff-2026-09-06.md`
- Test: public CI and local producer-to-consumer handoff

**Interfaces:**
- Consumes: `quant-research/scripts/export_publication.py` output and `quant-platform` contract package.
- Produces: a reproducible consumer fixture and receipt containing producer repository, producer commit, run ID, artifact IDs, hashes, and schema versions.

- [ ] **Step 1: Add a production-shaped fixture**

  Store only synthetic `watchlist_20.csv`, `selection_receipt.json`, and the publication manifest. Do not store real data or private paths.

- [ ] **Step 2: Validate both internal artifacts**

  Assert consumer selection, internal-audience opt-in, path confinement, and SHA-256 verification.

- [ ] **Step 3: Run remote consumer CI**

  Confirm all supported Python versions pass and record the run ID in the evidence document.

- [ ] **Step 4: Validate delivery behavior**

  Run the existing freshness/recovery/delivery smoke tests against the synthetic bundle and verify that a missing or tampered artifact fails closed.

### Task 9: Perform workspace consumer cutover

**Files:**
- Modify: `.gitmodules` only after all prior gates pass
- Modify: `docs/evidence/target-repository-version-manifest-2026-09-06.json`
- Modify: `docs/migrations/architecture-cutover-runbook.md`
- Modify: `docs/deprecations.yml`
- Test: workspace doctor, contract smoke, hard quality, full workspace tests, release rollback rehearsal

**Interfaces:**
- Consumes: green target repository commits, consumer receipt, license evidence, and production rollback manifest.
- Produces: an exact target version combination with a reversible production cutover.

- [ ] **Step 1: Verify all release gates**

  Require public CI, private CI, consumer CI, complete parity matrix, explicit license, CODEOWNERS, clean secret scan, and a production-shaped handoff receipt.

- [ ] **Step 2: Create a release manifest**

  Record exact target commits, previous legacy commits, artifact hashes, runtime dependency lock hashes, CI run IDs, and rollback release identifiers.

- [ ] **Step 3: Run compatibility checks before gitlink changes**

  ```bash
  uv run python scripts/workspace_doctor.py
  uv run python src/research_contracts/smoke_contracts.py
  PYTHONPATH=scripts:src uv run python scripts/run_quality_checks.py --profile hard
  uv run python scripts/run_workspace_tests.py
  ```

- [ ] **Step 4: Change one authoritative pointer at a time**

  Update the manifest first, validate, then update the smallest necessary gitlink or target reference. Keep the previous release active until the new release passes the same checks.

- [ ] **Step 5: Rehearse rollback**

  Atomically restore the previous `current` pointer and rerun contract, CLI, freshness, and delivery smoke checks.

### Task 10: Operate and close the rollback window

**Files:**
- Modify: `docs/migrations/architecture-cutover-runbook.md`
- Create: `docs/evidence/architecture-cutover-window-closure.md`
- Modify: `docs/evidence/target-repository-version-manifest-2026-09-06.json`
- Test: scheduled production checks and rollback rehearsal

**Interfaces:**
- Consumes: active target release, previous release, daily operational receipts, and rollback rehearsal output.
- Produces: explicit closure evidence authorizing legacy repository retirement consideration.

- [ ] **Step 1: Start the 14-day window at T0**

  Record UTC start time, active release, previous release, target commits, and rollback locations.

- [ ] **Step 2: Record daily checks**

  Record publication freshness, artifact hashes, consumer validation, delivery status, recovery behavior, and unexplained output drift.

- [ ] **Step 3: Trigger rollback on any defined failure**

  Restore the previous release atomically and record the failure, impact, restored commit, and follow-up migration task.

- [ ] **Step 4: Close only after all criteria pass**

  Require 14 calendar days without a rollback trigger, two successful scheduled production cycles, a successful rollback rehearsal, confirmed licensing, green CI/access, and explicit approval. Only then may repository archival or renaming be considered as a separate change.

## Final completion checklist

- [ ] Every legacy repository has a complete parity row and retained rollback commit.
- [ ] All required public code, tests, docs, configuration, CI, and runtime dependency locks are in `quant-platform`.
- [ ] All required private strategy code, tests, docs, evidence, configuration, CI, and runtime dependency locks are in `quant-research`.
- [ ] `market-intel` consumes the migrated artifact through the versioned contract and passes remote CI.
- [ ] `quant-platform` has an approved license and public-content review.
- [ ] `quant-research` private CI can authenticate and install private dependencies.
- [ ] `research-workspace` target manifest and compatibility checks pass before any gitlink changes.
- [ ] Production rollback has been rehearsed and the 14-day window has closed.
- [ ] Legacy repositories remain available until the final checklist is complete.
