# Documentation, Tests, and Quality-Gate Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the workspace documentation clearly distinguish active strategy research from optional E2 production-readiness audits, add regression tests that prevent the distinction and current lifecycle state from drifting, and make the root type-check command use its declared dependencies.

**Architecture:** Keep strategy identity and lifecycle statements in `strategy-research`, cross-repository priority and evidence-gate behavior in top-level `docs`, and test those contracts from the existing documentation, evidence-gate, and root-quality test modules. Do not change production strategy code, promotion schemas, submodule ownership, or ignored run artifacts in this cleanup.

**Tech Stack:** Markdown, JSON-backed project metadata, Python `pytest`, existing top-level documentation and evidence-gate scripts.

**Spec:** `docs/roadmap.md`, `docs/strategy-evidence-gate.md`, `strategy-research/README.md`, `strategy-research/catalog.json`, and `AGENTS.md`.

## Global Constraints

- The current five production-gated strategies remain `production_eligible: false`.
- E2 remains an `in_progress` production-readiness evidence track, not an active strategy identity.
- Generic `strategy run --config ...` remains a configurable workflow and must not be documented as a strategy.
- Do not claim local ignored artifacts are canonical or production-ready.
- Do not modify public APIs, asset keys, submodule pins, or ignored run artifacts. Refresh the generated maintainability baseline only when required by changed root Python files.
- Run documentation link/style checks and the focused evidence-gate tests before completion.

---

### Task 1: Add regression tests for the research-versus-promotion distinction

**Files:**
- Modify: `tests/test_documentation_entrypoints.py`
- Modify: `tests/test_strategy_evidence_gate.py`

**Interfaces:**
- Consumes: current roadmap, strategy-evidence guide, strategy-research README, and catalog JSON.
- Produces: tests that fail if E2 is presented as active strategy research or if the generic candidate is registered as a real strategy.

- [x] **Step 1: Write the failing documentation contract test**

Add a `test_e2_is_documented_as_a_promotion_audit` test to `tests/test_documentation_entrypoints.py`. It must read `docs/roadmap.md`, `docs/strategy-evidence-gate.md`, and `strategy-research/README.md`, then assert that:

```python
assert "生产准备审计" in roadmap
assert "不替代当前策略研究" in roadmap
assert "production-readiness audit" in evidence_gate
assert "not active strategy research" in evidence_gate
assert "E2" in strategy_research_readme
```

Use the existing test file’s style and keep the assertions tied to explicit wording introduced by Task 2.

- [x] **Step 2: Run the focused test and verify the expected failure**

Run:

```bash
uv run --project strategy-pipeline --extra dev pytest tests/test_documentation_entrypoints.py::test_e2_is_documented_as_a_promotion_audit -q
```

Expected: FAIL because the new status wording is not yet present.

- [x] **Step 3: Write the failing catalog/gate state test**

Add a `test_real_catalog_keeps_e2_candidates_outside_strategy_identity` test to `tests/test_strategy_evidence_gate.py`. It must load `strategy-research/catalog.json` and assert:

```python
ids = {item["id"] for item in catalog["strategies"]}
required = {
    "daily_watch20",
    "hotsector",
    "style_replica_a80_b20",
    "d11_h5_shadow",
    "dividend_growth_momentum",
}
assert required <= ids
assert "a_share_e2_promotion_candidate_20260825" not in ids
assert all(item["production_eligible"] is False for item in catalog["strategies"] if item["id"] in required)
```

- [x] **Step 4: Run the catalog test**

Run:

```bash
uv run --project strategy-pipeline --extra dev pytest tests/test_strategy_evidence_gate.py::test_real_catalog_keeps_e2_candidates_outside_strategy_identity -q
```

Expected: PASS, because the current catalog already preserves this boundary.

---

### Task 2: Refresh active documentation status and priorities

**Files:**
- Modify: `docs/roadmap.md:30-100`
- Modify: `docs/strategy-evidence-gate.md:1-115`
- Modify: `strategy-research/README.md:29-60`
- Modify: `docs/README.md:55-90`

**Interfaces:**
- Consumes: the current catalog, evidence policy, current E2 diagnostic findings, and the tests from Task 1.
- Produces: consistent wording that active research is primary, E2 is a conditional audit, and ignored diagnostic artifacts are not canonical evidence.

- [x] **Step 1: Add the explicit priority statement to the roadmap**

In the roadmap status section before the unfinished-project table, add a short English-compatible machine-checkable phrase in the existing Chinese prose:

```text
E2 是生产准备审计（production-readiness audit），不替代当前策略研究。当前优先级仍是推进已登记策略的投资假设、信号和组合实验；只有选定真实策略候选后，才运行该策略的完整 E2 审计。
```

Update the E2 row so it says the producer tooling and local diagnostic runs exist, but no current canonical promotion set exists; preserve `in_progress`.

- [x] **Step 2: Clarify the evidence-gate purpose**

Add a section after `为什么需要证据门禁` in `docs/strategy-evidence-gate.md` with this meaning:

```text
E2 的定位是 production-readiness audit，不是 active strategy research。它检查已经选定的策略候选能否形成可复核的长窗口、成本、容量、执行和 lineage 证据。它不创建新的策略，也不要求每个探索中的实验立即完成全部晋级检查。
```

Update `last_verified` to `2026-08-26` and state that the current five catalog strategies remain non-production-eligible. State that a generic `strategy run` candidate must not be attached to a catalog strategy without an explicit strategy specification.

- [x] **Step 3: Clarify the strategy-research lifecycle guidance**

In `strategy-research/README.md`, add E2 to the lifecycle section and state that the sequence is:

```text
active strategy research → stable candidate → focused E2 audit → production decision
```

Retain the existing rule that `strategy run --config ...` is not itself a strategy.

- [x] **Step 4: Update the documentation navigation’s current-facts wording**

In `docs/README.md`, replace the current-facts wording that implies E2 evidence is simply waiting to be generated with wording that distinguishes:

- diagnostic producer runs may exist locally;
- canonical promotion evidence is still incomplete;
- E2 is secondary to selecting and researching a real strategy candidate.

- [x] **Step 5: Run the documentation contract test and style/link checks**

Run:

```bash
uv run --project strategy-pipeline --extra dev pytest tests/test_documentation_entrypoints.py::test_e2_is_documented_as_a_promotion_audit -q
uv run --project strategy-pipeline --extra dev pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py -q
```

Expected: PASS with no missing links or documentation-style violations.

---

### Task 3: Run the evidence-gate and repository quality verification

**Files:**
- Modify: `scripts/run_quality_checks.py`
- Modify: `tests/test_root_quality.py`
- Regenerate: `docs/evidence/maintainability/baseline-20260719-ty.json`
- No production strategy files created.
- Verify: `tests/test_strategy_evidence_gate.py`, `tests/test_promotion_evidence_contract.py`, `tests/test_docs_links.py`, `tests/test_documentation_entrypoints.py`, `tests/test_root_quality.py`

**Interfaces:**
- Consumes: the updated documentation and existing gate implementation.
- Produces: fresh verification evidence that lifecycle, canonical-promotion, and documentation contracts remain intact.

- [x] **Step 1: Run focused evidence-gate tests**

```bash
uv run --project strategy-pipeline --extra dev pytest tests/test_strategy_evidence_gate.py tests/test_promotion_evidence_contract.py -q
```

Expected: all tests pass.

- [x] **Step 2: Run the top-level documentation and repository contract tests**

```bash
uv run --project strategy-pipeline --extra dev pytest tests/test_docs_links.py tests/test_documentation_entrypoints.py tests/test_strategy_research_catalog.py -q
```

Expected: all tests pass.

- [x] **Step 3: Run the workspace quality profile**

```bash
python scripts/run_quality_checks.py --profile hard
```

Expected: exit code 0, with only already-budgeted warnings if reported. The root `ty` command must run through `uv` with the workspace project so imports such as `yaml` resolve from declared dependencies.

- [x] **Step 4: Review the diff and confirm no ignored artifacts were added**

```bash
git status --short
git diff --check
git diff --stat
```

Expected: only the plan, documentation, root quality runner/test, and generated baseline listed above are changed; no `artifacts/`, generated data, or absolute local paths are staged.

- [x] **Step 5: Commit the cleanup**

```bash
git add docs/superpowers/plans/2026-08-26-docs-tests-cleanup.md docs/roadmap.md docs/strategy-evidence-gate.md docs/README.md strategy-research/README.md scripts/run_quality_checks.py tests/test_documentation_entrypoints.py tests/test_root_quality.py tests/test_strategy_evidence_gate.py docs/evidence/maintainability/baseline-20260719-ty.json
git commit -m "docs: clarify research and evidence priorities"
```
