## ADDED Requirements

### Requirement: Workspace reports distinct A-share readiness levels
The workspace SHALL report `baseline_reproducible`, `research_default_promotable`, and `broker_trading_enabled` as distinct A-share readiness levels and SHALL list missing or failed evidence for each level.

#### Scenario: Baseline passes while broker trading remains disabled
- **WHEN** A-share platform assets, research outputs, target lineage, and dry-run evidence pass but no supported A-share broker path has been approved
- **THEN** the workspace reports `baseline_reproducible` as passing and `broker_trading_enabled` as not passing

#### Scenario: Readiness report exposes missing evidence
- **WHEN** one or more required artifacts are absent or invalid
- **THEN** the workspace report names each missing or failed artifact and does not silently promote the affected readiness level

### Requirement: Baseline uses the canonical A-share platform contract
The reproducible baseline SHALL consume `metadata/current_assets/a_share_current.json` as the canonical A-share current contract, SHALL validate `metadata/dataset_registry.csv`, and SHALL treat `metadata/current_assets/cn_current.json` only as a historical compatibility alias if it exists.

#### Scenario: Canonical contract and registry are available
- **WHEN** the readiness gate inspects a valid `a_share_current.json` and a registry derived from the active A-share contract
- **THEN** the contract evidence passes and the report records the resolved asset manifests

#### Scenario: Legacy alias is present
- **WHEN** `cn_current.json` exists beside `a_share_current.json`
- **THEN** the readiness report identifies it as a legacy alias and does not use it as the authoritative entry

### Requirement: Baseline validates daily-clean and by-date universe assets
The reproducible baseline SHALL require a validated A-share `daily_clean` asset and a validated by-date universe asset with manifest provenance, coverage dates, and rebalance-date membership.

#### Scenario: Published medium-window baseline is inspected
- **WHEN** the active contract points to the current TuShare `daily_clean` and by-date universe assets
- **THEN** the gate records their effective coverage windows, symbol counts, and validation results

#### Scenario: Static sample symbols remain configured
- **WHEN** the candidate config still relies only on a hand-written static symbol list
- **THEN** the gate may report an exploratory baseline but SHALL NOT report `research_default_promotable`

### Requirement: Promoted research inputs are point-in-time
The promoted A-share research default SHALL use point-in-time universe membership. If financial-statement features are enabled, it SHALL use point-in-time fundamentals with report period, disclosure date, availability delay, and field mapping. If industry features or constraints are enabled, it SHALL use historical industry membership or explicitly restrict the feature to current-snapshot reporting outside historical backtests.

#### Scenario: Candidate uses historical membership
- **WHEN** a candidate run uses a by-date universe whose manifest documents historical membership construction without current-constituent backfill
- **THEN** the universe point-in-time requirement passes

#### Scenario: Daily valuation overlay is used
- **WHEN** the candidate uses `daily_basic` valuation fields such as `pe_ttm`, `pb`, or `total_mv`
- **THEN** the evidence identifies them as daily valuation overlays and does not claim they satisfy the financial-statement fundamentals requirement

#### Scenario: Current industry labels are backfilled
- **WHEN** a candidate historical backtest fills past dates with only the latest industry labels
- **THEN** the promoted-research gate fails

### Requirement: Promoted preset uses an honest effective date window
The promoted A-share preset SHALL use a research window covered by the published required assets and SHALL record the effective window in evidence.

#### Scenario: Config predates published assets
- **WHEN** a preset requests a start date earlier than a required current-contract asset can provide
- **THEN** the promotion gate fails with a window mismatch or the preset is corrected before promotion

### Requirement: A-share research evidence reuses generic review tools
The promoted A-share default SHALL include A-share benchmark-ladder evidence, walk-forward evidence, shortlist CPCV evidence, feature evidence, and a `cstree promotion-gate` report for the selected candidate.

#### Scenario: HK benchmark semantics are copied unchanged
- **WHEN** an A-share candidate references an HK benchmark file, HK symbol, or HK-only cohort semantics
- **THEN** the promoted-research gate fails and identifies the market mismatch

#### Scenario: Selected candidate has complete review evidence
- **WHEN** A-share report configs produce benchmark, walk-forward, CPCV, feature, and promotion reports for the selected candidate
- **THEN** the gate records those reports in the promotion bundle

### Requirement: A-share trading assumptions are side-aware
The A-share research lane SHALL model or explicitly document side-aware tradability behavior for T+1 settlement, ST state, suspension, listing age, board lot, board-specific rules, limit-up buys, and limit-down sells.

#### Scenario: Position reaches limit-up
- **WHEN** the strategy attempts to buy an A-share position that is limit-up under the selected simulation policy
- **THEN** the simulated buy is blocked or delayed and the evidence records the applied policy

#### Scenario: Held position is suspended or limit-down
- **WHEN** the strategy attempts to sell a suspended or limit-down A-share holding
- **THEN** the simulation does not assume an immediate successful sale and records the blocked or delayed exit

### Requirement: Baseline exports and dry-runs standard targets
The reproducible baseline SHALL export a standard A-share `targets.json` plus lineage metadata and SHALL verify that `quant-execution-engine` can parse and dry-run the file with an explicit CNY-to-USD FX configuration.

#### Scenario: Dry-run has explicit FX
- **WHEN** an exported CN target file is passed to `qexec rebalance` with `FX_CNY_USD` or equivalent configuration and a non-submitting broker path
- **THEN** the execution engine builds a dry-run plan and preserves CN symbol normalization evidence

#### Scenario: Dry-run lacks explicit FX
- **WHEN** a CN target file is passed to the execution engine without CNY-to-USD FX configuration
- **THEN** the execution engine blocks plan generation with a clear error

### Requirement: Default alias switches only after research promotion
The workspace SHALL keep `default_next` as the A-share candidate until `research_default_promotable` passes. After promotion, `default` SHALL resolve to the A-share primary preset and the named `hk` preset SHALL remain available as the HK compatibility entry.

#### Scenario: Promotion evidence is incomplete
- **WHEN** the A-share candidate is reproducible but the promoted-research evidence is incomplete
- **THEN** `default` remains unchanged and `default_next` remains the migration entry

#### Scenario: Promotion is approved
- **WHEN** the promoted-research gate passes and the alias-switch release checklist is complete
- **THEN** `default` resolves to the promoted A-share preset and documentation records the breaking compatibility change

### Requirement: Broker trading enablement remains execution-owned
The workspace SHALL NOT report A-share broker trading as enabled unless `quant-execution-engine` has an explicitly supported A-share broker adapter, verified account permissions, supervised submission and reconciliation evidence, and operational approval.

#### Scenario: File-contract dry-run passes
- **WHEN** CN `targets.json` parsing and offline planning pass
- **THEN** the workspace reports file-contract dry-run capability and does not claim real A-share order submission
