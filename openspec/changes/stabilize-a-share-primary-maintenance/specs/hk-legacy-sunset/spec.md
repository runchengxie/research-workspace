## ADDED Requirements

### Requirement: 港股 surfaces are retired by lifecycle class
The workspace SHALL classify retained 港股 surfaces as `shared_active`, `frozen_compatibility`,
`archived_provenance`, or `retire_after_audit`. A surface MUST NOT be removed solely because 港股
strategy research is paused.

#### Scenario: 港股 removal candidate is reviewed
- **WHEN** maintainers evaluate a 港股 implementation, configuration, or document for removal
- **THEN** the surface inventory records its lifecycle class, owner, consumers, tests, and rollback evidence
- **THEN** removal proceeds only when the class and evidence permit it

### Requirement: Restore-critical and multi-market surfaces remain available
The workspace MUST retain 港股 freeze and hydrate operations, restore-critical platform code,
explicit legacy research entry points, and shared multi-market execution behavior until a
replacement and restore evidence are available.

#### Scenario: Historical 港股 reproduction is needed
- **WHEN** an operator needs to reproduce a historical 港股 run
- **THEN** the documented flow verifies the cold-storage snapshot and hydrates it explicitly
- **THEN** A 股 active assets are not overwritten

### Requirement: Further retirement requires external-state verification
Before removing restore-sensitive 港股 code, the workspace MUST verify that required cold-storage
archives are reachable and that restore-drill evidence, source tags, archive manifests, and
consumer audits are current.

#### Scenario: Cold-storage snapshot is missing on the current machine
- **WHEN** the configured 港股 cold-storage directory is unavailable
- **THEN** restore-sensitive retirement remains blocked
- **THEN** tracked historical restore evidence is not described as proof that immediate local hydration is possible

### Requirement: Public 港股 demo remains a one-way clean-room export
The workspace SHALL publish any public 港股 portfolio demo only through an allowlisted clean-room
export. The demo MUST exclude Git history, licensed or real market data, provider caches,
credentials, broker adapters, private outputs, and historical return promotion.

#### Scenario: Demo staging tree is reviewed
- **WHEN** the public demo exporter creates or scans a staging tree
- **THEN** credential, path, forbidden-file, size, and offline-smoke checks pass before manual publication
- **THEN** the demo contains synthetic fixtures and paused-maintenance disclaimers

### Requirement: Public demo does not become a workspace dependency
The public 港股 demo SHALL remain an external portfolio reference and MUST NOT become a required
submodule or a bidirectional synchronization target.

#### Scenario: Workspace checks run without demo clone
- **WHEN** the external public demo repository is absent locally
- **THEN** required workspace doctor, test, and quality checks still run successfully
