## Context

The workspace already has the correct ownership split: `market-data-platform` produces versioned data assets and current contracts, `cross-sectional-trees` consumes them read-only for research, and `quant-execution-engine` consumes standard `targets.json` for dry-run, risk, broker adapters, and audit evidence. Existing docs also record that A 股 is the active primary research lane while 中国香港市场 / 港股 research is legacy or frozen-active unless explicitly resumed.

Inside `cross-sectional-trees`, the current research flow is capable but cognitively expensive. Dataset preparation returns many pipeline-local frames such as `df_features`, `df_full`, `df_model_all`, and `backtest_pricing_df`; model behavior is spread across the `ModelSpec` registry and pipeline stages; scored output is controlled by `eval.save_scored_artifact`; construction rules live mostly as backtest parameters; and run consumers need to know file names such as `summary.json`, `config.used.yml`, `positions_current.csv`, `targets.json`, and lineage sidecars.

An existing OpenSpec change, `archive-hk-legacy-strengthen-a-share-quality-gates`, already covers HK private archive governance and A 股 `daily_clean` quality gates. This design deliberately builds on that boundary: this change does not redefine data-platform validation or delete HK code in the first pass. It focuses on research-layer abstractions, canonical signal handoff, named construction, candidate promotion evidence, and an independent HK research lane.

## Goals / Non-Goals

**Goals:**

- Reduce research workflow cognitive load by adding stable, low-ceremony objects for runs, datasets, models, signals, and strategies.
- Make learn/infer boundaries explicit in code, summary metadata, and tests to improve leakage auditability.
- Make `signals.parquet` the common score artifact for evaluation, construction-grid, backtest, positions, and target export preparation.
- Preserve existing public functions and artifacts during migration so old runs and configs remain inspectable.
- Add named strategy lineage so a fixed model signal can be compared across portfolio-construction rules.
- Add candidate-only sidecar execution evidence before promotion without slowing every exploratory run.
- Stage HK research extraction into an independently runnable repo while keeping data and execution contracts shared.

**Non-Goals:**

- Do not merge the three-repo architecture into a single lab object.
- Do not move data production, HK current refresh, freeze / hydrate, registry, or manifest responsibilities out of `market-data-platform`.
- Do not move broker adapters, LongPort, FX, risk gates, dry-run, or audit logs out of `quant-execution-engine`.
- Do not delete HK compatibility commands, configs, research scripts, or tests in the first implementation.
- Do not replace the vectorized research backtest with a full tick or broker-grade event engine.
- Do not claim complete PIT fundamentals, live broker readiness, or production strategy readiness from the new abstractions alone.

## Decisions

### 1. Add thin facades before changing pipeline internals

Introduce small modules in `cross-sectional-trees` rather than rewriting the pipeline in one pass:

- `cstree.research_run` for `ResearchWorkspace` and `ResearchRun`.
- `cstree.research_dataset` for `ResearchDataset` and lifecycle metadata.
- `cstree.research_model` for `CSTreeModel` and model detail.
- `cstree.signals` for canonical signal schema and writers/readers.
- `cstree.strategy` or `cstree.portfolio` for `StrategySpec` and construction adapters.
- `cstree.promotion_sidecar` for candidate event evidence.

Existing function APIs such as `build_model`, `fit_model`, `feature_importance_frame`, `build_modeling_dataset`, and `simulate_capacity_execution` remain available. The first implementation should wrap and adapt these functions, then migrate pipeline call sites only where the new object clarifies ownership.

Alternative considered: rewrite the research pipeline around new objects immediately. Rejected because the current pipeline has many tested edge cases around PIT filters, CPCV, final OOS, execution simulation, and target export. A wrapper-first migration is safer and easier to review.

### 2. Treat `signals.parquet` as the score boundary

The pipeline should emit `signals.parquet` whenever normal run artifacts are enabled. `eval_scored.parquet` remains readable as a legacy artifact and `eval.save_scored_artifact` can become a compatibility alias or explicit additional debug option. The signal writer should normalize existing prediction and signal columns into a schema with date, symbol, raw prediction, evaluation score, backtest score, direction, rank, eligibility flags, and artifact-level metadata.

Evaluation, construction-grid, backtest, and position generation should gradually learn to accept a saved signal artifact. This enables fast portfolio-construction comparison without retraining the model.

Alternative considered: keep scored output optional and document the path better. Rejected because optional score persistence keeps model scoring and portfolio construction coupled by convention rather than by a clear file contract.

### 3. Make dataset lifecycle metadata explicit without duplicating data

`ResearchDataset` should initially hold references to existing frames or lazily created views, not duplicate large DataFrames. The existing `build_modeling_dataset()` result can be translated into named lifecycle frames and metadata:

- `raw_panel`: input panel after symbol/date normalization.
- `raw_feature_label`: feature, label, price, and passthrough columns before model eligibility filters.
- `infer_frame`: prediction-time visible feature frame.
- `learn_frame`: training/evaluation frame with target and training-only filters.
- `backtest_pricing_frame`: pricing and tradability columns used by backtest and sidecar logic.

Processor provenance should be accumulated as small records in summary metadata. Fit scope is important: per-date cross-sectional transforms, training-fitted thresholds, all-sample operations, and static overlays must be distinguishable.

Alternative considered: materialize every lifecycle frame to disk by default. Rejected because the project already treats large artifacts carefully; summary counts and canonical signals provide most audit value, while optional dataset persistence remains available for diagnostics.

### 4. Keep model behavior registry-based, add research semantics on top

`CSTreeModel` should delegate construction and fitting to the existing registry but provide a consistent research surface: `fit(dataset, segment)`, `predict(dataset, segment)`, `detail()`, and artifact metadata. `detail()` should consolidate information that already exists in pieces: model type, params, feature importance source, top features, constant prediction, zero feature importance, train/CV/test IC where available, and degradation reasons.

Alternative considered: replace `ModelSpec` with class-per-model implementations. Rejected because the registry is simple, tested, and sufficient; the missing piece is research semantics, not model factory complexity.

### 5. Introduce `StrategySpec` as a compatibility layer first

Add a named strategy config while deriving equivalent specs from existing `backtest` parameters for old configs. The implementation should support the current long-only top-k and buffered top-k behavior first, then add optional group caps and execution policy references. Construction outputs and target lineage should carry strategy name, type, score column, and source signal artifact.

Construction-grid should support "fixed signals, varying strategies" as an explicit mode.

Alternative considered: move all backtest config under `strategy` immediately. Rejected because existing configs and docs are numerous, including HK legacy configs. A derived compatibility spec lets implementation proceed without a breaking config migration.

### 6. Build event sidecar as promotion evidence, not a universal backtest

The event sidecar should run only for configured candidate or promotion workflows. It can reuse existing `execution_sim` assumptions where they match: daily capacity, participation limits, delayed sells, `is_buy_tradable`, `is_sell_tradable`, and target positions. It should add clearer event terminology and state outputs: signal event, target event, order intent, fill event, cash, and position state.

For A 股, the sidecar must make signal/entry date separation, T+1 sell constraints, limit and suspension constraints, cash use, and target-list cleanup visible. This is daily evidence, not a broker emulator.

Alternative considered: make all research backtests event-driven. Rejected because vectorized backtest is still the right default for low-frequency research iteration; the sidecar is for handoff realism.

### 7. Split HK research by runnable lane, not filename grep

The HK split should be staged:

1. Generate or maintain a machine-readable HK research surface inventory.
2. Create an independent HK research repo skeleton with synthetic fixture smoke tests.
3. Move or wrap `alloc_hk*` first because it is market-specific and noisy in the A 股 primary repo.
4. Move reusable HK research scripts, selected configs, and docs after the skeleton can run.
5. Keep shared data-platform and execution contracts active in their owner repositories.
6. Delete active legacy surfaces only in later OpenSpec changes after archive and zero-usage gates pass.

Alternative considered: move every path containing `hk` into a new repo immediately. Rejected because many HK-named surfaces are restore-critical data-platform code, shared execution support, or historical provenance, and direct moves would break imports and reproduction.

## Risks / Trade-offs

- [Wrapper layer becomes another abstraction to learn] -> Keep object surfaces narrow, document the six-stage map, and avoid duplicating every pipeline helper.
- [Signals schema misses columns needed by current backtests] -> Start from existing `eval_scored_data`, backtest score, direction, and eligibility use cases; add schema metadata and focused tests before switching downstream consumers.
- [Default `signals.parquet` increases artifact size] -> Write it only when normal artifacts are enabled, use Parquet, and keep smoke/dry-run opt-outs.
- [Dataset frame names imply stronger PIT guarantees than data supports] -> Record processor provenance and input lineage, and keep static or non-PIT overlays explicitly labeled.
- [Strategy config migration breaks old configs] -> Derive `StrategySpec` from legacy `backtest` keys first and keep old config docs valid during the migration window.
- [Event sidecar is mistaken for live execution proof] -> Label it candidate research evidence and keep qexec dry-run, broker evidence, and live readiness as separate gates.
- [HK split creates a second half-maintained codebase] -> Require runnable synthetic smoke tests, paused or explicit maintenance status, and no default A 股 dependency on the HK repo.
- [Existing HK archive change overlaps this split] -> Use the archive change for private archive and deletion gates; use this change for research-lane skeleton, compatibility wrappers, and active-code migration planning.

## Migration Plan

1. Add `ResearchWorkspace` / `ResearchRun` readers, run validation, and docs for the six-stage workflow. Verify against synthetic run fixtures and at least one existing run shape.
2. Add canonical signal schema, writer, reader, summary metadata, and legacy `eval_scored.parquet` detection. Switch normal artifact output to write `signals.parquet` when artifacts are enabled.
3. Introduce `ResearchDataset` lifecycle metadata around the existing dataset-building path. Add summary counts and processor provenance without changing model results.
4. Add `CSTreeModel` and model-detail output while keeping existing registry functions stable. Migrate one pipeline training/eval path to produce model detail through the facade.
5. Add `StrategySpec` parsing and legacy `backtest` compatibility mapping. Update construction and target lineage to record strategy identity.
6. Add fixed-signal construction-grid mode and focused tests proving strategy comparison can run without retraining.
7. Add candidate event sidecar evidence behind an explicit config gate and connect it to promotion/readiness workflows only.
8. Generate HK research surface inventory, create the HK repo skeleton, and add synthetic smoke tests. Do not move active code until the skeleton can execute independently.
9. Move or wrap `alloc_hk*` and selected HK research scripts/configs in follow-up implementation steps with focused tests and docs.
10. Update superproject docs, doctor/checklist references, lifecycle inventory, and owner-repo docs. Run boundary-focused tests in order: data platform docs/contract checks if touched, `cross-sectional-trees` focused pytest, `quant-execution-engine` targets tests if lineage is changed, then top-level doctor.

Rollback is mostly additive for the early phases: leave legacy artifacts and config keys readable, disable `signals.parquet` default through config if needed, and keep pipeline call sites on existing functions until each wrapper path is tested. HK source removal is outside this first implementation and should have its own rollback plan tied to archive tags.

## Open Questions

- Final module names: `research_run.py` / `research_dataset.py` / `research_model.py` are clear, but `strategy.py` versus `portfolio.py` should follow local naming conventions during implementation.
- Decide whether `signals.parquet` metadata lives in Parquet key-value metadata, `summary.json`, or a small `signals.meta.json` sidecar in addition to summary fields.
- Decide the default config transition for `eval.save_scored_artifact`: compatibility alias, deprecated no-op, or "write legacy extra artifact" option.
- Choose initial event sidecar thresholds and promotion-gate wording so sidecar evidence does not imply broker readiness.
- Choose HK repo name and remote location before any moved code is published.
