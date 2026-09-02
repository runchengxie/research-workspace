# Cross-Sectional ML Research Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one durable cross-sectional ML research agenda and one workspace hygiene policy without creating a new repository or runtime dependency.

**Architecture:** Keep research hypotheses in `strategy-research` and cross-repository lifecycle rules in the workspace docs. Reuse the owner boundaries already accepted in ADR-0006 and treat capability extraction plus archiving as the mechanism for controlling research growth.

**Tech Stack:** Markdown, existing GitHub multi-repository workspace, existing strategy-research lifecycle and evidence governance.

**Spec:** `docs/superpowers/specs/2026-09-02-cross-sectional-ml-research-governance-design.md`

## Global Constraints

- Do not create a new repository.
- Do not modify runtime code, package dependencies, strategy lifecycle, or production eligibility.
- Standard ranking-learning taxonomy is pointwise, pairwise, listwise; do not introduce `rank-wise` as a peer category.
- Keep research hypotheses in `strategy-research` and reusable implementation in the existing owner repositories.
- Research GC is a review process, not an automatic age-based deletion job.

---

### Task 1: Cross-sectional ML research agenda

**Files:**
- Create: `strategy-research/research/cross_sectional_ml_research_agenda.md`

**Interfaces:**
- Consumes: existing Fundamental State Forecasting experiment, style-factor findings, ADR-0006 ownership boundaries.
- Produces: one research map covering horizons, targets, ranking objectives, model phenotype and falsification criteria.

- [ ] **Step 1: Write the research questions**

Cover prediction horizon, return vs fundamental targets, stable-compounder omission, attention/catalyst mechanisms, valuation bridge, and A-share competing explanations.

- [ ] **Step 2: Define ranking-learning comparisons**

Define pointwise return regression, pointwise rank regression, pairwise ranking and listwise top-k ranking. State explicitly that `rank-wise` is not a fourth standard category.

- [ ] **Step 3: Define an experiment matrix**

Cross target family, horizon, learning objective and evaluation. Require model-phenotype diagnostics in addition to return metrics.

- [ ] **Step 4: Add falsification and escalation rules**

Require persistence/simple baselines, PIT-safe walk-forward, exposure attribution and explicit negative-result recording before model-complexity escalation.

- [ ] **Step 5: Commit**

```bash
git add strategy-research/research/cross_sectional_ml_research_agenda.md
git commit -m "research: add cross-sectional ML research agenda"
```

### Task 2: Workspace hygiene and capability extraction policy

**Files:**
- Create: `docs/research-lifecycle-and-workspace-hygiene.md`

**Interfaces:**
- Consumes: `docs/documentation-lifecycle.md`, `docs/maintainability-governance.md`, `docs/research-decision-governance.md`, ADR-0006.
- Produces: cross-repository rules for active research, extraction, archive, deletion and future repository splitting.

- [ ] **Step 1: Define the three asset classes**

Document living infrastructure, active research and historical knowledge, including their authoritative owner locations.

- [ ] **Step 2: Define capability extraction triggers**

Require extraction when a capability is reused by two research lines, becomes a stable public contract, or duplicates an existing owner responsibility.

- [ ] **Step 3: Define quarterly Research GC**

Review stalled/rejected experiments, duplicated implementations, superseded docs/configs, orphaned evidence and already-extracted experiment code. Each item receives retain, extract, archive, supersede or delete.

- [ ] **Step 4: Define evidence retention and deletion boundaries**

Preserve thesis, key config, data/code versions, results, failure reason and evidence references; do not require indefinite retention of bulky ignored artifacts.

- [ ] **Step 5: Define future repository split triggers**

Require independent ownership, release cadence and stable contracts. Explicitly reject splitting solely because a directory has become large.

- [ ] **Step 6: Commit**

```bash
git add docs/research-lifecycle-and-workspace-hygiene.md
git commit -m "docs: define research workspace hygiene policy"
```

### Task 3: Navigation and consistency review

**Files:**
- Modify: `docs/README.md`

**Interfaces:**
- Consumes: documents from Tasks 1 and 2.
- Produces: discoverable workspace navigation without duplicating their contents.

- [ ] **Step 1: Add navigation links**

Add the research agenda and workspace hygiene policy to the recommended-reading or reference section.

- [ ] **Step 2: Check consistency against accepted governance**

Verify that the new docs do not move strategy identity out of `strategy-research`, do not move reusable alpha/portfolio code into strategy docs, and do not create a new lifecycle value.

- [ ] **Step 3: Run documentation-oriented checks when the full workspace checkout is available**

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/workspace_doctor.py
```

If the current environment cannot execute these commands, record them as pending in the PR instead of claiming success.

- [ ] **Step 4: Commit and open a draft PR**

```bash
git add docs/README.md
git commit -m "docs: link research agenda and hygiene policy"
```

The PR description must state that this is documentation/governance only and does not add ranking implementations yet.
