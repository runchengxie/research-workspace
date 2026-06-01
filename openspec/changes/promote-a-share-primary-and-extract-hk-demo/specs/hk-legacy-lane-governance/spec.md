## ADDED Requirements

### Requirement: HK surfaces are classified before removal
The workspace SHALL maintain a tracked inventory that classifies HK-related code, configs, docs, tests, and lifecycle tooling as `shared_active`, `frozen_compatibility`, `archived_provenance`, or `retire_after_audit` before files are removed from an active repository.

#### Scenario: Research-only HK experiments are inventoried
- **WHEN** bulky HK experiment configs and historical research notes are reviewed
- **THEN** the inventory records whether they move to archive/demo extraction or remain as a minimal compatibility surface

#### Scenario: Shared code contains HK references
- **WHEN** a market-agnostic module also contains HK branches used by supported behavior
- **THEN** the module is not removed solely because an HK text scan matched it

### Requirement: Data-platform HK restore support remains available until retirement
`market-data-platform` SHALL retain HK freeze markers, hydrate support, restore instructions, and restore-critical code until a restore drill succeeds and documented downstream retirement conditions pass.

#### Scenario: Local cold snapshot has been removed
- **WHEN** the HK freeze marker reports `local_snapshot_available: false`
- **THEN** restore documentation requires downloading the release archive, verifying its checksum, extracting it to the recorded cold path, and only then running hydrate

#### Scenario: Restore-critical workflow is proposed for removal
- **WHEN** an HK data workflow is required by the documented restore path
- **THEN** the workflow remains in `market-data-platform` until a replacement restore path is validated

### Requirement: Strategy repository keeps a bounded HK compatibility route
`cross-sectional-trees` SHALL keep an explicitly named HK compatibility route for historical reproduction until its downstream dependencies are retired, while SHALL NOT present that route as the active research default.

#### Scenario: User needs historical HK reproduction
- **WHEN** the HK data and research archives have been hydrated
- **THEN** the documented HK compatibility preset can run without changing the A-share primary default

#### Scenario: New HK research feature is proposed
- **WHEN** no funding, paper-trading, manual-tracking, or cross-market validation need has been documented
- **THEN** the active workspace rejects expanding the HK research lane

### Requirement: Execution engine retains valid multi-market behavior
`quant-execution-engine` SHALL retain supported HK parsing, FX, symbol-normalization, and broker behavior independently of whether the HK strategy lane is actively maintained.

#### Scenario: HK strategy lane is archived
- **WHEN** HK research code is extracted or retired from `cross-sectional-trees`
- **THEN** `quant-execution-engine` HK support remains unchanged unless a separate execution capability review approves its removal

### Requirement: HK retirement uses dependency evidence and rollback artifacts
The workspace SHALL require a dependency audit, focused compatibility tests, restore evidence, a reproducible source tag, and rollback documentation before removing an audited HK compatibility surface.

#### Scenario: Dependency audit finds an active consumer
- **WHEN** an active command, preset, script, CI job, or downstream workflow still depends on an HK surface
- **THEN** the surface remains supported or receives an explicit migration before removal

#### Scenario: Audited research-only surface has no active consumer
- **WHEN** dependency evidence shows that an HK research-only surface is archived provenance and restore does not require it
- **THEN** the surface can be extracted or retired from the active strategy repository with its rollback reference recorded
