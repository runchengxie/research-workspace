## ADDED Requirements

### Requirement: Clean-room HK public demo export
The workspace SHALL publish any HK public demo only from an allowlisted clean-room export that excludes Git history, licensed market data, provider cache, credentials, private research outputs, broker adapters, and production performance claims.

#### Scenario: Export uses only curated files
- **WHEN** a maintainer stages the HK public demo for publication
- **THEN** the staged tree contains only files copied from the versioned allowlist plus generated synthetic sample outputs and `export-manifest.json`

#### Scenario: Unsafe content blocks export
- **WHEN** the export scanner detects a forbidden path, archive/data suffix, oversized file, credential-like assignment, provider cache, or local absolute path
- **THEN** the export command fails and the staged tree is not considered publishable

### Requirement: Public demo remains external to the workspace
The workspace SHALL treat the HK public demo repository as an external portfolio reference, not as a submodule, package dependency, required CI target, or release-matrix participant.

#### Scenario: Workspace links the public demo
- **WHEN** top-level documentation references the HK public demo
- **THEN** it identifies the repository as an external paused-maintenance reference and does not add it to `.gitmodules`, delegated checks, or release blocking profiles

#### Scenario: Active checks run without the public demo repository
- **WHEN** workspace doctor, smoke contracts, or submodule checks run in a clone that has no public demo checkout
- **THEN** those checks complete without requiring the public demo repository to exist locally

### Requirement: Public demo documentation sets strict expectations
The public demo SHALL state that it is synthetic-only, paused-maintenance, not investment advice, not a live trading system, and intentionally omits licensed data, credentials, broker integration, private research outputs, and production performance claims.

#### Scenario: Reader opens the public demo README
- **WHEN** a reader opens the public demo README
- **THEN** the first-screen description makes the synthetic portfolio-demo scope and paused-maintenance status clear

#### Scenario: Reader checks omitted content
- **WHEN** a reader looks for real data, broker execution, or performance claims in the public demo documentation
- **THEN** the documentation explicitly lists those items as intentionally omitted

### Requirement: Publication review records evidence
The workspace SHALL require publication review evidence before a maintainer pushes the clean-room HK demo to a public repository.

#### Scenario: Demo is ready to publish
- **WHEN** a maintainer decides a staged demo tree is ready for public publication
- **THEN** the review includes `scan=passed`, `offline_smoke=passed`, the generated manifest, and a human grep review for sensitive/provider/local-path terms

#### Scenario: Demo contains a large or binary artifact
- **WHEN** the staged public demo contains large files, archives, Parquet/cache/pickle files, or non-UTF-8 files not explicitly allowed
- **THEN** publication is blocked until those files are removed or the export policy is intentionally changed
