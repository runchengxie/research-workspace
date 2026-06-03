## ADDED Requirements

### Requirement: HK research surface inventory is machine-readable
The superproject SHALL maintain a machine-readable 港股 research surface inventory that classifies relevant files by owner, category, lifecycle, action, dependencies, and migration status.

#### Scenario: Inventory is generated
- **WHEN** the inventory script scans the superproject and submodules
- **THEN** it records HK research, liveops, config, docs, tests, data-platform, and execution-contract surfaces with explicit `move`, `keep`, `archive`, or `delete_later` actions

#### Scenario: Shared execution surface is detected
- **WHEN** the inventory finds standard multi-market `targets.json`, FX, broker, risk, or LongPort execution code
- **THEN** it classifies the surface as shared active execution infrastructure rather than 港股 research code to move

### Requirement: Independent HK research repo skeleton is runnable
The split SHALL create or document an independently runnable 港股 research repository skeleton with package metadata, README, baseline configs, source modules, synthetic fixtures, and smoke tests.

#### Scenario: HK smoke test runs without licensed data
- **WHEN** the HK research repo smoke test is run with synthetic fixtures
- **THEN** it builds a minimal universe, features, signals, positions, and target export without requiring provider credentials

#### Scenario: HK repo reads platform data contract
- **WHEN** real data is configured
- **THEN** the HK research repo reads 中国香港市场 current assets from `market-data-platform` contracts instead of reimplementing data production

### Requirement: HK migration follows staged compatibility gates
Migration of `alloc_hk*`, HK research scripts, HK configs, and HK docs MUST be staged behind inventory, smoke tests, restore evidence, replacement docs, and compatibility gates.

#### Scenario: alloc-hk migration starts
- **WHEN** 港股 allocation modules are moved or wrapped
- **THEN** the A 股 primary research path remains unchanged and the deprecated `cstree alloc-hk` entrypoint either forwards to the HK repo or reports a clear migration message

#### Scenario: Source removal is requested
- **WHEN** a later change proposes deleting an HK legacy surface from the active repository
- **THEN** deletion is blocked unless the archive gate, zero-usage window, replacement docs, and focused owner-repo tests pass

### Requirement: Data platform and execution boundaries remain shared
The split MUST NOT move restore-critical 中国香港市场 data platform commands, current contract mechanisms, standard `targets.json` parsing, FX handling, broker adapters, risk controls, or execution audit logic into the HK research repo.

#### Scenario: HK repo exports execution targets
- **WHEN** the HK research repo generates target weights
- **THEN** it emits the same standard `targets.json` contract consumed by `quant-execution-engine` and does not include broker execution code

#### Scenario: HK data is refreshed
- **WHEN** 港股 data assets need production, validation, current refresh, freeze, or hydrate operations
- **THEN** those operations remain owned by `market-data-platform`

### Requirement: Active docs use primary A 股 wording and HK lane references
Workspace and owner-repo documentation SHALL present A 股 as the active primary research lane and 中国香港市场 / 港股 research as an independent or legacy lane without changing public asset keys, historical filenames, or compatibility command names.

#### Scenario: Workflow documentation is updated
- **WHEN** a maintainer reads the platform workflow and market lifecycle docs
- **THEN** the docs describe data platform -> strategy research ->交易执行 boundaries and link to HK split or archive records for 港股-specific work
