# Quant Runtime Cutover Design

## Status

Approved for implementation in an isolated worktree. This design covers the first
production-shaped migration slice: the DailyWatch20 and cashflow shadow runtime.

## Problem

The current development and production paths are still rooted in the
`research-workspace` superproject and its `strategy-app` and `strategy-pipeline`
submodules. The new `quant-research` and `quant-platform` repositories contain
migration slices, but they are not yet the authoritative runtime. The cashflow
feature must not be promoted to live eligibility as part of this migration.

## Goal

Make `quant-research` the private strategy owner and `quant-platform` the public
contract/publication owner for the DailyWatch20 and cashflow shadow path, while
keeping `research-workspace` as a recoverable rollback source until the new path
has passed its gates.

## Target topology

```text
quant-research
  strategy-specific code, DailyWatch20, cashflow shadow runner
          |
          | versioned artifact and public package API
          v
quant-platform
  reusable contracts, publication, control-plane helpers
          |
          | path-free versioned artifact only
          v
market-intel
  artifact validation, reporting, and explicit Feishu test-group delivery
```

The `strategy_pipeline` namespace may remain temporarily inside the public
compatibility surface, but new strategy-owned code must not import the old
workspace checkout directly. The migration must distinguish namespace
compatibility from repository authority.

## Scope

The implementation includes:

1. A reproducible migration manifest linking source commits, destination
   commits, package versions, and artifact schema versions.
2. A quant-research entrypoint for the DailyWatch20 and cashflow shadow flow.
3. Quant-platform contract/publication integration for the cashflow selection and
   executable artifacts.
4. Market-intel consumption through versioned artifacts, without importing
   quant-research Python modules.
5. Offline deterministic tests for the migration path and separately gated network
   integration tests for FMP.
6. A shadow comparison and rollback procedure. Production `current` is not
   switched until the new path passes all stated gates.

The implementation does not grant `eligible_for_live`, does not send to a formal
production group, and does not delete the old repositories or releases.

## Data flow and contracts

The private side produces the existing versioned cashflow artifacts:

- `strategy_app.cashflow.selection.v1`
- `strategy_app.cashflow.executable.v1`

The public side validates and publishes:

- `strategy_pipeline.cashflow.publication.v1`

Every artifact must preserve strategy identity, source date, signal date,
policy identity, content hash, research-only status, and live-ineligibility
flags. Market-intel consumes the artifact and delivery receipt only.

## Cutover stages

### Stage 1: Build and contract parity

Complete the migrated DailyWatch20/cashflow code and make its dependencies resolve
from quant-platform and quant-research. Add a machine-readable manifest and
offline checks proving that the new entrypoints do not depend on the old workspace
source paths.

### Stage 2: Shadow execution

Run the new path with production-shaped inputs in a separate output root. Compare
old and new outputs by policy, dates, symbols, weights, hashes, publication
receipts, and delivery payloads. No production pointer or formal delivery target
changes during this stage.

### Stage 3: Controlled runtime cutover

After the parity and shadow gates pass, point the relevant production runner at
immutable quant-research/quant-platform commits or their packaged release. Keep
the previous research-workspace release and rollback manifest intact.

### Stage 4: Retirement cleanup

Only after a recorded observation window may the old runtime dependency and
compatibility bridges be removed. Historical source references and rollback
metadata remain archived.

## Safety and rollback

- All migration work occurs in isolated worktrees.
- Existing production releases are immutable and retained.
- The production pointer changes atomically, only after validation.
- Any failed readiness, artifact, parity, or delivery check leaves the old
  pointer unchanged.
- Cashflow remains `research_only=true` and `eligible_for_live=false` throughout
  this design.

## Acceptance criteria

The migration slice is ready for runtime cutover only when:

1. Quant-research can run the target shadow flow from its own checkout.
2. Quant-platform validates and publishes the resulting artifacts without reading
   strategy source files from research-workspace.
3. Market-intel consumes only the versioned artifact and does not import
   quant-research.
4. The relevant unit, contract, import-boundary, and offline integration tests
   pass.
5. FMP and other external-network tests are isolated behind an explicit opt-in.
6. A shadow comparison report and rollback manifest are recorded.
7. No artifact claims live eligibility unless an independent strategy-readiness
   gate has passed.

