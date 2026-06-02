## ADDED Requirements

### Requirement: Private archive candidate is staged from an explicit manifest
The workspace SHALL define a versioned private-archive manifest for 中国香港市场 legacy code and provenance. Each archived record MUST identify its owner repository, source revision or tag, tracked path allowlist, lifecycle classification, restore dependency, consumer-audit state, replacement documentation, rollback notes, focused tests, and archive checksum.

#### Scenario: Stage a private archive candidate
- **WHEN** a maintainer runs the private archive export command against clean source revisions
- **THEN** the system stages only allowlisted tracked files outside the superproject, emits a machine-readable export manifest with checksums, and labels the candidate as paused-maintenance and restore-only

#### Scenario: Reject an unresolved archive record
- **WHEN** an archive-manifest record omits its source revision, owner, path allowlist, checksum policy, or lifecycle evidence
- **THEN** the archive gate fails and reports the incomplete record without deleting or moving source files

### Requirement: Private archive candidate excludes runtime data and secrets
The private archive exporter MUST reject credentials, repo-local environment files, provider cache, Parquet market data, research run outputs, execution audit logs, and other runtime artifacts. Provider-specific business code MAY be included only when the private manifest classifies it as archive content.

#### Scenario: Reject accidental data export
- **WHEN** an allowlisted archive path resolves to a credential file, provider cache, market-data file, research output, or execution audit log
- **THEN** the exporter fails with a path-level diagnostic and does not mark the archive candidate ready

### Requirement: Active and restore-sensitive surfaces remain in the active repositories
The archive workflow SHALL retain `marketdata migration freeze-hk`, `marketdata migration hydrate-hk`, freeze markers, standard `targets.json` multi-market parsing, execution risk controls, and broker runtimes in their owning active repositories. LongPort runtime MUST remain owned by `quant-execution-engine` and MUST NOT be classified as 中国香港市场 legacy archive content.

#### Scenario: Classify retained execution support
- **WHEN** the archive gate evaluates LongPort runtime or shared HK market parsing in `quant-execution-engine`
- **THEN** the gate records the surface as `private_runtime` or `shared_active` and excludes it from the archive export allowlist

### Requirement: Removal requires a separate follow-up change
The workspace MUST NOT remove or migrate a restore-sensitive or compatibility surface from an active repository unless its deletion gate is ready. Readiness MUST require current restore evidence, completed consumer audit, replacement documentation, rollback notes, passing focused tests, source tag evidence, and private archive export evidence. Actual removal MUST occur in a separate follow-up change after the required zero-usage release window.

#### Scenario: Block premature removal
- **WHEN** a maintainer checks a surface whose consumer audit is pending or whose zero-usage release window has not elapsed
- **THEN** the archive gate reports the blocker and keeps the surface in the active repository

#### Scenario: Permit a follow-up removal review
- **WHEN** all deletion-gate fields are complete and the required zero-usage release window has elapsed
- **THEN** the archive gate marks the surface eligible for a separate removal review without deleting it automatically

### Requirement: Archive repository stays outside the active workspace graph
The private archive repository MUST be private, paused-maintenance, and restore-only. It MUST NOT become a superproject submodule, default CI dependency, release-matrix member, or runtime dependency of the A 股 mainline.

#### Scenario: Audit workspace integration
- **WHEN** the workspace doctor or archive gate evaluates the superproject configuration
- **THEN** it fails if the private archive repository is added as an active submodule or required A 股 workflow dependency
