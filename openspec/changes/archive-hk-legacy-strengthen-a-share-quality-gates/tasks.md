## 1. Shared Memory-Aware Scanning

- [x] 1.1 Add a market-agnostic `market-data-platform` Parquet scanner that uses `pyarrow.parquet.ParquetFile.iter_batches()` with explicit column projection and bounded telemetry.
- [x] 1.2 Extend `runtime_memory.MemoryPolicy` with bounded minimum, target, and maximum batch rows, adaptive soft-pressure reduction, hard-pressure diagnostics, and a fallback when `/proc` telemetry is unavailable.
- [x] 1.3 Replace A 股 `daily_clean` symbol compaction that concatenates every staging part with a bounded streaming Parquet writer and record compaction telemetry in the manifest.
- [x] 1.4 Add focused scanner and memory-policy tests for projected columns, multiple batches, soft-pressure reduction, hard-pressure abort, missing telemetry fallback, and streaming compaction.

## 2. A 股 Daily Clean Quality Gate

- [x] 2.1 Extract incremental A 股 `daily_clean` validation reducers for manifest reconciliation, required columns, symbol and trade-date format, duplicate keys, numeric fields, non-negative volume and amount, positive non-suspended prices, and OHLC bounds.
- [x] 2.2 Add research-profile reducers for valuation columns, limit-status columns, trading-calendar coverage, suspension consistency, limit-flag consistency, listed-days values, board classification, ST provenance, and configurable `pct_chg` warnings.
- [x] 2.3 Emit a versioned JSON report with stable check identifiers, severities, verdict, metrics, bounded samples, lineage, scanner telemetry, profile, and configured thresholds.
- [x] 2.4 Extend `marketdata tushare validate-a-share-daily-clean` with profile, report output, trading-calendar, severity threshold, warning-rate, batch-row, and memory-limit options while preserving a clear non-zero exit for rejected reports.
- [x] 2.5 Update the A 股 current-refresh plan and operations docs so baseline validation writes a retained report before alias updates or canonical `metadata/current_assets/a_share_current.json` rebuilds.
- [x] 2.6 Update readiness documentation to keep `baseline_reproducible`, research-profile validation, complete PIT data, and broker trading enablement as separate claims.
- [x] 2.7 Add focused A 股 tests for structural failures, overlay failures, bounded samples, manifest drift, PIT provenance wording, failed-publication blocking, and validation without whole-file pandas reads.
- [x] 2.8 Run `market-data-platform` focused pytest, Ruff, and Pyright checks for the scanner, A 股 cleaner, current-refresh planner, and affected documentation contracts.

## 3. 中国香港市场 Private Archive Governance

- [x] 3.1 Decide and document the private archive repository layout, paused-maintenance policy, candidate repository name, remote URL placeholder, and access-control owners before any remote publication.
- [x] 3.2 Add `docs/hk-private-archive-manifest.yml` with source revisions, tracked path allowlists, lifecycle classifications, checksums, restore dependencies, consumer-audit states, replacement docs, rollback notes, focused tests, and explicit retained execution surfaces.
- [x] 3.3 Add `scripts/export_hk_legacy_archive.py` to stage allowlisted tracked files from pinned revisions outside the superproject, reject runtime data and secrets, and write `archive-export-manifest.json`.
- [x] 3.4 Add `scripts/hk_archive_gate.py --check --format json --out <report>` to validate archive evidence and report blockers or eligibility without deleting source files.
- [x] 3.5 Update the top-level doctor, script lifecycle manifest, release checklist, archive index, lifecycle inventory, and deprecation docs with the private archive gate and the rule that the archive repository is not an active submodule or A 股 runtime dependency.
- [x] 3.6 Add focused superproject tests for manifest schema, pinned revisions, exporter checksums, forbidden runtime artifacts, blocked pending audits, eligible review state, retained LongPort boundaries, and doctor integration.
- [x] 3.7 Run top-level docs, doctor, exporter, maintainability-governance, secret-scan, and focused pytest checks.

## 4. Archive Evidence And Operator Handoff

- [ ] 4.1 Run repo-local 中国香港市场 consumer scans across the superproject and three submodules, record remaining `hkdata`, `hk_data_platform.*`, `rqdata-hk-*`, `cstree alloc-hk`, restore-tool, and historical-config consumers, and collect downstream owner attestations.
- [x] 4.2 Run a fresh isolated 中国香港市场 restore drill from the remote freeze releases and retain checksum, hydrate, registry, and research-output evidence without modifying active roots.
- [x] 4.3 Stage the private archive candidate in an external temporary directory, run the archive gate, inspect the emitted checksums, and confirm the candidate contains no market data, provider cache, credentials, research outputs, or execution audit logs.
- [ ] 4.4 Manually create or update the private paused-maintenance archive repository, publish the verified staged candidate, record its immutable reference, and keep it outside the workspace submodule graph and default CI.
- [x] 4.5 Update deprecation and archive records with consumer-audit evidence, restore evidence, private archive reference, and zero-usage release-window status without removing compatibility code.

## 5. Follow-Up Removal Reviews

- [ ] 5.1 After the required zero-usage release window, create separate follow-up OpenSpec changes only for surfaces whose archive gate reports `eligible_for_removal_review`.
- [ ] 5.2 In each follow-up change, keep `freeze-hk`, `hydrate-hk`, freeze markers, standard multi-market `targets.json` support, execution risk controls, FX logic, and LongPort broker runtime in their active owning repositories.
- [ ] 5.3 Verify each follow-up removal by boundary in this order: `market-data-platform` focused tests, `cross-sectional-trees` compatibility and target-export tests, `quant-execution-engine` shared contract tests, then top-level doctor and release checklist.
