## 1. Workspace Quality Governance

- [ ] 1.1 Add a superproject quality matrix documenting each repository's hard and advisory gates for Ruff, Pyright, mypy, pytest, coverage, secret scanning, dependency audit, and security linting.
- [ ] 1.2 Add or update a superproject-only Ruff configuration that checks only top-level `scripts/` and `tests/` and explicitly excludes submodule source trees.
- [ ] 1.3 Add a top-level quality command or delegated profile that runs the superproject Ruff check without changing submodule tool ownership.
- [ ] 1.4 Add a secret-scanning command and documented scope for the superproject and public demo staging tree.
- [ ] 1.5 Add dependency-audit and dependency-hygiene recommendations as advisory checks with allowlist/baseline guidance for optional provider and broker extras.
- [ ] 1.6 Update release checklist and workspace maintenance docs to distinguish hard, advisory, and manual checks.
- [ ] 1.7 Add focused top-level tests proving delegated submodule profiles do not scan submodule source through root quality config.

## 2. `quant-execution-engine` Type-Check Evaluation

- [ ] 2.1 Add Pyright as a dev dependency for `quant-execution-engine` without removing mypy.
- [ ] 2.2 Add `[tool.pyright]` in `quant-execution-engine/pyproject.toml` with Python 3.10, basic checking, source include scope, generated-output excludes, and optional SDK stub noise suppressed.
- [ ] 2.3 Add a non-blocking `pyright_advisory` profile to the superproject submodule checks while keeping `type` mapped to mypy.
- [ ] 2.4 Update `quant-execution-engine` testing docs to explain mypy hard gate, Pyright advisory, migration criteria, and how to triage optional broker SDK reports.
- [ ] 2.5 Run mypy, Pyright advisory, Ruff, and default pytest for `quant-execution-engine`; record the Pyright findings and whether any are actionable.
- [ ] 2.6 Add or update tests for the submodule check manifest so advisory profiles are listed and hard type gates remain unchanged.

## 3. TuShare A 股基本面 Raw Download

- [ ] 3.1 Add platform-native dataset specs for `income`, `balancesheet`, `cashflow`, `forecast`, `express`, `dividend`, `fina_indicator`, `fina_audit`, `fina_mainbz`, and `disclosure_date`.
- [ ] 3.2 Define entitlement policy for each dataset, including VIP batch API requirements, safe non-VIP fallbacks, and unsupported fallback behavior.
- [ ] 3.3 Implement a restartable raw downloader with query-unit planning, persisted state, retry policy, pagination guards, duplicate-page detection, and field validation.
- [ ] 3.4 Emit machine-readable failure reports for failed periods, dates, symbols, skipped datasets, entitlement failures, and stale refresh windows.
- [ ] 3.5 Write raw parquet assets with manifests containing dataset, endpoint, query parameters, retrieved timestamp, schema hash, row counts, entitlement mode, and source run id.
- [ ] 3.6 Add CLI entry points for planning, downloading, checking state, listing failures, and compacting raw TuShare A 股基本面 assets.
- [ ] 3.7 Add focused tests with mocked TuShare responses for pagination, duplicate pages, missing columns, entitlement skip/fail behavior, restart state, and failure reports.

## 4. A 股基本面 Normalization And PIT Assets

- [ ] 4.1 Implement normalized A 股基本面 asset builders that canonicalize symbol/date fields, validate dataset-specific keys, and preserve raw provenance.
- [ ] 4.2 Define duplicate and report-type policy for statement datasets, including whether raw keeps all report types and normalized/PIT selects a standard report type.
- [ ] 4.3 Implement PIT fundamentals builders that derive availability dates from disclosure or announcement dates plus configured delay.
- [ ] 4.4 Ensure PIT builders reject or conservatively quarantine rows without usable disclosure semantics instead of leaking future data.
- [ ] 4.5 Add validation reports for required PIT columns, symbol coverage, date coverage, duplicate keys, availability-delay semantics, and value-field mapping.
- [ ] 4.6 Add current-contract and registry publication only after normalized and PIT validation pass.
- [ ] 4.7 Add docs explaining why `daily_basic` valuation overlays do not satisfy financial-statement PIT fundamentals.
- [ ] 4.8 Run focused data-platform tests for specs, raw download, normalized assets, PIT builders, validation, current contract, and registry rows.

## 5. A 股 Strategy Production Evidence

- [ ] 5.1 Update readiness docs and reports to separate reproducible baseline, complete PIT research data, production strategy evidence, and broker-enabled trading.
- [ ] 5.2 Add a long-window A 股 data expansion plan with coverage targets, provider entitlement requirements, refresh cadence, and rollback points.
- [ ] 5.3 Add or update `cross-sectional-trees` configs for PIT fundamentals and historical industry features behind explicit feature flags.
- [ ] 5.4 Add benchmark ladder requirements for full A equal weight and index-family cohorts such as CSI 300/500/1000 where available.
- [ ] 5.5 Generate or script long-window feature evidence, benchmark, final OOS or documented substitute, CPCV, turnover/cost, and capacity reports for shortlisted A 股 candidates.
- [ ] 5.6 Update promotion-gate docs so short-window success cannot be described as production-grade strategy evidence.
- [ ] 5.7 Update execution docs to keep CN file-contract dry-run separate from real A 股 broker enablement.
- [ ] 5.8 Run focused research and execution tests for A 股 configs, PIT joins, target export, CN dry-run boundaries, and readiness-report parsing.

## 6. 港股 Active-Lane Slimming And Public Demo

- [ ] 6.1 Generate or update a tracked 港股 surface inventory with lifecycle class, owner repository, active consumers, tests, and rollback evidence for each retained surface.
- [ ] 6.2 Move bulky 港股 experiment configs, historical notes, and research-only helper docs out of active A 股 navigation while preserving archived provenance indexes.
- [ ] 6.3 Audit `alloc-hk` consumers and add explicit deprecation or frozen-compatibility notices to CLI help, docs, and tests.
- [ ] 6.4 Reduce default CI to A 股, shared pipeline, target-export, and minimal 港股 compatibility smoke; document any manual legacy HK test profile.
- [ ] 6.5 Refresh the clean-room 港股 public demo export, scan it, run offline smoke, and record the export manifest.
- [ ] 6.6 Link the public demo as an external paused-maintenance portfolio reference without adding a required submodule.
- [ ] 6.7 Add docs and tests proving workspace checks do not require the external demo repository.

## 7. Final Verification

- [ ] 7.1 Run `openspec validate harden-a-share-production-governance --strict`.
- [ ] 7.2 Run top-level workspace doctor, smoke contracts, top-level tests, and the new top-level quality checks.
- [ ] 7.3 Run `market-data-platform` Ruff, Pyright, focused TuShare A 股基本面 tests, contract tests, and registry tests.
- [ ] 7.4 Run `cross-sectional-trees` fast tests, docs-contract tests, A 股 config tests, promotion evidence tests, and minimal 港股 compatibility smoke.
- [ ] 7.5 Run `quant-execution-engine` Ruff, mypy, Pyright advisory, default pytest, CN target-contract tests, and retained HK execution tests.
- [ ] 7.6 Record final limitations: remaining A 股 data gaps, remaining broker gaps, advisory check status, and any 港股 surfaces intentionally retained.
