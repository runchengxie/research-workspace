## ADDED Requirements

### Requirement: A 股 production readiness has distinct states
The workspace SHALL report A 股 readiness as distinct data, research, and execution states rather than one ambiguous "formal" status.

#### Scenario: Research baseline is available
- **WHEN** A 股 current contract, registry, daily-clean validation, by-date universe, research run, target lineage, and CN dry-run evidence pass
- **THEN** the workspace reports the research baseline as reproducible while leaving complete PIT data and broker trading as separate states

#### Scenario: Broker evidence is missing
- **WHEN** CN `targets.json` dry-run passes but no A 股 broker adapter, account permission, supervised submission, reconciliation evidence, or operational approval exists
- **THEN** the workspace does not report broker trading as enabled

### Requirement: Complete A 股 research data requires PIT assets
A 股 complete research data SHALL require PIT universe membership, PIT financial-statement fundamentals where statement features are enabled, and historical industry membership where industry features or constraints are enabled.

#### Scenario: Daily valuation overlay is used
- **WHEN** a strategy uses daily valuation fields from `daily_clean` such as PE, PB, turnover, or market value
- **THEN** the evidence labels them as daily valuation overlays and not as financial-statement PIT fundamentals

#### Scenario: Statement features are enabled
- **WHEN** a research config enables financial-statement features
- **THEN** it references PIT fundamentals with report period, disclosure date, availability date, field mapping, and validation evidence

#### Scenario: Industry features are enabled
- **WHEN** a historical backtest uses industry labels for features, neutralization, exposure control, or constraints
- **THEN** it uses historical industry membership or explicitly restricts the label to current-snapshot reporting outside historical backtests

### Requirement: A 股 strategy evidence includes long-window and benchmark review
Production-grade A 股 research evidence SHALL include a window long enough for market-regime review, benchmark ladder evidence, feature evidence, final OOS or documented substitute, CPCV for shortlisted candidates, turnover/cost review, and capacity assumptions.

#### Scenario: Short-window evidence passes promotion gate
- **WHEN** the promotion gate passes on a short data window
- **THEN** the workspace may keep the research default but records that production strategy evidence still requires longer-window review

#### Scenario: Candidate underperforms benchmarks
- **WHEN** benchmark ladder evidence shows underperformance against required benchmark cohorts
- **THEN** the strategy is not described as production-grade even if the default preset remains useful for A 股 pipeline validation

### Requirement: A 股 execution evidence remains execution-owned
Real A 股 order submission SHALL be enabled only by `quant-execution-engine` evidence and operational approval, not by research repository outputs.

#### Scenario: Targets are exported
- **WHEN** `cross-sectional-trees` exports A 股 `targets.json`
- **THEN** the output is treated as a file contract for execution dry-run and not as authorization to submit real orders

#### Scenario: Broker adapter is proposed
- **WHEN** a real A 股 broker adapter is added
- **THEN** it includes account permission checks, market-specific order constraints, supervised smoke evidence, reconciliation, kill-switch behavior, and explicit operator approval

### Requirement: Readiness reports explain missing evidence
A 股 readiness reporting SHALL list missing, failed, stale, or out-of-scope evidence for each readiness state.

#### Scenario: PIT fundamentals are not enabled
- **WHEN** the selected A 股 strategy profile disables statement features
- **THEN** the report says PIT fundamentals are not required for that profile and still records that complete fundamental strategy support remains pending

#### Scenario: Historical industry is not enabled
- **WHEN** the selected A 股 strategy profile disables industry features and constraints
- **THEN** the report says historical industry is not required for that profile and still records that industry-backed research remains pending

### Requirement: Rollback preserves the A 股 migration route
Rollback from A 股 default promotion SHALL restore the prior explicit default alias while preserving a named A 股 route for migration scripts.

#### Scenario: Default alias regresses
- **WHEN** A 股 default evidence regresses after promotion
- **THEN** maintainers can restore `default` to the prior compatibility route while keeping `default_next` or another named A 股 preset available
