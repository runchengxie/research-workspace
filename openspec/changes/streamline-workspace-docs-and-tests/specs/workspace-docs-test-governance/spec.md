## ADDED Requirements

### Requirement: New Maintainer Documentation Entrypoints
The workspace documentation SHALL provide short first-read entrypoints for the superproject and each initialized submodule.

Each entrypoint MUST state the repo responsibility, current active market direction, first verification command, and next documents to read. Top-level docs MUST stay limited to cross-repo contracts, submodule boundaries, version locking, release checks, and workspace health.

#### Scenario: Reader starts from the superproject
- **WHEN** a new maintainer opens the root `README.md` and `docs/README.md`
- **THEN** they can identify the data-platform -> strategy-research -> execution-engine handoff, the active A-share direction, the 中国香港市场 archive/demo boundary, and the bootstrap and doctor commands without reading dated handoff notes

#### Scenario: Reader enters a submodule
- **WHEN** a new maintainer opens a submodule `README.md` and `docs/README.md`
- **THEN** they can identify that submodule's current responsibilities, test entrypoints, and next reference documents without relying on the superproject docs

### Requirement: Active Reference Archive Taxonomy
Documentation SHALL distinguish active guidance, stable reference material, and archived historical records.

Dated session handoffs, freeze notes, migration records, and completed phase checklists MUST live under an archive path or archive index. Primary docs MUST link to archive indexes only when historical context is needed for current work.

#### Scenario: Dated records are demoted from the primary path
- **WHEN** documentation includes a file whose name begins with `session-handoff-` or describes a completed dated freeze/release
- **THEN** that file is listed from an archive index and absent from the primary newcomer reading order

#### Scenario: Historical research remains recoverable
- **WHEN** 中国香港市场 research notes or vendor reference pages are moved or demoted
- **THEN** an index preserves their titles, status, last-check date when available, and current replacement or successor reading path

### Requirement: Version Matrix Reflects Current Checkout State
The version matrix workflow SHALL describe the current workspace checkout, submodule commits, submodule initialization state, and local dirty state.

The generator MUST produce clear output in a full git checkout and a clear limitation message in a plain source snapshot without `.git`. `docs/version-matrix.md` MUST say how to regenerate the matrix and MUST avoid presenting old manual rows as the current state.

#### Scenario: Full git checkout
- **WHEN** `python scripts/print_version_matrix.py` runs in an initialized git checkout
- **THEN** it prints the workspace commit, each expected submodule commit, and dirty or missing indicators without crashing

#### Scenario: Plain source snapshot
- **WHEN** `python scripts/print_version_matrix.py` runs outside a git checkout
- **THEN** it exits with an actionable message explaining that commit data requires a git checkout with initialized submodules

### Requirement: Documentation Tests Protect Facts
Documentation tests SHALL protect stable facts and interfaces instead of exact prose.

Tests MUST check commands, parser leaf commands, contract paths, file links, archive indexes, pytest markers, quality gate names, and public/private entrypoint layering. Tests MUST avoid requiring one exact Chinese sentence when equivalent wording preserves the same fact.

#### Scenario: Prose wording changes
- **WHEN** a maintainer rewrites a sentence to reduce defensive or translated-sounding wording while keeping the command, path, contract, and capability boundary unchanged
- **THEN** documentation tests continue to pass

#### Scenario: Contract fact changes accidentally
- **WHEN** a maintainer removes `metadata/current_assets/a_share_current.json`, `targets.json`, or a public CLI command from the relevant docs
- **THEN** documentation tests fail with the missing fact and owning document

### Requirement: Language Quality Checks Are Scoped
Language quality checks SHALL scan active README, AGENTS, and docs recursively while allowing archived historical prose to remain stable.

Active docs MUST prefer direct statements over repeated defensive phrasing. Checks MUST report occurrences of unnecessary contrast phrases with file and line context. Safety caveats and technical negation MUST use an explicit allowlist or archive exemption when they remain in checked paths.

#### Scenario: Active docs contain avoidable contrast wording
- **WHEN** an active documentation page contains an unnecessary "不是 / 而是 / 不代表 / 不等于" construction
- **THEN** the style check reports the file, line, and phrase so the maintainer can rewrite it directly

#### Scenario: Archived notes retain historical prose
- **WHEN** an archived research note contains historical wording that would fail the active style check
- **THEN** the style check either skips the archive path or reports it only in an advisory summary

### Requirement: CLI And Test Documentation Coverage
Each submodule SHALL maintain lightweight documentation consistency checks for public CLI commands and declared test markers.

`cross-sectional-trees` MUST keep parser-derived public CLI coverage while reducing exact prose locks. `market-data-platform` MUST add parser-derived CLI documentation coverage for its public commands. `quant-execution-engine` MUST check that documented top-level CLI commands, pytest markers, and broker smoke docs match the parser and `pyproject.toml`.

#### Scenario: New public CLI command is added
- **WHEN** a public CLI command is added to a submodule parser
- **THEN** the relevant docs coverage test fails until the command appears in the owning CLI or operations documentation

#### Scenario: Pytest marker changes
- **WHEN** a marker is added to or removed from `quant-execution-engine/pyproject.toml`
- **THEN** the testing documentation consistency check fails until `docs/testing.md` reflects the marker set

### Requirement: Verification Follows Repository Boundaries
The implementation SHALL verify each change at the narrowest owning boundary before running broader checks.

Focused tests MUST run in the owning repo for each touched area. The final superproject summary MUST report status in the order data platform -> strategy research -> execution engine -> top-level docs/doctor -> remaining limitations.

#### Scenario: Documentation restructure touches multiple repos
- **WHEN** implementation moves or edits docs in multiple submodules
- **THEN** focused tests for each touched submodule run before the final top-level doctor and docs checks

#### Scenario: A check cannot run
- **WHEN** a required check cannot run because of missing credentials, missing optional dependencies, network limits, or absent `DATA_PLATFORM_ROOT`
- **THEN** the final summary states the skipped check, the concrete reason, and the command to run when prerequisites are available
