## Why

The workspace has promoted A 股 as the default research lane, but the surrounding governance is still uneven: quality tools differ across submodules, A 股 fundamental ingestion is not yet a production contract, research evidence is still short-window, and the retained 港股 strategy surface remains too large for a paused-maintenance lane.

This change turns the migration into an explicit production-readiness program: keep the superproject as an integration layer, harden submodule checks without forcing one tool everywhere, add a TuShare A 股基本面 raw-to-PIT ingestion path, and shrink 港股 strategy code into bounded compatibility plus a clean public demo.

## What Changes

- Define a workspace quality-governance policy that records which repository owns Ruff, Pyright, mypy, pytest, coverage, secret scanning, dependency audit, and optional advisory checks.
- Keep `quant-execution-engine` on mypy as the hard type gate while adding Pyright as an advisory compatibility check before any future migration decision.
- Add a superproject-only lightweight quality check scope for `scripts/` and `tests/`, without making top-level configuration scan submodule source trees.
- Add security and dependency audit recommendations as staged, non-disruptive gates: secret scanning first, then dependency audit, then optional dependency hygiene and security linters.
- Introduce an A 股 production-readiness plan that distinguishes research baseline, complete PIT data stack, long-window strategy validation, and broker trading enablement.
- Add a TuShare A 股基本面 ingestion capability inspired by the public `tushare-a-share-fundamentals` project: dataset specs, stateful downloading, VIP/non-VIP handling, failure reports, raw storage, normalized assets, and PIT builders.
- Keep daily valuation overlays separate from PIT financial-statement fundamentals, and require disclosure-date / report-period / availability-delay semantics before research configs can claim PIT fundamentals.
- Define a 港股 strategy slimming path: keep shared multi-market code and explicit `hk` compatibility, move bulky experiments and notes out of active navigation, and publish the reviewed clean-room demo only as an external portfolio reference.
- **BREAKING** only if later implementation removes or moves public 港股 experiment configs or CLI entry points; this proposal requires deprecation and rollback evidence before such removals.

## Capabilities

### New Capabilities
- `workspace-quality-governance`: Tooling ownership, hard/advisory gates, and submodule delegation rules for Ruff, Pyright, mypy, pytest, security, dependency, and coverage checks.
- `a-share-production-readiness`: Evidence gates that define what remains before A 股 can be called a complete production research and execution stack.
- `a-share-fundamentals-ingestion`: Requirements for TuShare A 股基本面 raw download, state tracking, validation, normalized assets, and PIT conversion.
- `hk-strategy-archive-demo`: Requirements for shrinking 港股 active strategy surface and maintaining a paused public clean-room demo.

### Modified Capabilities

None. The current OpenSpec project has no base capability specs checked in.

## Impact

- Superproject: `docs/`, release checklist, workspace doctor/check scripts, `scripts/submodule_checks.json`, and any new top-level quality profile.
- `market-data-platform`: TuShare A 股基本面 downloader, dataset specs, state/failure tracking, raw and normalized asset manifests, PIT fundamentals validation, current-contract keys, registry rows, and focused tests.
- `cross-sectional-trees`: A 股 strategy evidence configs, long-window benchmark/CPCV/feature evidence, docs for production-readiness boundaries, and 港股 compatibility/archive navigation.
- `quant-execution-engine`: optional Pyright advisory config, retained mypy hard gate, CN dry-run boundary docs, and future broker-enable evidence requirements.
- Public demo workflow: clean-room export, safety scan, offline smoke, external GitHub reference, and no required submodule dependency.
