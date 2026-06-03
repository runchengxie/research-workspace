## ADDED Requirements

### Requirement: Portfolio construction is configured by named strategy spec
`cross-sectional-trees` SHALL support a named `strategy` configuration object that defines portfolio construction separately from model scoring.

#### Scenario: Strategy config is present
- **WHEN** a config contains `strategy.name`, `strategy.type`, `strategy.score_col`, and construction parameters
- **THEN** portfolio construction uses that strategy spec and records the strategy name in outputs and summary

#### Scenario: Legacy backtest parameters are present
- **WHEN** a config only contains legacy `backtest.top_k`, buffer, weighting, and execution settings
- **THEN** the pipeline derives an equivalent default strategy spec and records that compatibility mapping

### Requirement: Strategy spec supports current top-k behavior
The strategy spec MUST support current long-only top-k and buffered top-k construction behavior, including `top_k`, `buffer_exit`, `buffer_entry`, `weighting`, optional group caps, long-only constraints, and execution policy references.

#### Scenario: Buffered top-k strategy runs
- **WHEN** a strategy of type `topk_buffered_long_only` is applied to canonical signals
- **THEN** selected positions reflect the configured score column, top-k count, buffer rules, and long-only weighting policy

#### Scenario: Group cap is configured
- **WHEN** a group cap column and maximum names are configured
- **THEN** the constructor limits selected names per group and records cap-induced exclusions

### Requirement: Construction outputs carry strategy lineage
Portfolio construction outputs SHALL include strategy identity and source signal lineage in `summary.json`, positions artifacts, construction-grid reports, and target-export lineage where applicable.

#### Scenario: Targets are exported
- **WHEN** positions generated from a named strategy are exported to `targets.json`
- **THEN** the lineage sidecar records the strategy name, strategy type, score column, source `signals.parquet`, and positions file

### Requirement: Construction-grid can vary strategies against fixed signals
Construction-grid SHALL support comparing multiple named strategy specs against one fixed canonical signal artifact.

#### Scenario: Same signal artifact, multiple strategies
- **WHEN** a construction grid references one `signals.parquet` and multiple strategy specs
- **THEN** the grid produces separate results per strategy without re-running model training or prediction
