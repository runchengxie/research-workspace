## 1. Data Platform Maintainability Ratchet

- [x] 1.1 Split `build_a_share_current_refresh_plan` into path-resolution, stage-builder, and payload-builder helpers while preserving schema and stage ordering.
- [x] 1.2 Introduce a bounded options/context object for TuShare fundamentals raw downloads and split query-unit retry, persisted-state update, and manifest assembly into focused helpers.
- [x] 1.3 Replace the broad A 股 industry-changes column argument list with a column-mapping options object and update CLI/tests that call it.
- [x] 1.4 Extract reusable fixture/helper setup from oversized backup snapshot tests without removing current-contract, resolved-asset, manifest, or overlap-pruning assertions.
- [x] 1.5 Run focused A 股 refresh, fundamentals, industry, backup, contract, and registry tests.
- [x] 1.6 Run `uv run --extra dev python scripts/dev/maintainability_metrics.py --check-baseline` and confirm the existing baseline passes without `--write-baseline`.

## 2. Execution Engine Pyright Cleanup

- [x] 2.1 Add explicit float normalization at IBKR dynamic-object boundaries covered by current Pyright errors.
- [x] 2.2 Add explicit iterable normalization for IBKR runtime payloads before list construction or iteration.
- [x] 2.3 Add explicit enum-value and datetime normalization helpers for LongPort support boundaries.
- [x] 2.4 Triage delayed broker exports and PyYAML source-visibility warnings; fix actionable warnings and document any intentionally retained warnings without adding broad global ignores.
- [x] 2.5 Run execution-engine Ruff, mypy, Pyright, default pytest, and focused broker / CN targets-contract tests; require Pyright to report zero errors before gate migration.

## 3. Delegated Type-Gate Migration

- [x] 3.1 Change the superproject `quant-execution-engine` delegated `type` profile from mypy to Pyright after task 2.5 passes.
- [x] 3.2 Add a separately invokable `mypy_advisory` delegated profile for the defined bake period.
- [x] 3.3 Update execution-engine testing docs and top-level quality-governance docs with the new hard/advisory ownership, warning policy, bake-period end condition, and rollback command change.
- [x] 3.4 Update superproject delegated-profile tests to prove `type` invokes Pyright and `mypy_advisory` remains available.

## 4. A 股 Primary Readiness Review

- [x] 4.1 Re-run or review A 股 readiness evidence and keep `complete_pit_research_data`, `production_strategy_evidence`, and `broker_trading_enabled` pending unless new production evidence exists.
- [x] 4.2 Verify top-level, data-platform, research, and execution docs consistently use `metadata/current_assets/a_share_current.json` as the canonical A 股 current contract and label `cn_current.json` only as historical compatibility.
- [x] 4.3 Keep the operator backlog explicit for entitlement-aware PIT backfill/publication, historical industry membership, at least ten years of long-window data, regenerated strategy evidence, and real broker enablement.
- [x] 4.4 Verify CN `targets.json` and `local-dry-run` docs remain limited to file-contract handoff and do not imply real A 股 broker execution.

## 5. 港股 Legacy Sunset Review

- [x] 5.1 Check the configured 港股 cold-storage archives on the current machine and record whether local hydrate is actually possible before removing restore-sensitive code.
- [x] 5.2 Audit `retire_after_audit` 港股 wrappers, experiment navigation, and research-only provenance for consumers, tests, source tags, archive manifests, and rollback evidence.
- [x] 5.3 Remove or move only surfaces that pass the audit; retain freeze/hydrate, restore-critical data-platform code, explicit `hk` preset compatibility, shared multi-market execution behavior, and minimal focused smoke tests.
- [x] 5.4 Regenerate the allowlisted 港股 public demo staging tree, run scan-only and offline smoke checks, and record the reviewed export manifest.
- [x] 5.5 Keep public demo publication as an explicit maintainer action and verify required workspace checks do not depend on an external demo clone.

## 6. Final Verification

- [x] 6.1 Run `openspec validate stabilize-a-share-primary-maintenance --strict`.
- [x] 6.2 Run data-platform Ruff, Pyright, focused tests, and the maintainability baseline check.
- [x] 6.3 Run execution-engine Ruff, Pyright hard gate, mypy advisory, default pytest, and focused broker / CN targets-contract tests.
- [x] 6.4 If research-repository surfaces changed, run docs-contract, path-reference, config, target-export, and minimal 港股 compatibility tests.
- [ ] 6.5 Run top-level delegated-profile tests, quality checks, contract smoke, and workspace doctor.
- [x] 6.6 Record final remaining limitations for A 股 PIT publication, long-window strategy evidence, real broker enablement, intentionally retained 港股 surfaces, and any unavailable external cold-storage archive.
