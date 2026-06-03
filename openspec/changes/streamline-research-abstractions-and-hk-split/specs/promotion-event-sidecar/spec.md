## ADDED Requirements

### Requirement: Candidate promotion can run event sidecar backtest
`cross-sectional-trees` SHALL provide an optional event-driven sidecar backtest for promoted candidates, separate from the primary vectorized research backtest.

#### Scenario: Candidate sidecar is enabled
- **WHEN** a promotion or readiness workflow enables the event sidecar
- **THEN** the system generates sidecar evidence without replacing the primary vectorized backtest metrics

#### Scenario: Ordinary experiment omits sidecar
- **WHEN** a normal exploratory experiment does not enable promotion evidence
- **THEN** the pipeline does not require event sidecar artifacts

### Requirement: Sidecar uses daily event state machine
The sidecar MUST model daily `SignalEvent`, `TargetEvent`, `OrderIntent`, `FillEvent`, and `PositionState` concepts at daily frequency.

#### Scenario: Signal date precedes entry date
- **WHEN** a signal is produced after the decision cutoff for `signal_date`
- **THEN** generated order intents use the configured next eligible entry date instead of assuming same-day execution

#### Scenario: Position state rolls forward
- **WHEN** an order is partially filled or unfilled
- **THEN** the position state and cash balance roll forward consistently into the next event date

### Requirement: A 股 trading constraints are represented in sidecar evidence
The sidecar SHALL support configured T+1 sell constraints, buy/sell tradability flags, limit-up/limit-down direction constraints, suspension or zero-volume constraints, participation limits, cash usage, delayed sells, and cleanup of holdings outside target lists.

#### Scenario: Sell blocked by T+1 or tradability
- **WHEN** an existing holding cannot be sold due to T+1, suspension, sell tradability, or limit constraints
- **THEN** the sidecar records an unfilled or delayed sell and keeps the position in state

#### Scenario: Buy exceeds participation capacity
- **WHEN** target buy value exceeds configured daily participation capacity
- **THEN** the sidecar records partial fill, unfilled cash, and remaining target intent according to configured policy

### Requirement: Sidecar emits promotion evidence artifacts
The sidecar SHALL emit structured summary and tabular artifacts for events, order intents, fills, end-of-day positions, cash, and constraint violations.

#### Scenario: Sidecar completes
- **WHEN** the sidecar finishes a candidate run
- **THEN** `summary.json` records sidecar status, artifact paths, key fill ratios, delayed-sell counts, cash drag, and blocking constraint counts
