# Strategy Research Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move strategy research ownership out of `strategy-pipeline` while keeping the public pipeline responsible for orchestration, publication, runtime safety, and execution handoff.

**Architecture:** `strategy-research` owns private experiment specifications, research configurations, proprietary runner logic, and research evidence. `strategy-app` owns reusable strategy-specific calculations and contracts. `strategy-pipeline` keeps thin public launchers, input loading, publication, receipts, CLI wiring, and `targets.json` handoff. The pipeline must not import the private repository as a required Python dependency.

### Boundary decision (2026-08-29)

The file-level audit found that the remaining DailyWatch20 and Hotsector
commands still own asset loading, resource bounds, fail-closed validation,
publication, receipts, credentials, or execution handoff. They are therefore
public control-plane adapters, not private research implementations. Their
deterministic strategy calculations have been delegated to `strategy-app`, and
the genuinely private runners remain in `strategy-research`. Mechanically
moving the adapters would create the prohibited private-to-pipeline runtime
dependency, so `runner_manifest.json` is the replacement boundary artifact.

**Tech Stack:** Python 3.12+, `uv`, setuptools packages, YAML/JSON experiment contracts, pytest, ruff, Git submodules, GitHub private repository.

**Spec:** Existing boundary records in `strategy-pipeline/docs/internal/documentation-ownership-inventory.md`, `strategy-pipeline/docs/internal/data-ops-boundary-inventory.md`, and `docs/adr/0006-strategy-knowledge-and-runtime-boundaries.md`.

## Global Constraints

- `strategy-research` remains a private GitHub repository and a locked submodule of `research-workspace`.
- `strategy-pipeline` must remain runnable without initializing the private submodule for public smoke checks.
- No strategy-research code may import `strategy_pipeline` as a required runtime dependency after extraction.
- Publication, freshness, fail-closed validation, run receipts, and execution-target export remain in `strategy-pipeline` or the appropriate owner repository.
- Reusable signal, feature, ranking, and strategy contracts belong in `strategy-app` or `alpha-research`, not in the private experiment directory.
- Every moved file must have a replacement path, an updated reference, and a focused test or an explicit historical-archive justification.

---

### Task 1: Create the private research configuration contract

**Files:**
- Create: `strategy-research/experiments/configs/README.md`
- Create: `strategy-research/experiments/configs/manifest.json`
- Modify: `strategy-pipeline/configs/experiments/README.md`
- Modify: `strategy-pipeline/src/strategy_pipeline/config_utils.py`
- Test: `strategy-pipeline/tests/test_config_utils.py`
- Test: `tests/test_private_research_config_boundary.py`

**Interfaces:**
- `strategy-research/experiments/configs/manifest.json` records each private config path, lifecycle, parent config, and required public owner APIs.
- `strategy-pipeline.config_utils.resolve_pipeline_config()` continues resolving public presets and accepts an explicit path under `strategy-research/experiments/configs/` when the submodule is initialized.
- A missing private submodule produces a clear `FileNotFoundError` naming the initialization command, rather than silently falling back to a public config.

- [x] **Step 1: Write the boundary tests**

Add tests that assert public presets resolve without the private submodule, an initialized private config resolves by explicit path, and an absent private path fails with `git submodule update --init strategy-research` in the error.

- [x] **Step 2: Run the tests to verify the new contract fails**

Run:

```bash
uv run --project strategy-pipeline --extra dev python -m pytest tests/test_private_research_config_boundary.py strategy-pipeline/tests/test_config_utils.py -q
```

Expected: the new private-config assertions fail before implementation.

- [x] **Step 3: Add the private manifest and resolver behavior**

Keep `configs/presets/` and `configs/catalog.csv` public. Register only active research variants, diagnostics, and sweeps in the private manifest. Make the resolver distinguish public aliases from explicit private paths and never search the private directory implicitly for a public alias.

- [x] **Step 4: Update config documentation and references**

Document the private config root, initialization command, and the rule that `config.used.yml` is copied into each run directory so later audit does not require the submodule.

- [x] **Step 5: Run the focused tests and commit each repository separately**

Run the focused tests, then commit the private repo and pipeline changes independently before updating the parent gitlink.

---

### Task 2: Extract DailyWatch20 research ownership behind public adapters

**Files:**
- Create: `strategy-research/experiments/pipeline_research/daily_watch20_candidate_oos.py`
- Create: `strategy-research/experiments/pipeline_research/daily_watch20_fundamental_shadow.py`
- Create: `strategy-research/experiments/pipeline_research/daily_watch20_incumbent_challenger.py`
- Create: `strategy-research/experiments/pipeline_research/daily_watch20_long_horizon_buffer.py`
- Create: `strategy-research/experiments/pipeline_research/daily_watch20_minute_campaign.py`
- Create: `strategy-research/experiments/pipeline_research/daily_watch20_slow_volume_campaign.py`
- Modify: `strategy-pipeline/scripts/research/*.py` for the six corresponding thin launchers
- Modify: `strategy-pipeline/src/strategy_pipeline/daily_watch20_*` only where an input/publication adapter is required
- Test: `strategy-research/tests/test_pipeline_research_launchers.py`
- Test: existing DailyWatch20 pipeline tests

**Interfaces:**
- Each private runner exposes the existing CLI arguments and returns a JSON-serializable result summary.
- Each public launcher resolves the private runner by an explicit submodule path, forwards arguments, and exits with a clear private-submodule error when unavailable.
- Input bundles, owner API calls, output schemas, publication receipts, and fail-closed checks retain their existing contracts.

- [x] **Step 1: Characterize current behavior**

Use the existing pipeline tests and each runner’s `--help` output to record arguments, imports, output paths, and receipt fields before moving implementation.

- [x] **Step 2: Add ownership/launcher boundary tests**

The ownership manifest test replaces a private launcher test for the retained
adapters: they must remain runnable without the private submodule and must not
duplicate private implementation. Explicit private runners keep their own
CLI tests in `strategy-research`.

- [x] **Step 3: Move research-only calculations and experiment assembly**

Move only code that builds research candidates, challenger variants, or experiment reports. Keep asset loading, publication, receipt validation, and operational path handling in public adapters or owner APIs.

- [x] **Step 4: Replace old scripts with thin launchers or retain explicit adapters**

Keep the existing script names where external runbooks depend on them. The launcher must not duplicate the research implementation.

- [x] **Step 5: Run DailyWatch20 tests and commit**

Run the six existing runner-related test files plus the new private launcher tests. Commit the private repo first, then the pipeline repo, then update the workspace gitlink.

---

### Task 3: Extract Hotsector research internals while retaining operational controls

**Files:**
- Create: `strategy-research/experiments/pipeline_research/hotsector_challenger_campaign.py`
- Create: `strategy-research/experiments/pipeline_research/hotsector_deepseek_campaign.py`
- Create: `strategy-research/experiments/pipeline_research/hotsector_deepseek_v4_month.py`
- Create: `strategy-research/experiments/pipeline_research/hotsector_ai_shadow.py`
- Create: `strategy-research/experiments/pipeline_research/hotsector_ai_shadow_observation.py`
- Modify: `strategy-pipeline/src/strategy_pipeline/hotsector_*.py`
- Modify: `strategy-pipeline/scripts/research/hotsector_*.py`
- Test: `strategy-research/tests/test_hotsector_pipeline_research.py`
- Test: existing Hotsector pipeline and strategy-app tests

**Interfaces:**
- Private modules own experiment composition, model/API-specific research decisions, and report interpretation.
- Public modules own credential boundaries, external-call controls, append-only artifact publication, validation, and operational receipts.
- No private module writes to a production target path or calls the execution engine directly.

- [x] **Step 1: Add ownership tests**

Assert that private experiment modules contain no `strategy_pipeline` imports and public modules retain the publication and credential guard functions.

- [x] **Step 2: Extract pure experiment assembly**

Move the portions that construct challenger arms, prompts, analysis variants, and research reports into the private repository. Keep API invocation and publication adapters explicit.

- [x] **Step 3: Add public compatibility launchers or retain control-plane entrypoints**

Preserve the current command names and artifact schemas. The launcher must fail closed if the private implementation is unavailable.

- [x] **Step 4: Run Hotsector focused tests and commit**

Run the private tests, pipeline shadow tests, and no-external-send tests before updating the parent gitlink.

---

### Task 4: Move reusable strategy-specific calculations to `strategy-app`

**Files:**
- Modify: `strategy-app/src/strategy_app/daily_watch20/` modules identified by the ownership scan
- Modify: `strategy-app/src/strategy_app/hotsector/` modules identified by the ownership scan
- Remove: duplicate pure calculation implementations remaining in `strategy-pipeline`
- Test: `strategy-app/tests/test_strategy_app_ownership.py`
- Test: `strategy-pipeline/tests/test_strategy_app_*ownership.py`

**Interfaces:**
- Strategy-app public APIs own deterministic ranking, feature-combination, campaign-contract, and strategy-policy calculations.
- Strategy-pipeline imports only public strategy-app APIs and retains orchestration and publication facades where needed for compatibility.

- [x] **Step 1: Generate a duplicate and import-boundary inventory**

Compare function definitions and imports in the pipeline strategy modules against `strategy_app` and `alpha_research`. Do not move code solely because a filename contains `strategy`.

- [x] **Step 2: Add an ownership regression test**

Fail if a new pure strategy calculation is added under `strategy_pipeline` when the corresponding owner API already exists.

- [x] **Step 3: Move only duplicated pure calculations**

Use a public owner API and preserve compatibility imports only where existing callers require them. Leave output schemas and runtime guards in the pipeline.

- [x] **Step 4: Run owner and pipeline tests, then commit**

Run the relevant strategy-app suite and pipeline import-boundary suite before updating the workspace version matrix.

---

### Task 5: Finalize documentation, submodule pointers, and full verification

**Files:**
- Modify: `README.md`
- Modify: `.gitmodules`
- Modify: `docs/strategy-satellites.md`
- Modify: `strategy-pipeline/docs/internal/documentation-ownership-inventory.md`
- Modify: `strategy-pipeline/docs/internal/strategy-pipeline-transition.md`
- Modify: `strategy-pipeline/scripts/README.md`
- Modify: `tests/test_gitmodules.py`
- Modify: `tests/test_strategy_research_catalog.py`

- [x] **Step 1: Search for stale paths and duplicate implementations**

Search for every moved filename, old `scripts/research/` path, and `strategy_pipeline` import from private research code.

- [ ] **Step 2: Run all relevant verification**

The owner and pipeline suites, focused workspace boundary suites, and
`workspace_doctor` pass. The root suite currently reports three pre-existing
workspace-accounting failures: the maintainability evidence is stale relative
to the checked-out submodule sources, one accepted-hotspot path was removed in
the dirty alpha checkout, and the owner-native namespace manifest does not
match the dirty alpha/market-data gitlinks. These must be reconciled only after
those submodule changes are intentionally committed and pinned; this plan does
not overwrite them.

Run:

```bash
uv run --locked --extra dev python -m pytest tests -q
uv run --project strategy-pipeline --extra dev python -m pytest strategy-pipeline/tests -q
uv run --locked --extra dev python -m pytest strategy-research/tests -q
python scripts/workspace_doctor.py
```

- [x] **Step 3: Verify GitHub and submodule invariants**

Confirm the private repo is private, the parent gitlink points to the pushed private commit, all moved files exist exactly once, and public smoke checks do not require private source checkout.

- [x] **Step 4: Commit and push repository pointers**

Push private repo changes, owner-repo changes, pipeline changes, and finally the parent workspace pointer. Preserve unrelated dirty changes in other submodules.
