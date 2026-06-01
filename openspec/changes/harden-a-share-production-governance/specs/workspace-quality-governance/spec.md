## ADDED Requirements

### Requirement: Quality profiles are delegated by repository
The workspace SHALL expose stable delegated quality profiles while each submodule owns its own lint, type, test, and coverage tool configuration.

#### Scenario: Superproject runs delegated checks
- **WHEN** a maintainer runs a superproject submodule check profile such as `lint`, `type`, `test`, or `full`
- **THEN** the workspace invokes the commands declared for each submodule without replacing that submodule's `pyproject.toml`, dependency groups, or ignore rules

#### Scenario: Submodule tool differs
- **WHEN** two submodules use different type checkers for their hard `type` profile
- **THEN** the workspace treats both as valid if the delegated profile is documented and passes in that submodule

### Requirement: Superproject checks stay in superproject scope
The superproject SHALL NOT use root-level lint or type-check configuration to scan submodule source trees as if the workspace were a single Python package.

#### Scenario: Top-level Ruff is added
- **WHEN** the superproject adds a Ruff check
- **THEN** the configured include scope is limited to superproject-owned paths such as `scripts/` and `tests/`

#### Scenario: Submodule sources are present
- **WHEN** `market-data-platform`, `cross-sectional-trees`, or `quant-execution-engine` source files are present under the workspace
- **THEN** top-level checks exclude those trees and rely on delegated submodule profiles instead

### Requirement: Execution engine keeps mypy as the hard type gate during Pyright evaluation
`quant-execution-engine` SHALL retain mypy as its hard type gate until a documented migration review proves that Pyright is at least as useful and no noisier for execution-critical code.

#### Scenario: Pyright advisory is enabled
- **WHEN** a Pyright advisory profile is added for `quant-execution-engine`
- **THEN** the existing mypy command remains the hard `type` profile and Pyright results are reported separately

#### Scenario: Pyright produces optional SDK noise
- **WHEN** Pyright reports missing stubs or dynamic typing issues from optional broker SDKs or UI dependencies
- **THEN** those findings are classified as advisory until the optional dependency boundary is explicitly modeled

### Requirement: Hard and advisory checks are classified
Every workspace-managed check SHALL be classified as `hard`, `advisory`, or `manual` before it is added to CI or release checklists.

#### Scenario: New security check is proposed
- **WHEN** a maintainer adds secret scanning, dependency audit, dependency hygiene, or security linting
- **THEN** the check has an owner, command, scope, expected output, and promotion criterion before becoming a hard gate

#### Scenario: Advisory check fails
- **WHEN** an advisory check finds issues
- **THEN** the release report records the findings without blocking unrelated A 股 migration work unless the issue is credential leakage or another explicitly blocking risk

### Requirement: Secret scanning protects provider and broker credentials
The workspace SHALL include a secret-scanning path for superproject docs/scripts and each submodule before publishing public artifacts or enabling broker-related workflows.

#### Scenario: Public demo is exported
- **WHEN** a clean-room demo staging tree is created
- **THEN** the scan rejects credentials, `.env*` files, provider caches, local absolute paths, and private outputs before publication

#### Scenario: Broker workflow is changed
- **WHEN** execution code, broker docs, or credential-loading logic changes
- **THEN** the relevant repository runs a secret scan or documents why the changed files are outside credential scope

### Requirement: Coverage and dependency checks use ratchets
Coverage, dependency audit, and dependency hygiene checks SHALL use repository-specific baselines or allowlists rather than immediate global pass/fail thresholds.

#### Scenario: Coverage policy is added
- **WHEN** a coverage ratchet is introduced
- **THEN** it targets contract, target-export, risk, data-manifest, or execution-state modules before broad research scripts

#### Scenario: Dependency audit has optional extras
- **WHEN** dependency audit or unused-dependency checks inspect a repository with optional provider or broker extras
- **THEN** optional dependencies and intentionally dynamic imports are documented before findings become hard failures
