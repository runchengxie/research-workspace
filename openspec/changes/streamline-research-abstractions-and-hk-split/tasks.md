## 1. Research Run Bundle

- [x] 1.1 Add `ResearchWorkspace` and `ResearchRun` modules in `cross-sectional-trees` with typed accessors for summary, config, inputs lock, datasets, signals, positions, targets, and lineage sidecars.
- [x] 1.2 Add run validation status objects that separate reproducibility, research artifacts, portfolio artifacts, and execution handoff completeness.
- [x] 1.3 Add legacy-run detection for runs that contain `eval_scored.parquet` but no canonical `signals.parquet`.
- [x] 1.4 Add focused tests for complete runs, missing optional artifacts, missing reproducibility files, and target-export delegation.
- [x] 1.5 Update `cross-sectional-trees` outputs and workflow docs with the run object entrypoint and six-stage method map.

## 2. Dataset Lifecycle

- [x] 2.1 Add `ResearchDataset` lifecycle types for `raw_panel`, `raw_feature_label`, `infer_frame`, `learn_frame`, and `backtest_pricing_frame` without duplicating large frames by default.
- [x] 2.2 Adapt the existing `build_modeling_dataset()` result into lifecycle frames and metadata while preserving current model inputs.
- [x] 2.3 Add `fetch_learn(segment)` and `fetch_infer(segment)` accessors with explicit target-column and audit-view behavior.
- [x] 2.4 Record dataset lifecycle row counts, universe filter effects, dropped-date counts, and asset lineage in `summary.json`.
- [x] 2.5 Add processor provenance records for missing fill, cross-sectional transforms, winsorization, train-target transforms, universe filters, purge, embargo, and sampling decisions.
- [x] 2.6 Add focused leakage-boundary tests for learn/infer target visibility, PIT universe filtering, per-date processor scope, and training-fitted processor metadata.

## 3. Canonical Signal Artifact

- [x] 3.1 Add canonical signal schema constants, writer, reader, and metadata helpers for `signals.parquet`.
- [x] 3.2 Map existing prediction, evaluation, backtest, direction, rank, eligibility, model, and feature-set fields into the canonical signal schema.
- [x] 3.3 Change normal artifact output to write `signals.parquet` when artifacts are enabled and record path, row count, schema version, and score columns in `summary.json`.
- [x] 3.4 Preserve `eval.save_scored_artifact` and `eval_scored.parquet` compatibility during the migration window.
- [x] 3.5 Update evaluation, backtest, construction-grid, positions, and run-bundle readers to accept canonical signals as shared score input where applicable.
- [x] 3.6 Add focused tests for signal schema, disabled artifact mode, legacy scored artifact loading, fixed-signal backtest input, and summary metadata.

## 4. Model Detail

- [x] 4.1 Add `CSTreeModel` facade over the existing model registry with `fit(dataset, segment)`, `predict(dataset, segment)`, `detail()`, and artifact metadata methods.
- [x] 4.2 Keep existing `build_model`, `fit_model`, `feature_importance_frame`, and direct pipeline usage compatible while introducing the facade.
- [x] 4.3 Add model-detail summary or artifact output with model type, params, feature-importance source, top features, constant-prediction flag, zero-feature-importance flag, available IC metrics, and degradation reasons.
- [x] 4.4 Link `model_version` and `feature_set_id` from model detail into canonical signal metadata.
- [x] 4.5 Add focused tests for supported model types, predict output identity columns, detail before fit, constant predictions, unavailable feature importance, and legacy function compatibility.

## 5. Named Strategy Construction

- [x] 5.1 Add `StrategySpec` parsing for `strategy.name`, `strategy.type`, `strategy.score_col`, top-k, buffer, weighting, group cap, long-only, and execution policy settings.
- [x] 5.2 Add compatibility mapping from existing `backtest` construction keys to an equivalent default strategy spec.
- [x] 5.3 Update portfolio construction to consume canonical signals through a strategy spec while preserving current top-k and buffered top-k behavior.
- [x] 5.4 Record strategy identity, score column, source signal artifact, and construction parameters in positions outputs, `summary.json`, construction-grid reports, and target-export lineage.
- [x] 5.5 Add fixed-signal construction-grid mode that compares multiple strategy specs without retraining or rescoring.
- [x] 5.6 Add focused tests for legacy mapping, buffered top-k selection, group caps, fixed-signal grids, and target lineage.

## 6. Promotion Event Sidecar

- [x] 6.1 Add candidate-only config gate for the event sidecar and keep ordinary exploratory runs free of sidecar requirements.
- [x] 6.2 Implement daily event records for signal events, target events, order intents, fill events, cash state, and position state.
- [x] 6.3 Reuse or adapt existing `execution_sim` capacity and tradability logic for participation limits, delayed sells, `is_buy_tradable`, and `is_sell_tradable`.
- [x] 6.4 Add A 股-specific daily constraints for signal/entry separation, T+1 sell restrictions, limit direction constraints, suspension or zero-volume handling, cash drag, and holdings outside target lists.
- [x] 6.5 Emit sidecar artifacts and summary fields for events, orders, fills, end-of-day positions, cash, fill ratios, delayed sells, and constraint counts.
- [x] 6.6 Add focused tests for disabled sidecar, next-entry-date handling, T+1 blocked sells, limit/tradability blocks, partial fills, cash roll-forward, and summary evidence.

## 7. HK Research Lane Split

- [x] 7.1 Add or update a machine-readable HK research surface inventory that classifies owner, category, lifecycle, action, dependencies, and migration status.
- [x] 7.2 Create an independent HK research repo skeleton or documented staging directory with package metadata, README, baseline configs, source layout, synthetic fixtures, and smoke tests.
- [x] 7.3 Add synthetic HK smoke workflow that builds a minimal universe, features, signals, positions, and `targets.json` without licensed provider data.
- [x] 7.4 Stage `alloc_hk*` migration or forwarding wrapper behavior while keeping the A 股 primary path and standard `cstree alloc` unchanged.
- [x] 7.5 Stage selected HK research scripts, configs, and docs into the HK lane only after the smoke workflow passes.
- [x] 7.6 Ensure `market-data-platform` remains owner of HK data production, current contracts, freeze, and hydrate operations.
- [x] 7.7 Ensure `quant-execution-engine` remains owner of standard `targets.json`, FX, broker adapters, risk gates, dry-run, and audit evidence.
- [x] 7.8 Add focused tests or governance checks for inventory classification, no runtime data or credentials in the HK lane, compatibility messages, and blocked deletion without archive gates.

## 8. Documentation And Cross-Repo Verification

- [x] 8.1 Update superproject workflow, contracts, release checklist, doctor references, and HK lifecycle docs with A 股 primary lane and independent 港股 research lane boundaries.
- [x] 8.2 Update `cross-sectional-trees` docs for outputs, config, CLI, pipeline overview, and get-started paths affected by run bundle, signals, dataset lifecycle, strategy specs, and sidecar evidence.
- [x] 8.3 Update `market-data-platform` docs only where consumer-facing HK/A 股 ownership wording changes; do not move data production docs into research docs.
- [x] 8.4 Update `quant-execution-engine` docs only if target lineage fields or examples change; do not add research or backtest responsibilities.
- [x] 8.5 Run focused `cross-sectional-trees` tests for run bundle, dataset lifecycle, signals, model detail, strategy construction, sidecar, export targets, and docs contracts.
- [x] 8.6 Run top-level doctor/docs tests, including `uv run --with pytest python -m pytest tests/test_workspace_doctor.py -q`.
- [x] 8.7 If target lineage or execution examples changed, run focused `quant-execution-engine` target contract tests.
- [x] 8.8 If data-platform docs or current-contract references changed, run focused `market-data-platform` docs/contract tests.
