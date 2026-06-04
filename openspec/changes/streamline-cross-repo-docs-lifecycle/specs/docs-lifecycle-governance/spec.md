## ADDED Requirements

### Requirement: Documentation lifecycle metadata
Documentation entry points and archived records MUST declare their lifecycle state and source-of-truth role in a machine-readable or consistently parseable status block.

#### Scenario: Active entry point declares ownership
- **WHEN** a maintainer opens a top-level or `cross-sectional-trees` docs entry point
- **THEN** the page identifies its lifecycle state, owner scope, last verification date, and whether it is a source of truth

#### Scenario: Superseded page points to replacement
- **WHEN** a page is retained only for compatibility after being superseded
- **THEN** the page identifies the current replacement or archive entry before any historical narrative

### Requirement: Superproject docs remain cross-repo focused
`research-workspace` active docs MUST only cover cross-repo workflow, contracts, version combinations, release or checklist gates, workspace maintenance, and current market transition playbooks.

#### Scenario: Top-level process record is archived
- **WHEN** a document records a one-time handoff, freeze, restore drill, release note, or historical review
- **THEN** it is routed under `docs/archive/` and linked from an archive entry rather than from the primary reading path

#### Scenario: Top-level duplicate checklist is consolidated
- **WHEN** two active top-level docs repeat the same A-share readiness or Hong Kong market archive gate
- **THEN** one source-of-truth page keeps the current operational guidance and the other page becomes a short compatibility pointer or archive record

### Requirement: Hong Kong market archive routing
The top-level Hong Kong market archive MUST provide a single human-readable entry for frozen data assets, archived research outputs, public demo split state, private archive state, restore evidence, and removal gates.

#### Scenario: Maintainer reviews archive status
- **WHEN** a maintainer needs the current Hong Kong market archive status
- **THEN** `docs/archive/hk/README.md` links to the relevant manifests, evidence files, restore notes, and cleanup gates without requiring the maintainer to read multiple overlapping active docs

#### Scenario: Manifest owns inventory details
- **WHEN** a keep, move, archive, delete, restore-sensitive, or public-demo classification is needed
- **THEN** the structured manifest is the authoritative inventory and Markdown pages only summarize or link to that manifest

### Requirement: Cross-sectional research notes are archived provenance
`cross-sectional-trees` MUST treat Hong Kong market historical research notes as archived provenance unless a note is explicitly promoted to an active playbook or current research entry.

#### Scenario: New maintainer enters research docs
- **WHEN** a maintainer opens the active research documentation
- **THEN** active A-share or current research guidance is visible before archived Hong Kong market monthly or quarterly notes

#### Scenario: Historical note remains reproducible
- **WHEN** a maintainer needs to reproduce or audit a historical Hong Kong market run
- **THEN** the archive index links to the relevant note, config or run summary references, and any known authority precedence such as `config.used.yml` or `summary.json`

### Requirement: Overlapping subproject docs are consolidated
`cross-sectional-trees` docs MUST avoid multiple active pages that repeat the same legacy Hong Kong market data boundary, RQData sunset status, intraday asset status, or model-selection guidance.

#### Scenario: Legacy Hong Kong market data boundary is queried
- **WHEN** a maintainer needs to understand legacy Hong Kong market data consumption in `cross-sectional-trees`
- **THEN** one active or archive entry explains that data production and health checks live in `market-data-platform`, while old pages either link to that entry or move under archive

#### Scenario: Modeling guidance is queried
- **WHEN** a maintainer needs to choose among maintained models or understand why unsupported model families are out of scope
- **THEN** one modeling concept entry covers both selection rules and model landscape rationale, or separate pages clearly define non-overlapping purposes

### Requirement: Documentation tests enforce the new routing
Documentation tests MUST be updated to verify lifecycle routing, current source-of-truth links, and compatibility references after files move or shrink.

#### Scenario: File movement changes paths
- **WHEN** an active doc path is moved to archive or replaced by a compatibility stub
- **THEN** docs link tests and docs contract tests assert the new path, replacement link, or manifest entry instead of the obsolete active path

#### Scenario: Runtime contract tokens remain protected
- **WHEN** docs are streamlined
- **THEN** tests still protect public CLI tokens, market lifecycle tokens, canonical contract names, and restore-sensitive archive evidence
