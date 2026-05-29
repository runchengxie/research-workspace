## ADDED Requirements

### Requirement: Platform Owns Market Data Operations
The system SHALL route market data production, maintenance, validation, current-contract, registry, and asset-release workflows to `market-data-platform` as the authoritative implementation.

#### Scenario: HK asset maintenance command is needed
- **WHEN** a user needs to download, mirror, clean, inspect, repair, package, refresh, or release HK market data assets
- **THEN** the documented entry point is a `marketdata ...`, `rqdata-hk-assets`, or `rqdata-hk-depth` platform command rather than a `cross-sectional-trees` command

#### Scenario: Current contract or registry is refreshed
- **WHEN** a workflow updates `hk_current.json`, `cn_current.json`, `dataset_registry.csv`, or manifest-backed catalog metadata for shared market data assets
- **THEN** the workflow runs in `market-data-platform` and writes under the configured platform artifacts root

#### Scenario: New data quality check is introduced
- **WHEN** a new shared data health, coverage, reconciliation, audit, or quality gate is added
- **THEN** its implementation and user-facing runbook live in `market-data-platform`

### Requirement: Research Repository Remains A Consumer
The system SHALL keep `cross-sectional-trees` responsible for strategy research consumption only: resolving platform asset paths, reading configured data inputs, building features and labels, running models and backtests, exporting positions, and preserving run provenance.

#### Scenario: Default research run uses platform assets
- **WHEN** `cross-sectional-trees` runs with `data.source_mode=platform_assets`
- **THEN** it reads local assets prepared by `market-data-platform` and does not initialize provider clients for data asset maintenance

#### Scenario: Provider online read is explicitly requested
- **WHEN** a research configuration opts into `data.source_mode=provider_online_legacy` or a research-only provider overlay
- **THEN** `cross-sectional-trees` may read provider data for that research run without creating shared asset snapshots, current contracts, or release artifacts

#### Scenario: Research output is packaged
- **WHEN** `cross-sectional-trees` packages or releases historical run outputs
- **THEN** the package includes research outputs and provenance references only, while data asset backup and release remain platform responsibilities

### Requirement: Compatibility Wrappers Are Explicit And Temporary
The system SHALL allow `cross-sectional-trees` compatibility wrappers for existing callers only when the wrapper delegates to `market-data-platform`, emits or documents a migration notice, and has clear removal criteria.

#### Scenario: Existing caller invokes a compatibility command
- **WHEN** a user invokes a retained `cross-sectional-trees` wrapper such as a HK universe builder, standardized data helper, current asset helper, or intraday download module
- **THEN** the wrapper delegates to the matching `market_data_platform` module or command without carrying independent data operations logic

#### Scenario: Wrapper cannot load the platform package
- **WHEN** a compatibility wrapper needs `market-data-platform` but the package is unavailable
- **THEN** the wrapper fails with an actionable message telling the user to install the platform package or run from the workspace checkout

#### Scenario: Compatibility status is audited
- **WHEN** maintainers review retained wrappers
- **THEN** platform compatibility documentation records the replacement command, risk, status, and deletion condition

### Requirement: Documentation Points To The Authoritative Owner
The system SHALL make `market-data-platform` docs the authoritative runbook for shared data operations and keep `cross-sectional-trees` docs focused on consumption and research interpretation.

#### Scenario: User reads a research repository data asset page
- **WHEN** a `cross-sectional-trees` page mentions HK data download, health checks, current contracts, registry, release, or platform-owned universe assets
- **THEN** it states that the operation is owned by `market-data-platform` and links or names the platform command or document to use

#### Scenario: User reads platform data operations docs
- **WHEN** a `market-data-platform` page documents HK assets, data warehouse, operations, migration, or integrations
- **THEN** it includes the authoritative command family and clarifies that `cross-sectional-trees` consumes the published outputs

#### Scenario: Workspace documentation describes module responsibilities
- **WHEN** top-level workspace docs describe the data-to-research workflow
- **THEN** they identify `market-data-platform` as the market data operations owner and `cross-sectional-trees` as the downstream research consumer

### Requirement: Governance Prevents Ownership Regression
The system SHALL include tests or static governance checks that flag newly introduced data-production, health-check, current-refresh, registry, or asset-release implementations under `cross-sectional-trees`.

#### Scenario: Research repo adds a data operations command
- **WHEN** a change adds or modifies a `cross-sectional-trees` command or module that appears to download, mirror, inspect, refresh current contracts, build shared registries, or release market data assets
- **THEN** the relevant test or governance check fails unless the surface is an explicit platform-delegating compatibility wrapper

#### Scenario: Documentation reintroduces research-owned data operations
- **WHEN** `cross-sectional-trees` docs describe a platform-owned data operation as a research-repo responsibility
- **THEN** documentation checks fail or the review checklist requires correction before merge

#### Scenario: Platform command coverage changes
- **WHEN** a platform-owned operation is migrated or renamed
- **THEN** compatibility docs and downstream research wrapper tests are updated in the same change
