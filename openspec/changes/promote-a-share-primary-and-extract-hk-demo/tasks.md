## 1. Baseline Readiness Reporting

- [x] 1.1 Add a top-level no-write A-share readiness command that emits machine-readable `baseline_reproducible`, `research_default_promotable`, and `broker_trading_enabled` statuses with missing-evidence details.
- [x] 1.2 Make the readiness command inspect `metadata/current_assets/a_share_current.json`, `metadata/dataset_registry.csv`, resolved manifests, daily-clean validation evidence, universe validation evidence, research outputs, target lineage, and qexec dry-run evidence without importing submodule packages.
- [x] 1.3 Add top-level tests for canonical `a_share_current.json` handling, legacy `cn_current.json` warnings, incomplete evidence, window mismatches, and the rule that CN dry-run evidence does not enable broker trading.
- [x] 1.4 Update top-level migration docs and release checklist with the three readiness levels and the current medium-window baseline boundary.

## 2. A-Share Data Platform Completion

- [x] 2.1 Record the selected primary A-share universe policy and the licensed provider/schema decisions for point-in-time fundamentals and historical industry changes.
- [x] 2.2 Add or finish an A-share current-refresh workflow that plans and validates raw refresh, `daily_clean`, by-date universe, contract rebuild, and registry rebuild before updating latest aliases.
- [x] 2.3 Ensure A-share contract inspection reports manifest coverage, symbol counts, missing required assets, and effective date-window mismatches for the promoted research profile.
- [x] 2.4 Add point-in-time A-share fundamentals assets with report period, disclosure date, availability-delay semantics, field mappings, manifests, validation, and current-contract keys.
- [x] 2.5 Add historical A-share industry assets with effective-date membership, manifests, validation, and current-contract keys.
- [x] 2.6 Add focused `market-data-platform` tests for refresh planning, current-contract keys, registry rows, PIT fundamentals validation, historical industry validation, and compatibility with the existing by-date universe.
- [x] 2.7 Run the focused platform tests and produce a fresh A-share contract-inspection report for the active shared-data root.

## 3. A-Share Research Candidate

- [x] 3.1 Wire `configs/presets/default_next.yml` through an A-share candidate preset that uses the published by-date universe with `require_by_date: true` and does not rely on the ten-symbol static sample.
- [x] 3.2 Align the A-share candidate date window with the required current-contract asset coverage and add validation that rejects misleading earlier configured windows.
- [x] 3.3 Add A-share PIT fundamentals and historical industry consumption while keeping daily valuation overlays explicitly separate from financial-statement fundamentals.
- [x] 3.4 Implement or refine side-aware A-share simulation policies for limit-up buys, limit-down sells, suspended holdings, T+1 availability, ST state, listing age, board lots, and board-specific rules.
- [x] 3.5 Add A-share benchmark-ladder, feature-evidence, CPCV, and promotion-gate configs by reusing the existing generic research tools.
- [x] 3.6 Add focused `cross-sectional-trees` tests for by-date universe consumption, PIT semantics, window validation, A-share benchmark market checks, and side-aware exit behavior.
- [x] 3.7 Run the candidate pipeline and preserve `summary.json`, `config.used.yml`, `inputs.lock.json`, and `positions_current*.csv` for the selected A-share baseline.
- [x] 3.8 Generate A-share benchmark, walk-forward, shortlisted CPCV, feature-evidence, and promotion-gate reports for the selected candidate.

## 4. Research To Execution Handoff

- [x] 4.1 Export the selected A-share positions to standard CN `targets.json` and retain `targets.json.lineage.json`.
- [x] 4.2 Add or confirm `quant-execution-engine` focused tests for `.SH`, `.SZ`, `.BJ`, `.XSHG`, and `.XSHE` normalization, explicit CNY FX requirements, board-lot planning, and non-submitting CN dry-run behavior.
- [x] 4.3 Run a non-submitting qexec rebalance dry-run with explicit `FX_CNY_USD` and save a machine-readable evidence record for the workspace readiness report.
- [x] 4.4 Update execution capability docs to keep the distinction between CN file-contract dry-run and real A-share broker submission explicit.

## 5. Default Promotion

- [x] 5.1 Run the top-level readiness command against the selected A-share evidence bundle and resolve every `research_default_promotable` failure before changing aliases.
- [x] 5.2 Switch `cross-sectional-trees/configs/presets/default.yml` to the promoted A-share preset while retaining `configs/presets/hk.yml` as the named HK compatibility entry.
- [x] 5.3 Update `cross-sectional-trees` README, docs, config catalog lifecycle fields, CLI examples, package description, and release notes for the breaking default change.
- [x] 5.4 Add regression tests proving `default` resolves to A-share, `default_next` remains a valid migration-compatible alias, and `hk` remains the explicit HK route.
- [x] 5.5 Run top-level and research-repository focused tests after the alias switch and record the rollback procedure.

## 6. HK Legacy Lane Governance

- [x] 6.1 Create a tracked HK surface inventory across all three submodules with `shared_active`, `frozen_compatibility`, `archived_provenance`, and `retire_after_audit` classifications plus dependency references.
- [x] 6.2 Download and checksum-verify the HK data and HK research freeze releases in a temporary cold path, perform a documented restore drill, and retain machine-readable restore evidence.
- [x] 6.3 Confirm that `market-data-platform` freeze/hydrate and restore-critical HK support remain covered by focused tests after the inventory review.
- [x] 6.4 Confirm that `quant-execution-engine` HK parsing, symbol, FX, and broker tests remain in the multi-market execution suite independently of HK research maintenance status.
- [x] 6.5 Extract archived HK experiments, historical notes, and research-only provenance from the active `cross-sectional-trees` lane after their source tag and archive manifest are recorded.
- [x] 6.6 Audit `alloc-hk` consumers and either retain it as a documented deprecated compatibility command, move it to an optional legacy package, or retire it after migration evidence is complete.
- [x] 6.7 Update lifecycle docs, compatibility docs, and rollback notes with the final retained HK surface and sunset decisions.

## 7. HK Public Demo Export

- [x] 7.1 Choose the public demo repository name, owner, and license, then define a versioned clean-room allowlist for the curated HK demo.
- [x] 7.2 Add a maintainer export tool that stages the allowlisted demo tree without copying source Git history.
- [x] 7.3 Add public-safety scans for credentials, `.env*`, provider caches, Parquet or other licensed data, private outputs, disallowed absolute local paths, and oversized files.
- [x] 7.4 Add synthetic HK fixtures and a minimal offline strategy workflow that generates sample `summary.json` and sample `targets.json`.
- [x] 7.5 Add a demo README, architecture overview, license, disclaimer, paused-maintenance statement, and minimal CI smoke command.
- [x] 7.6 Emit an export manifest with source revision, included files, generated fixtures, scan results, and smoke-test result; verify the staged repository offline.
- [x] 7.7 Publish the reviewed demo through an explicit maintainer action and link it from the workspace as an external portfolio reference without adding a required submodule.

## 8. Final Verification

- [x] 8.1 Run top-level workspace doctor, no-write contract smoke checks, docs-link tests, and readiness-report tests.
- [x] 8.2 Run focused `market-data-platform` A-share contract, TuShare, universe, PIT, industry, and HK restore tests.
- [x] 8.3 Run focused `cross-sectional-trees` config, pipeline, research-evidence, export-targets, docs-contract, and HK compatibility tests.
- [x] 8.4 Run focused `quant-execution-engine` target-contract and rebalance-helper tests for CN and retained HK behavior.
- [x] 8.5 Verify the staged public demo contains no private data or local paths, run its offline CI smoke, and record the final migration limitations.
