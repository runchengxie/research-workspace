## ADDED Requirements

### Requirement: Research model facade wraps existing registry
`cross-sectional-trees` SHALL provide a thin research model facade over the existing `ModelSpec`, `build_model`, `fit_model`, and `feature_importance_frame` registry behavior without removing the current function-level API.

#### Scenario: Existing model type is used
- **WHEN** a caller builds a research model for `ridge`, `elasticnet`, `xgb_regressor`, or `xgb_ranker`
- **THEN** the facade resolves the same normalized model type and default parameters as the existing registry

#### Scenario: Existing function API is used
- **WHEN** existing pipeline code calls `build_model` and `fit_model`
- **THEN** those calls continue to work during the migration

### Requirement: Model facade supports fit, predict, and detail
The research model facade MUST expose `fit(dataset, segment)`, `predict(dataset, segment)`, and `detail()` semantics aligned with `ResearchDataset` segments.

#### Scenario: Model predicts a segment
- **WHEN** a fitted model predicts an inference segment
- **THEN** the returned frame preserves `signal_date` or `trade_date`, `symbol`, raw prediction values, and segment metadata needed to build canonical signals

#### Scenario: Detail is requested before fit
- **WHEN** detail is requested before a model has been fitted
- **THEN** the facade reports model type and parameters while marking fit-dependent metrics as unavailable

### Requirement: Model detail artifact is auditable
The pipeline SHALL emit a model-detail artifact or summary section containing model type, parameters, feature importance source, top features, constant-prediction flag, zero-feature-importance flag, available train/CV/test IC metrics, and degradation reasons.

#### Scenario: Constant prediction is detected
- **WHEN** scored predictions are constant within the evaluated segment
- **THEN** model detail records `constant_prediction: true` and includes the affected segment

#### Scenario: Feature importance is unavailable
- **WHEN** a model exposes no useful feature importance
- **THEN** model detail records the importance source as unavailable or zero and sets the zero-feature-importance flag consistently with existing summary behavior

### Requirement: Model metadata links to signal artifacts
Model artifact metadata SHALL include enough identity to link predictions in `signals.parquet` back to the model configuration and feature set used to produce them.

#### Scenario: Signals are written
- **WHEN** canonical signals are emitted
- **THEN** each signal row or artifact-level metadata contains `model_version` and `feature_set_id` values traceable to the model detail and run config
