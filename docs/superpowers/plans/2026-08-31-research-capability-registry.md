# Research Capability Registry Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a machine-readable capability registry for the current workspace, connect optional Trial Ledger references to ResearchSpec, and expose both checks through the existing local governance gates without creating a second implementation layer.

**Architecture:** The top-level workspace owns only cross-repository capability metadata and validation. Each capability points to a canonical owner repository source path/entrypoint plus evidence; the registry never wraps or reimplements owner logic. ResearchSpec gains an optional pointer into the merged `strategy-research` Trial Ledger, preserving all existing specs unchanged.

**Tech Stack:** Python 3.12+, PyYAML, pathlib, argparse, JSON, pytest, Ruff, ty, Git submodules.

**Spec:** `docs/superpowers/specs/2026-08-31-research-capability-trial-ledger-design.md`

## Global Constraints

- Owner repositories remain the only canonical implementation source.
- A capability may be listed only when its source path/contract and evidence can be located in the pinned workspace version.
- AFML, QuantSkills and papers may appear only as method references; their existence never proves workspace implementation.
- Capability maturity is implementation/research validation maturity, not expected return or investment confidence.
- `research_spec.v1.trial_ledger` is optional and backward-compatible.
- Existing historical specs, strategy lifecycles and `production_eligible` values remain unchanged.
- New governance checks use current local pre-push infrastructure; do not create a second CI system.

---

### Task 1: Define and validate `research_capability_registry.v1`

**Files:**
- Create: `docs/research-capabilities.yml`
- Create: `docs/research-capabilities.md`
- Create: `scripts/research_capability_registry_check.py`
- Create: `tests/test_research_capability_registry.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces YAML contract:

```yaml
schema_version: research_capability_registry.v1
capabilities: []
```

- Produces: `RegistryCheck(path: str, issues: list[str])` with `.ok`.
- Produces: `load_registry(path: Path) -> dict[str, Any]`.
- Produces: `validate_registry(path: Path, *, root: Path) -> RegistryCheck`.
- Produces CLI: `python scripts/research_capability_registry_check.py [--registry PATH] [--root PATH] [--json]`.

Each capability uses this shape:

```yaml
capability_id: governance.research_spec
summary: 机器校验 research_spec.v1 实验说明书和证据引用
owner_repository: research-workspace
stage: governance
kind: validation
maturity: verified
canonical_entrypoint:
  type: script
  value: python scripts/research_spec_check.py
  source_path: scripts/research_spec_check.py
inputs:
  - research_spec.v1
outputs:
  - research_spec_check.v1
requires: []
method_refs: []
evidence_refs:
  - tests/test_research_spec_check.py
```

Allowed `stage` values:

```text
data | feature | labeling | modeling | validation | portfolio | orchestration | execution | governance
```

Allowed `kind` values:

```text
computation | validation | contract | orchestration | monitoring
```

Allowed `maturity` values:

```text
experimental | runnable | verified | deprecated
```

- [ ] **Step 1: Write failing registry tests**

Create `tests/test_research_capability_registry.py` that writes temporary YAML registries and proves:

```python
from scripts.research_capability_registry_check import validate_registry


def test_valid_registry_passes(tmp_path):
    ...
    assert validate_registry(registry, root=workspace).ok
```

Add RED cases for duplicate `capability_id`, unknown owner, missing `requires`, dependency cycle, missing `source_path`, missing evidence, private entrypoint path containing a path segment beginning `_`, and `verified` without at least one test evidence path containing `/tests/` or beginning `tests/`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run --locked python -m pytest tests/test_research_capability_registry.py -q
```

Expected: import failure because the validator does not exist.

- [ ] **Step 3: Implement the registry validator**

Use `yaml.safe_load`. Define the canonical owner set exactly as:

```python
OWNER_REPOSITORIES = {
    "research-workspace",
    "market-data-platform",
    "deep-learning-tick-data-prediction",
    "alpha-research",
    "portfolio-backtester",
    "strategy-research",
    "strategy-app",
    "strategy-pipeline",
    "quant-execution-engine",
}
```

Resolve `source_path` and `evidence_refs` relative to the owner repository root; for `research-workspace`, use the workspace root directly. Reject paths escaping their owner root. Validate IDs with `^[a-z0-9][a-z0-9._-]*$`, dependency existence, and dependency cycles using DFS.

For `maturity=runnable`, require an existing source path and non-empty evidence. For `verified`, additionally require at least one existing test evidence path. `experimental` still requires an owner and at least one existing source or evidence path. `deprecated` requires either a non-empty `replacement` capability ID or a non-empty `deprecation_reason`.

- [ ] **Step 4: Add JSON and human CLI output**

`--json` must emit:

```json
{
  "schema_version": "research_capability_registry_check.v1",
  "ok": true,
  "issues": [],
  "capability_count": 4
}
```

Exit 0 only when validation passes.

- [ ] **Step 5: Run targeted tests and verify GREEN**

```bash
uv run --locked python -m pytest tests/test_research_capability_registry.py -q
```

- [ ] **Step 6: Add the new validator to ty coverage**

Add `scripts/research_capability_registry_check.py` to `[tool.ty.src].include` in `pyproject.toml`.

- [ ] **Step 7: Commit the registry contract and validator**

```bash
git add docs/research-capabilities.yml docs/research-capabilities.md scripts/research_capability_registry_check.py tests/test_research_capability_registry.py pyproject.toml
git commit -m "feat: add research capability registry"
```

---

### Task 2: Seed only capabilities verified in the pinned workspace

**Files:**
- Modify: `docs/research-capabilities.yml`
- Modify: `tests/test_research_capability_registry.py`

**Interfaces:**
- Adds metadata only; no owner code is changed in this task.

- [ ] **Step 1: Inventory candidate capabilities against pinned sources**

Check source paths and tests before listing. The first seed set should prioritize capabilities already documented in `docs/afml-methodology-rollout.md` plus governance capabilities. Candidate names include:

```text
governance.research_spec
governance.strategy_evidence_gate
governance.decision_governance
governance.trial_ledger
alpha.triple_barrier
alpha.meta_labeling
alpha.uniqueness_weighting
alpha.sequential_bootstrap
alpha.purged_cross_validation
alpha.cpcv
portfolio.probabilistic_sharpe
portfolio.strategy_failure_probability
portfolio.hrp
portfolio.calibrated_sizing
portfolio.capacity_analysis
execution.handoff_audit
```

A candidate is omitted if no public/canonical source path plus evidence can be identified in the pinned submodule. Do not invent API names to make the table look complete.

- [ ] **Step 2: Add a test that the committed registry validates against the real workspace tree**

```python
def test_committed_registry_is_valid():
    root = Path(__file__).resolve().parents[1]
    result = validate_registry(root / "docs/research-capabilities.yml", root=root)
    assert result.ok, result.issues
```

- [ ] **Step 3: Populate the verified seed entries**

For method references use explicit records such as:

```yaml
method_refs:
  - type: afml
    ref: chapter-7-cross-validation-in-finance
```

or:

```yaml
method_refs:
  - type: external
    ref: https://github.com/quantskills/skill-backtest-overfit
```

External method references remain documentation only and are not checked as workspace paths.

- [ ] **Step 4: Validate the committed registry**

```bash
uv run --locked python scripts/research_capability_registry_check.py
uv run --locked python -m pytest tests/test_research_capability_registry.py -q
```

- [ ] **Step 5: Commit the seed inventory**

```bash
git add docs/research-capabilities.yml tests/test_research_capability_registry.py
git commit -m "docs: seed verified research capabilities"
```

---

### Task 3: Connect optional Trial Ledger references to ResearchSpec

**Files:**
- Modify: `scripts/research_spec_check.py`
- Modify: `tests/test_research_spec_check.py`
- Modify: `docs/research-spec.md`

**Interfaces:**
- Adds optional top-level ResearchSpec object:

```json
"trial_ledger": {
  "path": "trial-ledger/<experiment_id>.jsonl",
  "multiple_testing_family": "volume-price-v1"
}
```

- Existing specs without `trial_ledger` remain valid.

- [ ] **Step 1: Add failing backward-compatibility and linkage tests**

Keep an existing valid fixture/spec unchanged and prove it still passes. Add a spec with `trial_ledger` and a temporary `strategy-research/trial-ledger/<experiment_id>.jsonl`. Tests must fail when the path is missing, any ledger row has another `experiment_id`, or the declared `multiple_testing_family` has no row with `multiple_testing.counted=true`.

- [ ] **Step 2: Run ResearchSpec tests and verify RED only for new linkage cases**

```bash
uv run --locked python -m pytest tests/test_research_spec_check.py -q
```

- [ ] **Step 3: Implement `_check_trial_ledger()`**

The top-level checker should parse JSONL directly rather than import the private submodule script. This is cross-repository contract validation, not a duplicate statistical validator. It checks only linkage semantics:

```python
path exists
all row experiment_id == research_spec.experiment_id
at least one row has multiple_testing.family_id == declared family and counted is True
```

Do not duplicate parent graph, fingerprint or final-OOS validation; those remain owned by `strategy-research/scripts/trial_ledger_check.py`.

- [ ] **Step 4: Document the optional field**

Update `docs/research-spec.md` with the exact object shape, explain when automated/grid/genetic/Agent searches should use it, and state that one-off exploratory diagnostics may omit it.

- [ ] **Step 5: Run ResearchSpec tests and verify GREEN**

```bash
uv run --locked python -m pytest tests/test_research_spec_check.py -q
python scripts/research_spec_check.py
```

- [ ] **Step 6: Commit ResearchSpec linkage**

```bash
git add scripts/research_spec_check.py tests/test_research_spec_check.py docs/research-spec.md
git commit -m "feat: link research specs to trial ledgers"
```

---

### Task 4: Wire governance checks into existing local gates

**Files:**
- Modify: `scripts/run_pre_push_checks.py`
- Modify: `tests/test_pre_push_hooks.py`
- Modify: `tests/test_pre_push_hook_integration.py`
- Modify: `docs/script-lifecycle.yml`
- Modify: `docs/quality-governance.md`

**Interfaces:**
- Adds top-level pre-push check `research-capability-registry`.
- Adds a strategy-research delegated check that runs `python scripts/trial_ledger_check.py` only when the pinned submodule contains that script.

- [ ] **Step 1: Add failing tests for the new pre-push commands**

Extend existing pre-push command-list assertions to require a root command equivalent to:

```text
python scripts/research_capability_registry_check.py
```

and a delegated strategy-research command equivalent to:

```text
python scripts/trial_ledger_check.py
```

The strategy-research check must run from the submodule repository root.

- [ ] **Step 2: Implement gate registration without copying validation logic**

Add commands through the same `CheckSpec`/command construction patterns already used by `run_pre_push_checks.py`. Do not shell-inline YAML/JSON parsing.

- [ ] **Step 3: Register the new root script lifecycle record**

Add `scripts/research_capability_registry_check.py` to `docs/script-lifecycle.yml` with owner `research-workspace`, purpose `Validate the cross-repository research capability registry`, lifecycle `governance`, `safe_to_run_locally: true`, and no external dependency beyond the pinned workspace tree and PyYAML.

- [ ] **Step 4: Update quality-governance documentation**

Document capability registry validation and trial-ledger delegation as local governance checks. Do not describe disabled GitHub Actions as active CI.

- [ ] **Step 5: Run targeted pre-push tests**

```bash
uv run --locked python -m pytest tests/test_pre_push_hooks.py tests/test_pre_push_hook_integration.py -q
```

- [ ] **Step 6: Commit gate integration**

```bash
git add scripts/run_pre_push_checks.py tests/test_pre_push_hooks.py tests/test_pre_push_hook_integration.py docs/script-lifecycle.yml docs/quality-governance.md
git commit -m "chore: gate capability and trial ledger governance"
```

---

### Task 5: Pin the merged strategy-research owner revision and verify the integration PR

**Files:**
- Modify: `strategy-research` gitlink
- Modify: `docs/version-matrix.md` only if the repository's normal version-matrix workflow requires a refreshed row for the new gitlink.

**Interfaces:**
- The parent repository must point to the merged `strategy-research/main` commit containing Trial Ledger.

- [ ] **Step 1: Confirm the owner PR is merged**

Do not pin an unmerged feature-branch SHA. Resolve the merged `strategy-research/main` revision and update the gitlink to that commit.

- [ ] **Step 2: Run the complete relevant root gates**

```bash
uv run --locked python -m pytest tests/test_research_capability_registry.py tests/test_research_spec_check.py tests/test_pre_push_hooks.py tests/test_pre_push_hook_integration.py -q
python scripts/research_capability_registry_check.py
python scripts/research_spec_check.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
```

- [ ] **Step 3: Review the diff for owner-boundary regressions**

Confirm no top-level computation duplicates owner logic; registry entries resolve only to real pinned paths; no strategy lifecycle or production status changes; and no large research artifact was added.

- [ ] **Step 4: Open the integration PR**

Use title:

```text
feat: add research capability and trial accounting governance
```

The PR body must link the merged Trial Ledger owner PR, list exact test commands/results, enumerate capability seed entries, state that external method references are documentation-only, and explain backward compatibility for ResearchSpec.
