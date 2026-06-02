## ADDED Requirements

### Requirement: HK Public Split Manifest
The workspace SHALL maintain a versioned manifest that classifies 中国香港市场 related surfaces before any public demo split or main-workspace deletion.

The manifest MUST record each surface's owner repo, path or glob, action, public-safety classification, restore dependency, consumer-audit status, replacement or successor path, and removal condition. Valid actions MUST include `keep_in_main`, `move_to_public_demo`, `archive_in_public_demo`, `delete_after_split`, and `private_do_not_export`.

#### Scenario: Maintainer reviews HK surface ownership
- **WHEN** a maintainer opens the split manifest
- **THEN** they can identify which HK surfaces remain in the main workspace, which are public-demo candidates, which are archived provenance, which can be deleted after split evidence, and which MUST NOT be exported

#### Scenario: Manifest entry lacks a required decision
- **WHEN** a manifest record omits its action, public-safety classification, restore dependency, consumer-audit status, or removal condition
- **THEN** the manifest validation check fails with the affected record path or glob

### Requirement: Public Demo Staging Boundary
The demo staging tree SHALL be a self-contained public repository candidate that uses synthetic data only and does not depend on workspace packages or private runtime state.

Active demo code MUST live under the demo template's source, script, fixture, test, and active documentation paths. Public-safe historical material MUST be placed under an archive path and marked as provenance, not as an active workflow.

#### Scenario: Public demo runs outside the workspace
- **WHEN** the demo template is copied to an isolated directory with no workspace submodules available
- **THEN** its smoke workflow and unit tests run using only files inside the copied tree

#### Scenario: Demo code imports workspace packages
- **WHEN** active demo source, tests, or scripts import `market_data_platform`, `hk_data_platform`, `cstree`, or `quant_execution_engine`
- **THEN** the demo boundary check fails and reports the importing file

### Requirement: Export Safety And Evidence
The HK public demo exporter SHALL export only allowlisted files, generated synthetic samples, and export evidence.

The exporter MUST reject `.git`, credentials, `.env*`, provider cache, licensed data formats, compressed archives, private output directories, oversized files, non-UTF-8 files, local absolute paths, broker integrations, and provider-specific runtime dependencies in the staged public tree. The generated `export-manifest.json` MUST include source revision, public repository metadata, included files, generated files, split manifest version, scan status, offline smoke status, and quality-check status.

#### Scenario: Safe staged export
- **WHEN** the exporter stages the public demo into an empty directory
- **THEN** it writes `export-manifest.json`, `samples/summary.json`, and `samples/targets.json`, and all scan, smoke, and quality statuses are `passed`

#### Scenario: Private or licensed content appears in staged export
- **WHEN** the staged tree contains a credential-like assignment, provider cache path, Parquet file, compressed archive, broker adapter, local absolute path, or non-allowlisted private output
- **THEN** the exporter fails before publication and reports the check name and relative path

### Requirement: Independent Demo Quality Gates
The public demo candidate SHALL define quality checks that can run independently of the superproject and submodules.

The active demo code MUST have commands or CI steps for unit tests, offline workflow generation, Ruff lint or format checks, and Pyright type checks. Archive paths MAY be excluded from strict Ruff/Pyright checks when they are explicitly documented as frozen provenance.

#### Scenario: Demo CI runs on a public repository checkout
- **WHEN** CI runs in the copied demo repository candidate
- **THEN** it executes the offline workflow, unit tests, Ruff, and Pyright without requiring provider credentials, broker credentials, submodules, or shared data roots

#### Scenario: Active demo quality regression
- **WHEN** active demo code introduces a lint failure, type-check failure, or broken offline sample generation
- **THEN** the demo quality gate fails before the staged tree is considered publishable

### Requirement: Main Workspace HK Cleanup Gates
The workspace SHALL NOT delete restore-sensitive or compatibility HK surfaces until their manifest records show the required evidence.

Deletion eligibility MUST require restore evidence when applicable, downstream consumer audit, replacement documentation, focused tests, rollback notes, and public split evidence when the surface is being moved or archived into the public demo candidate.

#### Scenario: Compatibility command is still pending audit
- **WHEN** an HK compatibility command has no completed consumer audit or replacement documentation
- **THEN** it remains in the main workspace and is marked as compatibility or retire-after-audit rather than deleted

#### Scenario: Surface is eligible for deletion
- **WHEN** a manifest record has completed restore evidence, consumer audit, replacement documentation, focused tests, rollback notes, and public split evidence where required
- **THEN** a follow-up implementation change can remove the surface and update docs/tests in the owning repository

### Requirement: Split Documentation
The workspace documentation SHALL explain the relationship among active A-share work, frozen HK restore evidence, and the public demo staging tree.

Docs MUST state that the public demo is a clean-room, synthetic-data, paused-maintenance repository candidate and is not a workspace submodule, package dependency, required CI target, release gate, trading system, or source of licensed market data.

#### Scenario: Maintainer reads HK archive docs
- **WHEN** a maintainer opens the HK archive or public demo export documentation
- **THEN** they can find the split manifest, export command, publication review checklist, non-exportable surfaces, and post-split cleanup gates

#### Scenario: Reader looks for active workflow direction
- **WHEN** a reader starts from the root docs
- **THEN** they can identify that active mainline work remains data platform -> strategy research -> trading execution for A-share contracts, while the 中国香港市场 public demo is an external frozen reference
