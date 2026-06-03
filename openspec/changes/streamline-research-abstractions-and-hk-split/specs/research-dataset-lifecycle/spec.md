## ADDED Requirements

### Requirement: Dataset lifecycle exposes named frames
`cross-sectional-trees` SHALL expose a `ResearchDataset` lifecycle with named frames for `raw_panel`, `raw_feature_label`, `infer_frame`, `learn_frame`, and `backtest_pricing_frame`.

#### Scenario: Pipeline builds a research dataset
- **WHEN** the research pipeline finishes feature and label preparation
- **THEN** the resulting dataset object exposes the named lifecycle frames and row counts for each frame

#### Scenario: Backtest pricing is requested
- **WHEN** a caller requests the backtest pricing frame
- **THEN** the returned frame contains `trade_date`, `symbol`, the configured price column, required execution pricing columns, and tradability columns available in the source data

### Requirement: Learn and infer accessors enforce leakage boundaries
The dataset object MUST provide `fetch_learn(segment)` and `fetch_infer(segment)` accessors that make target availability and prediction-time feature visibility explicit.

#### Scenario: Inference frame is fetched
- **WHEN** a caller fetches an inference frame for a segment
- **THEN** the returned frame excludes training-only target columns unless the caller explicitly requests an audit view

#### Scenario: Learning frame is fetched
- **WHEN** a caller fetches a learning frame for a training or validation segment
- **THEN** the returned frame includes the configured training target and only rows eligible under the segment, purge, embargo, and universe filters

### Requirement: Processor provenance is recorded
The pipeline SHALL record dataset processor provenance in `summary.json`, including processor name, fit scope, applied frames, parameters, input columns, output columns, and leakage-safety classification.

#### Scenario: Cross-sectional transform runs per date
- **WHEN** a cross-sectional standardization or winsorization processor is applied per trade date
- **THEN** the summary records `fit_scope: per_date` and identifies the affected learn and infer frames

#### Scenario: Training-fitted processor is added
- **WHEN** a processor uses parameters fitted on a training segment
- **THEN** the summary records the training segment used for fit and the frames to which those parameters were applied

### Requirement: Summary records lifecycle counts and filters
The run summary MUST record row counts and key filter effects for raw, infer, learn, and signal-base frames.

#### Scenario: Universe-by-date filter removes rows
- **WHEN** a PIT-safe universe-by-date filter is applied
- **THEN** the dataset summary records rows before filtering, rows after filtering, and the universe asset lineage

#### Scenario: Dates are dropped for minimum symbol count
- **WHEN** dates are removed because they do not meet `min_symbols_per_date`
- **THEN** the summary records dropped date counts and the threshold used
