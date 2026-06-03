## Why

`cross-sectional-trees` already has strong data governance, PIT controls, research evidence, backtest outputs, and execution handoff contracts, but the mental model is spread across many configs, pipeline variables, optional artifacts, and legacy 中国香港市场 surfaces. This change reduces active cognitive load by introducing a small set of stable research objects and artifacts while moving 港股-specific research and allocation code toward an independent, reproducible lane.

## What Changes

- Add a lightweight `ResearchWorkspace` / `ResearchRun` API for discovering run outputs such as `summary.json`, `config.used.yml`, `inputs.lock.json`, datasets, canonical signals, positions, and `targets.json` lineage.
- Make the dataset lifecycle explicit in code and run summaries: `raw_panel` / `raw_feature_label` / `infer_frame` / `learn_frame` / `backtest_pricing_frame`, including processor provenance and fit-scope metadata.
- Promote scored signals from optional debug output to a canonical run artifact, `signals.parquet`, with stable columns for evaluation, construction, backtest, live eligibility, and lineage.
- Add a thin `CSTreeModel` / research-model facade around the existing `ModelSpec` registry so fit, predict, detail, artifact metadata, and model diagnostics have a single semantic entrypoint.
- Introduce named portfolio-construction strategy specs that separate model score production from holdings construction, construction-grid comparison, and target export lineage.
- Add an event-driven sidecar backtest evidence path for promoted candidates only, reusing existing daily execution simulation semantics where possible and recording order, fill, cash, delayed-sell, and position-state evidence.
- Define a staged HK research lane split: keep shared data contracts and execution contracts active, create an independently runnable 港股 research repo skeleton, migrate `alloc_hk*`, HK research scripts, configs, and docs only behind inventory, smoke tests, and archive gates.
- Update top-level and owner-repo documentation with a short six-stage method map: Data Contract -> Research Dataset -> Model -> Signal -> Portfolio -> Execution Handoff.
- No breaking removal occurs in the first implementation. Deprecated HK compatibility commands may gain forwarding or warning wrappers before any later removal review.

## Capabilities

### New Capabilities

- `research-run-bundle`: Stable workspace/run object model for locating, validating, summarizing, and exporting run artifacts.
- `research-dataset-lifecycle`: Explicit research dataset frames and processor provenance for learn/infer separation and leakage auditability.
- `canonical-signal-artifact`: Canonical `signals.parquet` contract consumed by evaluation, construction-grid, backtest, positions, and target export flows.
- `research-model-detail`: Thin research model facade and model-detail artifact over the existing model registry.
- `named-strategy-construction`: Named strategy spec and portfolio-construction contract that decouples scores from holdings.
- `promotion-event-sidecar`: Candidate-only event-driven sidecar backtest evidence for realistic handoff checks before export or promotion.
- `hk-research-lane-split`: Staged 港股 research repo split contract, including inventory, smoke-test, migration, compatibility, and documentation gates.

### Modified Capabilities

无。当前工作区尚未建立 OpenSpec capability baseline.

## Impact

- `cross-sectional-trees`: Adds research run/dataset/model/signal/strategy abstractions, changes default saved signal behavior, updates run summary fields, output references, CLI docs, focused tests, and compatibility wrappers around 港股-specific commands.
- `market-data-platform`: Remains the producer of A 股 and 中国香港市场 current contracts, manifests, registry entries, and restore-critical HK data assets; this change may add consumer-facing documentation references but does not move data production into research code.
- `quant-execution-engine`: Remains the shared execution engine for standard `targets.json`, FX, risk, dry-run, broker adapters, evidence bundles, and audit logs; no strategy research or backtest logic is added there.
- `research-workspace`: Updates cross-repo docs, doctor/checklist references, lifecycle inventory, and HK split records so A 股 primary research and independent 港股 research lane boundaries are visible at the superproject level.
- Compatibility: Existing run outputs, `positions_current*.csv`, `targets.json`, `targets.json.lineage.json`, and deprecated HK explicit reproduction paths remain readable during the first implementation phase.
