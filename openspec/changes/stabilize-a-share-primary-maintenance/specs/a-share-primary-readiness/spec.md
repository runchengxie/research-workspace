## ADDED Requirements

### Requirement: A 股 readiness is reported as four independent layers
The workspace SHALL report A 股 readiness using `baseline_reproducible`,
`complete_pit_research_data`, `production_strategy_evidence`, and `broker_trading_enabled`.
Passing an earlier layer MUST NOT implicitly pass a later layer.

#### Scenario: Baseline evidence exists without production evidence
- **WHEN** current contract, registry, daily-clean, universe, research output, targets lineage, and CN dry-run evidence pass
- **THEN** `baseline_reproducible` is reported as passed
- **THEN** PIT data, production strategy evidence, and broker trading remain pending unless their own evidence exists

### Requirement: Canonical A 股 current contract is used
The workspace and submodules SHALL use `metadata/current_assets/a_share_current.json` as the
canonical A 股 current contract. Historical `cn_current.json` references MUST be labeled as aliases
or compatibility artifacts.

#### Scenario: A 股 release checklist is reviewed
- **WHEN** maintainers inspect A 股 publication and downstream-consumption documentation
- **THEN** new authoritative references point to `metadata/current_assets/a_share_current.json`
- **THEN** `cn_current.json` is not presented as the canonical entry point

### Requirement: Complete PIT research data requires published production assets
The workspace MUST keep `complete_pit_research_data` pending until production backfill,
validation, and publication evidence exists for long-window A 股 data, PIT statement
fundamentals, and historical industry membership.

#### Scenario: Code exists but production assets are not published
- **WHEN** raw-to-PIT builders are implemented but entitlement-aware backfill or publication is incomplete
- **THEN** readiness reports keep `complete_pit_research_data` pending

### Requirement: Production strategy evidence is regenerated from complete data
The workspace MUST require long-window benchmark ladder, feature evidence, final OOS or documented
substitute, CPCV, turnover and cost, and capacity reports after complete PIT assets are published
before reporting `production_strategy_evidence` as passed.

#### Scenario: Short-window reports are available
- **WHEN** short-window baseline reports pass but complete long-window PIT assets are not yet published
- **THEN** the reports are described as baseline evidence only
- **THEN** `production_strategy_evidence` remains pending

### Requirement: CN dry-run is not treated as real A 股 brokerage
The workspace SHALL describe CN `targets.json` parsing and `local-dry-run` as a file-contract
handoff only. `broker_trading_enabled` MUST require a real adapter, account permissions, supervised
smoke, reconciliation evidence, kill-switch validation, and operational approval.

#### Scenario: CN targets file passes offline dry-run
- **WHEN** the execution engine parses and plans a CN `targets.json` file without submitting orders
- **THEN** the file-contract handoff is accepted
- **THEN** readiness reports do not claim real A 股 broker trading
