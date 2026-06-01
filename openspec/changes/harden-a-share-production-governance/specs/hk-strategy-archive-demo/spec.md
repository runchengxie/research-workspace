## ADDED Requirements

### Requirement: 港股 strategy surfaces are lifecycle classified before removal
The workspace SHALL classify 港股 strategy code, configs, docs, tests, and scripts as `shared_active`, `frozen_compatibility`, `archived_provenance`, or `retire_after_audit` before moving or removing them from active repositories.

#### Scenario: HK-named file is found
- **WHEN** a file path or symbol contains `hk`
- **THEN** maintainers classify it by ownership and downstream dependency instead of deleting it solely by text match

#### Scenario: Shared multi-market code has HK branches
- **WHEN** shared pipeline, target export, symbol parsing, FX, or execution code contains 港股 behavior still covered by supported tests
- **THEN** the code remains `shared_active`

### Requirement: 港股 compatibility route remains explicit
`cross-sectional-trees` SHALL retain an explicit 港股 compatibility route until downstream consumers and restore needs are retired.

#### Scenario: User needs historical 港股 reproduction
- **WHEN** 港股 data and research archives have been hydrated
- **THEN** the user can run a documented `hk` preset or equivalent compatibility route without changing the A 股 default

#### Scenario: Default route is inspected
- **WHEN** docs or CLI examples describe the default strategy route
- **THEN** they identify A 股 as default and 港股 as legacy compatibility

### Requirement: Archived provenance leaves active navigation
Bulky 港股 experiments, historical research notes, and research-only scripts SHALL move out of active A 股 navigation before they are removed from the repository.

#### Scenario: Research note remains in repository
- **WHEN** a 港股 historical note is retained
- **THEN** it is indexed as historical provenance or legacy reference rather than current research guidance

#### Scenario: Experiment config remains in repository
- **WHEN** a 港股 experiment config is retained for reproducibility
- **THEN** catalog lifecycle and docs mark it as legacy or archived provenance, not active primary research

### Requirement: Removal requires archive and rollback evidence
港股 research-only surfaces SHALL NOT be removed until source reference, archive manifest, restore evidence, dependency audit, focused compatibility tests, and rollback instructions exist.

#### Scenario: Surface has no active consumer
- **WHEN** dependency audit finds no active command, CI job, script, preset, or downstream workflow depending on a 港股 research-only surface
- **THEN** the surface may be moved to archive or removed only after restore and rollback evidence is recorded

#### Scenario: Active consumer exists
- **WHEN** dependency audit finds an active consumer for a 港股 surface
- **THEN** maintainers either keep the surface or provide a migration path before removal

### Requirement: `alloc-hk` is deprecated before any retirement
The `alloc-hk` command and related modules SHALL be treated as frozen compatibility until a documented usage audit supports migration, extraction, or removal.

#### Scenario: New A 股 workflow is documented
- **WHEN** docs describe A 股 allocation or execution handoff
- **THEN** they direct users to market-agnostic `alloc`, `export-targets`, and execution-engine dry-run rather than `alloc-hk`

#### Scenario: `alloc-hk` retirement is proposed
- **WHEN** maintainers propose removing or extracting `alloc-hk`
- **THEN** the proposal includes consumers, replacement command, test coverage, deprecation notice, and rollback path

### Requirement: Public 港股 demo is clean-room and synthetic-only
The public 港股 demo SHALL be produced from an allowlisted clean-room export without source Git history, licensed market data, credentials, provider caches, private outputs, or local absolute paths.

#### Scenario: Demo export runs
- **WHEN** the exporter stages the public demo
- **THEN** it copies only allowlisted files, generates synthetic sample outputs, runs offline smoke tests, scans the staged tree, and writes an export manifest

#### Scenario: Sensitive content is detected
- **WHEN** the staged demo tree contains credentials, `.env*`, provider data, Parquet files, private artifacts, large archives, or disallowed local paths
- **THEN** the scan fails before publication

### Requirement: Public demo is an external reference only
The workspace SHALL link the published 港股 demo as an external portfolio reference and SHALL NOT add it as a required submodule or active dependency.

#### Scenario: Demo repository is published
- **WHEN** a maintainer explicitly publishes or updates the public demo repository
- **THEN** workspace docs may link to it as paused-maintenance historical reference while default A 股 workflows remain independent

#### Scenario: User runs workspace checks
- **WHEN** workspace tests, doctor checks, or submodule checks run
- **THEN** they do not require the external public demo repository to be cloned
