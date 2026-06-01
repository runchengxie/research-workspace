## ADDED Requirements

### Requirement: Pyright is the delegated hard type gate
The superproject SHALL delegate hard type-checking profiles for active subprojects to Pyright through `scripts/submodule_checks.json`.

#### Scenario: Type profile is inspected
- **WHEN** a maintainer inspects each active subproject `type` profile in `scripts/submodule_checks.json`
- **THEN** `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine` each run Pyright as the hard type gate

#### Scenario: Full profile is inspected
- **WHEN** a maintainer inspects each active subproject `full` profile
- **THEN** the profile includes the subproject `type` profile and does not make mypy a hidden hard gate

### Requirement: qexec mypy remains advisory during bake period
The superproject SHALL keep `quant-execution-engine` mypy as a separate advisory profile until a release review explicitly removes it.

#### Scenario: qexec advisory profile is inspected
- **WHEN** a maintainer inspects `quant-execution-engine` profiles in `scripts/submodule_checks.json`
- **THEN** `mypy_advisory` exists as a separate profile and is not included in `full`

#### Scenario: Release review evaluates mypy removal
- **WHEN** the next release review evaluates removing mypy from `quant-execution-engine`
- **THEN** it verifies that mypy found no unique blocking issues, Pyright warnings remain classified, and documentation/tasks record the removal decision

### Requirement: Type status is reported precisely
Documentation SHALL state that the workspace has migrated hard type gates to Pyright, while avoiding claims that mypy has been fully removed or that all repositories have strict full-project Pyright coverage.

#### Scenario: Type migration is summarized
- **WHEN** documentation summarizes the mypy-to-Pyright migration
- **THEN** it says Pyright is the hard gate across active subprojects, including `quant-execution-engine`, and says `quant-execution-engine` mypy remains advisory during the bake period

#### Scenario: Pyright coverage is summarized
- **WHEN** documentation describes Pyright coverage or warning state
- **THEN** it distinguishes Pyright errors that block the hard gate from classified warnings and staged/basic coverage constraints

### Requirement: Type-gate rollback is explicit
The superproject SHALL require an explicit rollback decision before restoring mypy as a hard type gate for `quant-execution-engine`.

#### Scenario: Pyright gate must be rolled back
- **WHEN** maintainers decide Pyright cannot remain the `quant-execution-engine` hard type gate
- **THEN** they update `scripts/submodule_checks.json`, documentation, and release notes to restore the mypy hard-gate command intentionally

#### Scenario: Advisory mypy fails
- **WHEN** `quant-execution-engine` `mypy_advisory` fails during the bake period
- **THEN** the failure is recorded as advisory unless a maintainer explicitly promotes it to a blocking release criterion
