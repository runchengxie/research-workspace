# Platform Publication Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fail-closed, versioned publication manifest for handing approved research projections to the Dashboard and market-intel without cross-repository runtime imports.

**Architecture:** `research_contracts` owns the canonical handoff metadata. The manifest contains only producer identity, safe relative paths, schemas, hashes, disclosure audience, and consumer declarations. Downstream surfaces copy and validate projection files; research computation remains in owner repositories.

**Tech Stack:** Python 3.12, stdlib dataclasses/pathlib/datetime, pytest, existing `research_contracts` package.

**Spec:** `docs/superpowers/specs/2026-09-02-platform-publication-and-research-platform-design.md`

## Global Constraints

- Do not import research owner runtime code into market-intel or trading-research-dashboard.
- Public consumers must fail closed on internal artifacts explicitly targeted at them.
- Publication paths are relative POSIX paths and may not escape the publication root.
- The manifest carries no raw market data, model object, broker object, or third-party framework object.
- Existing artifact-envelope v2 remains valid and unchanged.

---

### Task 1: Define publication contract behavior

**Files:**
- Create: `tests/test_platform_publication.py`
- Create: `src/research_contracts/platform_publication.py`
- Modify: `src/research_contracts/__init__.py`

**Interfaces:**
- Produces: `PlatformPublicationArtifact`, `PlatformPublicationManifest`, `load_platform_publication_manifest()`.
- Consumes: only Python standard library types.

- [x] **Step 1: Write failing tests for round-trip, path traversal, disclosure firewall, and consumer filtering**

The test imports the new public symbols and asserts public projection round-trip, `../` rejection, internal-to-public failure, and consumer selection.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
uv run --project strategy-pipeline --extra dev python -m pytest tests/test_platform_publication.py -q
```

Expected before implementation: import failure for the new symbols.

The connected editing environment cannot execute the workspace checkout; this verification must be run before merge and is not claimed as completed here.

- [x] **Step 3: Implement the minimal contract**

Implement immutable dataclasses, timezone-aware generation timestamps, lowercase SHA-256 validation, safe relative POSIX paths, unique artifact ids/paths, audience validation, and consumer filtering.

- [ ] **Step 4: Run focused and root contract tests**

```bash
uv run --project strategy-pipeline --extra dev python -m pytest \
  tests/test_platform_publication.py \
  tests/test_artifact_envelope.py \
  tests/test_artifact_contract_manifest.py -q
```

Expected: PASS.

- [x] **Step 5: Export the new contract from `research_contracts`**

Public exports:

```python
PLATFORM_PUBLICATION_SCHEMA_VERSION
PUBLICATION_AUDIENCES
PlatformPublicationArtifact
PlatformPublicationManifest
load_platform_publication_manifest
```

### Task 2: Document platform ownership and external-framework boundaries

**Files:**
- Create: `docs/superpowers/specs/2026-09-02-platform-publication-and-research-platform-design.md`
- Create: `docs/superpowers/plans/2026-09-02-platform-publication-contract.md`

**Interfaces:**
- Consumes: existing ADR-0001/ADR-0006 boundaries.
- Produces: approved ownership and adoption guidance for downstream PRs.

- [x] **Step 1: Record three-plane topology**

Define research, intelligence/distribution, and presentation planes while preserving repository independence.

- [x] **Step 2: Record framework roles**

Specify vectorbt as screening, RQAlpha as differential backtest reference, Qlib as existing optional dataset/trainer backend, portfolio libraries as optimizer candidates, vn.py as execution transport candidate, and NautilusTrader as research/live-parity reference.

- [x] **Step 3: Record capability roadmap**

Cover risk model, optimizer, attribution, factor catalog, live drift, and logical asset registry without creating a nested superproject.

### Task 3: Merge gate

**Files:** none

- [ ] **Step 1: Run workspace quality gates**

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
python src/research_contracts/smoke_contracts.py
```

- [ ] **Step 2: Review the publication contract for accidental disclosure fields**

Confirm no absolute path, raw payload, credential, account, model binary, or arbitrary metadata field can be embedded in the manifest.

- [ ] **Step 3: Merge only after downstream consumers have compatible PRs or a documented rollout order**
