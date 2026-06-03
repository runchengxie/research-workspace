## ADDED Requirements

### Requirement: Completed research runs write canonical signals
`cross-sectional-trees` SHALL write a canonical `signals.parquet` artifact for completed research runs when run artifacts are enabled, making scored signals a first-class output instead of an optional debug artifact.

#### Scenario: Run artifacts are enabled
- **WHEN** a research run completes model scoring and artifact output is enabled
- **THEN** the run directory contains `signals.parquet` and `summary.json` records its path, row count, schema version, and score columns

#### Scenario: Artifact output is disabled
- **WHEN** a run explicitly disables artifact output for a smoke or dry-run mode
- **THEN** the pipeline may skip `signals.parquet` but MUST record that canonical signal persistence was disabled

### Requirement: Signal schema is stable
The canonical signal artifact MUST include stable columns for `signal_date`, `symbol`, `raw_pred`, `signal_eval`, `signal_backtest`, `signal_direction`, `rank`, `model_version`, `feature_set_id`, `eligible_for_backtest`, and `eligible_for_live` when those concepts are available.

#### Scenario: Optional eligibility cannot be computed
- **WHEN** live or backtest eligibility cannot be computed from the configured inputs
- **THEN** the artifact includes the eligibility column with a conservative false or null value and records the reason in signal metadata

#### Scenario: Ranking is computed per date
- **WHEN** signal ranks are generated
- **THEN** rank values are computed within each `signal_date` cross-section using the configured signal score column

### Requirement: Downstream research flows consume canonical signals
Evaluation, construction-grid, backtest, positions, and target-preparation flows SHALL be able to consume `signals.parquet` as their shared score input.

#### Scenario: Construction parameters change
- **WHEN** a user runs construction-grid with a fixed `signals.parquet`
- **THEN** the grid compares portfolio-construction parameters without retraining or rescoring the model

#### Scenario: Backtest reads signals
- **WHEN** backtest evaluation is run from saved artifacts
- **THEN** it reads canonical signal columns and uses the configured strategy score column instead of a pipeline-local prediction column name

### Requirement: Legacy scored artifact remains readable
Existing `eval_scored.parquet` artifacts and `eval.save_scored_artifact` configuration SHALL remain compatible during the migration window.

#### Scenario: Legacy run lacks signals parquet
- **WHEN** a run object loads an older run containing `eval_scored.parquet` but not `signals.parquet`
- **THEN** it can identify the legacy scored artifact and mark canonical signals as unavailable
