## ADDED Requirements

### Requirement: Demo export is a clean-room repository snapshot
The HK public demo exporter SHALL create a new staged repository snapshot from an explicit allowlist and SHALL NOT copy the active repository Git history.

#### Scenario: Demo snapshot is generated
- **WHEN** a maintainer runs the demo export workflow
- **THEN** the staged output contains only allowlisted files plus generated demo assets and does not contain the source `.git` directory

### Requirement: Demo export blocks sensitive and licensed content
The HK public demo exporter SHALL fail review when the staged tree contains credentials, local environment files, provider caches, licensed market data, private research outputs, disallowed absolute local paths, or files above the configured size limit.

#### Scenario: Local path leaks into documentation
- **WHEN** a staged file contains a disallowed path such as a maintainer home-directory path
- **THEN** the public-safety scan fails and identifies the file

#### Scenario: Provider data is staged
- **WHEN** the staged tree includes a Parquet market-data file, provider cache, private report, or non-synthetic market fixture
- **THEN** the public-safety scan fails before publication

#### Scenario: Secret-like content is staged
- **WHEN** the scan detects a credential file or secret-like token pattern
- **THEN** the public-safety scan fails before publication

### Requirement: Demo runs without private providers
The HK public demo SHALL include synthetic fixtures, a minimal runnable strategy path, minimal CI, and sample outputs generated from synthetic fixtures, including a sample `summary.json` and a sample `targets.json`.

#### Scenario: External user runs the demo offline
- **WHEN** an external user follows the README without provider credentials or private data
- **THEN** the documented smoke command completes and reproduces the synthetic sample workflow

### Requirement: Demo positioning is explicit
The HK public demo README SHALL state that the project is a paused-maintenance historical engineering demo, excludes real market data, is not investment advice, and is not an active dependency of the A-share workspace.

#### Scenario: Workspace links to public demo
- **WHEN** the external demo repository is published
- **THEN** the workspace links to it as an external portfolio reference and does not add it as a required submodule

### Requirement: Demo export is reviewable and reproducible
The demo export workflow SHALL emit a manifest containing the selected source revision, included files, generated fixture files, scan results, and smoke-test result. Publication SHALL remain an explicit maintainer action after review.

#### Scenario: Maintainer reviews a staged export
- **WHEN** the exporter finishes successfully
- **THEN** the maintainer can inspect a machine-readable manifest and smoke-test evidence before creating or updating a public repository

#### Scenario: Export succeeds locally
- **WHEN** the staged export passes scans and smoke tests
- **THEN** the workflow does not automatically publish or push the snapshot without a separate explicit maintainer action
