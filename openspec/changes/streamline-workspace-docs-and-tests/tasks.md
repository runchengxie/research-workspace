## 1. Baseline And Migration Rules

- [x] 1.1 Record the current Markdown inventory and line-count hotspots for the superproject, `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine`.
- [x] 1.2 Choose final archive paths for top-level HK dated docs, `cross-sectional-trees` HK research notes, `market-data-platform` dated handoffs, and `quant-execution-engine` phase checklists.
- [x] 1.3 Decide which moved docs need one-release forwarding stubs and which can be updated by internal link rewrites only.
- [x] 1.4 Define active-doc style lint scope, archive exemptions, and any explicit allowlist for required technical negation.

## 2. Superproject Documentation And Tests

- [x] 2.1 Create a top-level HK archive entrypoint and move or demote dated HK handoff and release-note documents under that archive.
- [x] 2.2 Update root `README.md`, `AGENTS.md`, and `docs/README.md` so the newcomer path is short and separates active, reference, and archive material.
- [x] 2.3 Update `docs/platform-workflow.md`, `docs/contracts.md`, `docs/bootstrap.md`, `docs/release-checklist.md`, and related links after any archive moves.
- [x] 2.4 Refresh `docs/version-matrix.md` so it reflects the generated current-checkout workflow and no longer presents 2026-05-27 as the current state.
- [x] 2.5 Harden `scripts/print_version_matrix.py` for missing `.git`, missing submodules, uninitialized submodules, and dirty checkout reporting.
- [x] 2.6 Align `tests/test_docs_links.py` with `workspace_doctor.py` so links into uninitialized submodules produce a clear submodule initialization message.
- [x] 2.7 Add focused tests for version-matrix generation and source-snapshot limitation messaging.

## 3. Data Platform Documentation And Tests

- [x] 3.1 Move `market-data-platform/docs/session-handoff-a-share-backfill-20260531.md` into an archive path and update docs indexes and links.
- [x] 3.2 Split `market-data-platform/docs/operations.md` into focused operations pages for credentials, A-share TuShare workflows, HK assets, and backup/cold-storage procedures.
- [x] 3.3 Update `market-data-platform/README.md`, `AGENTS.md`, and `docs/README.md` to make A-share, TuShare, data contract, and catalog responsibilities clear.
- [x] 3.4 Rewrite avoidable contrast wording in active data-platform docs while preserving safety caveats around provider, PIT, and execution boundaries.
- [x] 3.5 Expand `tests/test_quality_governance.py` to scan active docs recursively, skip archive paths by policy, and report file/line context for style findings.
- [x] 3.6 Add parser-derived CLI documentation coverage for public `marketdata` command families.
- [x] 3.7 Run focused data-platform docs and governance tests.

## 4. Strategy Research Documentation And Tests

- [x] 4.1 Update `cross-sectional-trees/docs/README.md` and research indexes so current A-share work, HK legacy research, vendor references, and archive material are visibly separated.
- [x] 4.2 Move or demote HK dated research notes into the chosen archive path while preserving title, status, last-check date, and successor-reading metadata.
- [x] 4.3 Split `cross-sectional-trees/docs/outputs.md` into smaller reference pages for root layout, summary artifacts, positions, targets, platform assets, and dataset-specific details.
- [x] 4.4 Demote `cross-sectional-trees/docs/rqdata/hk-stock-data-reference.md` from the main reading path into a vendor reference or archive area.
- [x] 4.5 Rewrite active research docs that use avoidable contrast phrasing, especially `capabilities.md`, `cookbook.md`, `pipeline-overview.md`, `outputs.md`, and A-share playbooks.
- [x] 4.6 Refactor `cross-sectional-trees/tests/test_docs_contracts.py` so entrypoint-layer, lifecycle, and dev workflow checks validate facts instead of exact prose.
- [x] 4.7 Adjust research-note indexing tests to match the archive layout and still require metadata on historical notes.
- [x] 4.8 Run focused `cross-sectional-trees` documentation contract and path-reference tests.

## 5. Execution Engine Documentation And Tests

- [x] 5.1 Split stable testing guidance from dated Pyright/mypy migration notes in `quant-execution-engine/docs/testing.md`.
- [x] 5.2 Move completed execution checklists or migration notes into an archive path and update `docs/README.md`.
- [x] 5.3 Clarify overlap among `architecture.md`, `execution-foundation.md`, and `execution-checklist.md` so each page has one stable responsibility.
- [x] 5.4 Rewrite avoidable contrast wording in active execution docs while preserving broker safety and evidence maturity caveats.
- [x] 5.5 Add a lightweight test that parser-derived top-level `qexec` commands are documented in `docs/cli.md`.
- [x] 5.6 Add a lightweight test that pytest markers from `pyproject.toml` are documented in `docs/testing.md`.
- [x] 5.7 Add a lightweight test that broker smoke docs cover the registered broker backends and linked smoke files exist.
- [x] 5.8 Run focused execution-engine CLI, docs, and marker consistency tests.

## 6. Final Verification

- [x] 6.1 Run top-level docs, root quality, workspace doctor, version matrix, and docs link tests.
- [x] 6.2 Run changed submodule focused tests in the order data platform, strategy research, then execution engine.
- [x] 6.3 Run `python scripts/workspace_doctor.py` and `python scripts/print_version_matrix.py`, then capture the concrete output for the final summary.
- [x] 6.4 Run `python scripts/run_submodule_checks.py --profile smoke` or document the exact prerequisite that blocks it.
- [x] 6.5 Review `git status --short` in the superproject and each touched submodule, including submodule gitlink changes.
- [x] 6.6 Summarize results in the required order: data platform, strategy research, execution engine, top-level docs/doctor, remaining limitations.
