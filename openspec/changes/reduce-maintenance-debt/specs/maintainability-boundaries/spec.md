## ADDED Requirements

### Requirement: Maintainability metrics
The system SHALL report maintainability metrics for Python source files, including file length, function length, argument count, public export count, and complexity-rule diagnostic counts. The report MUST identify current outliers and support baseline comparison.

#### Scenario: Developer inspects long files and functions
- **WHEN** a developer runs the maintainability metrics report
- **THEN** the system lists the largest files and longest functions in source modules
- **AND** the report is suitable for deciding which refactor target should be handled first

#### Scenario: New severe outlier is introduced
- **WHEN** a change introduces a file or function exceeding the accepted maintainability baseline
- **THEN** the governance check fails or requires an explicit baseline update with justification

### Requirement: Public API boundary control
The system SHALL distinguish stable public API, internal cross-module API, and private helpers. Public facade modules MUST expose only documented stable symbols or explicitly documented compatibility exports.

#### Scenario: Private helper is exported through public facade
- **WHEN** a helper whose name or ownership marks it private is imported into a public API facade
- **THEN** the governance check flags the export unless it is documented as a compatibility exception

#### Scenario: Test needs a private helper
- **WHEN** a test needs to exercise a private helper
- **THEN** the test imports the helper from its owning module rather than through the public facade

### Requirement: Architecture dependency boundaries
The system SHALL preserve dependency direction between core contracts, providers, pipelines, CLI adapters, release tooling, and reports. Core contract modules MUST NOT import HK-specific pipelines, CLI modules, provider runtimes, or release workflow code.

#### Scenario: Core module imports HK asset implementation
- **WHEN** a core contract, path, registry, or manifest module imports an HK asset pipeline module
- **THEN** the architecture check fails and reports the dependency violation

#### Scenario: CLI invokes business logic
- **WHEN** a CLI module needs to run a workflow
- **THEN** it delegates through a command registry, adapter, or workflow function instead of embedding provider, persistence, validation, and reporting logic directly in argument handling

### Requirement: Incremental refactor pattern for long workflows
The system SHALL refactor oversized workflows by extracting cohesive plan/config, provider/fetch, transform, validate, persist, manifest, and report steps. New configuration objects MUST prefer dataclasses, TypedDicts, or Protocol-backed interfaces over large positional parameter lists.

#### Scenario: Long workflow is refactored
- **WHEN** a long workflow function is selected for cleanup
- **THEN** the refactor preserves behavior through focused tests
- **AND** separates at least one cohesive step into a smaller function or configuration object

#### Scenario: New workflow requires many parameters
- **WHEN** a new workflow function would require a large positional parameter list
- **THEN** the implementation introduces a typed configuration object or request model instead
