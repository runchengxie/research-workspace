## Context

The superproject already records 中国香港市场 freeze and restore evidence in `docs/hk-legacy-surface-inventory.md`, `docs/hk-public-split-manifest.yml`, `docs/deprecations.yml`, and `docs/evidence/hk-restore-drill-20260601.json`. Those records deliberately block direct removal: restore-sensitive data-platform implementations and deprecated compatibility commands still have pending consumer audits. The existing public-demo exporter is a clean-room workflow for synthetic examples and must not become the archive of record for private legacy code.

The data platform already has an A 股 `daily_clean` builder in `market_data_platform.providers.tushare_a_share_clean`. It streams raw `trade_date` partitions into staging batches and uses `runtime_memory.MemoryPolicy` to flush below a soft `MemAvailable` threshold and abort below a hard threshold. Two memory risks remain: compacting one symbol currently concatenates all staging parts, and validation currently calls `pd.read_parquet(path)` for every complete symbol file. Existing validation checks only required columns, duplicate keys, and minimum asset size.

The A 股 current-refresh planner already orders `daily_clean_validate` before `publish_current`. This gives the enhanced report a natural publication boundary without moving research or execution responsibilities into the superproject.

## Goals / Non-Goals

**Goals:**

- Reduce active maintenance and cognitive load by staging a private, paused-maintenance 中国香港市场 legacy archive candidate with explicit evidence and deletion gates.
- Keep restore-sensitive compatibility available until consumer audits and release-window requirements permit a separate removal change.
- Add reusable projected Parquet batch scanning with adaptive memory telemetry.
- Upgrade A 股 `daily_clean` validation from a minimal smoke check to an auditable publication gate.
- Preserve the existing ownership chain: data platform produces assets, research consumes them read-only, execution consumes `targets.json`.

**Non-Goals:**

- Do not delete 中国香港市场 code, deprecated entrypoints, or historical configs in the first implementation change.
- Do not move LongPort runtime, shared `targets.json` parsing, FX logic, execution risk controls, or broker evidence out of `quant-execution-engine`.
- Do not turn the public synthetic demo into a source archive or workspace dependency.
- Do not claim complete PIT fundamentals, historical ST intervals, historical industry membership, or broker trading support from `daily_clean` validation.
- Do not run private remote repository creation, GitHub access-control changes, or large archive uploads automatically from default CI.

## Decisions

### 1. Add a private archive manifest and staging exporter

Create `docs/hk-private-archive-manifest.yml` as a JSON-compatible YAML document separate from `docs/hk-public-split-manifest.yml`. The public manifest continues to govern clean-room synthetic export. The private manifest governs code and provenance staging and can include provider-specific business code, but never credentials, runtime data, caches, run outputs, or execution logs.

Add `scripts/export_hk_legacy_archive.py` to stage allowlisted tracked files from pinned superproject and submodule revisions into an operator-selected output directory. The exporter writes an `archive-export-manifest.json` containing source revisions, file checksums, scan results, and the paused-maintenance marker. It does not initialize a remote repository, copy `.git`, delete source files, or add a submodule.

Alternative considered: move directories directly into a new repository in one change. Rejected because current manifests explicitly record pending consumer audits and restore-sensitive entrypoints.

### 2. Add a read-only archive gate before any migration

Add `scripts/hk_archive_gate.py --check --format json --out <report>` to validate the private archive manifest, existing restore evidence, deprecation records, source tags, consumer-audit state, replacement docs, rollback notes, focused-test references, and staged export evidence. Extend top-level doctor and release checklist only with lightweight checks that the governance records exist and the archive repository is not an active submodule or required workflow dependency.

The gate can report `blocked_pending_audit`, `follow_up_required`, or `eligible_for_removal_review`. It never deletes files. Actual source migration or deletion is a separate follow-up OpenSpec change after the required zero-usage release window.

Alternative considered: make doctor recursively scan all submodule HK surfaces on every run. Rejected because doctor is intentionally lightweight; the explicit archive gate is the correct place for deeper audit work.

### 3. Extract a shared projected Parquet scanner

Add a market-agnostic scanner module under `market_data_platform`, for example `parquet_scanning.py`, and keep Linux telemetry in `runtime_memory.py`. Use `pyarrow.parquet.ParquetFile.iter_batches()` with declared column projection. The scanner yields bounded pandas batches only at the check boundary and accumulates bounded telemetry.

Extend `MemoryPolicy` with configured minimum, target, and maximum batch rows plus a method that chooses the next bounded batch size from `MemAvailable`, RSS, and observed bytes per row. Soft pressure reduces work or flushes a pending sink; hard pressure raises a diagnostic error before more work begins. Missing `/proc` telemetry falls back to a configured bounded target.

Update symbol compaction to use `pyarrow.parquet.ParquetWriter` or an equivalent streaming sink rather than concatenating all staging parts for one symbol.

Alternative considered: hard-code a table of batch sizes by total available memory. Rejected because row width changes across assets; bounded adaptation using observed bytes per row is more defensible and still allows conservative defaults.

### 4. Build A 股 checks as incremental reducers

Split A 股 validation from build orchestration into small check reducers that accept projected batches and accumulate counts plus bounded samples. Keep state bounded: because `daily_clean` output is symbol-partitioned and sorted, duplicate detection can track the previous key within a symbol stream rather than retaining every historical key in memory.

The baseline profile hard-fails structural and OHLC corruption. The research profile adds valuation, limit-status, trading-calendar, suspension, listed-days, board, and ST-provenance checks. Heuristic checks such as `pct_chg` consistency are warnings with explicit tolerance. The JSON report separates `checks`, `quality_verdict`, `metrics`, `samples`, `lineage`, and scanner telemetry.

Reuse stable severity concepts where practical, but do not make the new shared scanner import 中国香港市场-specific `hk_depth` modules. If shared quality primitives are extracted from `hk_depth.quality`, preserve existing HK behavior with focused tests.

Alternative considered: add more conditions inside the existing `_validate_daily_clean_streaming()` loop. Rejected because that would keep whole-file reads and make the validation path difficult to reuse for future universe, PIT, industry, and raw-backfill audits.

### 5. Gate A 股 publication without overstating readiness

Extend `marketdata tushare validate-a-share-daily-clean` with options such as `--profile`, `--trade-cal-file`, `--fail-on-severity`, `--max-warning-rate`, `--batch-rows`, memory-limit controls, and `--out`. Update `plan-a-share-current-refresh` so its validation stage writes a report and its publication policy states that alias updates require an accepted baseline report.

The research profile is an additional readiness artifact. A successful baseline report can support `baseline_reproducible`; it cannot promote `complete_pit_research_data`. Static ST markers derived from the latest instruments snapshot must be labeled as non-PIT provenance until an interval-aware source exists.

Alternative considered: require all research overlays before any A 股 current contract can exist. Rejected because the workspace intentionally supports a price-only baseline while stronger readiness tiers remain separate.

## Risks / Trade-offs

- [Private archive becomes a second active product] -> Mark it paused-maintenance and restore-only, keep it outside submodules and default CI, and prohibit active A 股 dependencies.
- [Premature removal breaks historical reproduction] -> Require current restore evidence, source tags, consumer audit, export evidence, rollback notes, focused tests, and a separate follow-up removal change.
- [Adaptive batches still underestimate pandas expansion] -> Use conservative bounded defaults, observed bytes-per-row feedback, hard memory aborts, and telemetry that identifies the active file and stage.
- [Quality checks report false positives around suspension or price limits] -> Separate structural hard failures from heuristic warnings, add bounded samples, and make tolerances explicit in the report.
- [Static ST flags are mistaken for historical PIT truth] -> Record provenance in the research-profile report and keep complete PIT readiness blocked until interval-aware assets exist.
- [Scanner extraction changes existing HK validation behavior] -> Keep the first scanner consumer focused on A 股 and preserve HK modules unless a shared primitive can be extracted with focused regression tests.

## Migration Plan

1. Add the shared scanner, adaptive memory telemetry, bounded symbol compaction, and focused scanner tests in `market-data-platform`.
2. Add baseline and research A 股 `daily_clean` validation profiles, structured JSON output, CLI flags, current-refresh planning changes, documentation, and focused tests.
3. Run the enhanced validator on the current A 股 asset in an operator environment and retain a report before repointing aliases.
4. Add the top-level private archive manifest, staging exporter, archive gate, doctor/checklist integration, and focused superproject tests.
5. Run consumer audits and a fresh restore drill, stage the private archive candidate outside the workspace, verify checksums, and manually create the private paused-maintenance remote repository.
6. Record the remote archive reference and zero-usage release-window evidence. Create a separate follow-up change for each eligible source migration or compatibility removal.

Rollback is intentionally simple: before any follow-up removal, retain current active code. After a removal change, restore the source-tagged implementation and compatibility wrapper from the pinned source revision, then rerun focused owner-repo tests and the restore drill.

## Open Questions

- Choose the final private archive repository name, remote URL, and access-control owners before staging is published.
- Decide whether archive staging is one combined private repository or one repository per source owner after reviewing restore operations; the manifest format supports either.
- Set initial `pct_chg` tolerance, warning-rate defaults, and scanner batch-row bounds from a representative A 股 validation run before making the research profile a release requirement.
