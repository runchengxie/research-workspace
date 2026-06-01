## ADDED Requirements

### Requirement: Pyright errors are fixed before hard-gate migration
The execution engine MUST reduce the current reproducible Pyright error count to zero before the
workspace delegates the execution-engine hard type profile to Pyright. Fixes MUST use explicit
normalization at optional SDK boundaries rather than broad global ignores.

#### Scenario: Optional SDK boundary is checked
- **WHEN** Pyright analyzes IBKR and LongPort dynamic-object normalization code
- **THEN** float, iterable, enum-value, and datetime conversions are narrowed before use
- **THEN** Pyright reports zero errors

### Requirement: Remaining Pyright warnings are explicitly classified
The execution engine MUST either fix each remaining Pyright warning or document why it is an
intentional delayed-export or optional-dependency visibility warning. New global warning
suppression MUST NOT be added solely to make migration appear clean.

#### Scenario: Pyright warning policy is reviewed
- **WHEN** the migration verification runs
- **THEN** each retained warning has a documented category and rationale
- **THEN** warning policy does not hide execution, risk, state, or targets-contract defects

### Requirement: Workspace delegated type profile migrates with a mypy bake period
After Pyright reports zero errors and focused behavior tests pass, the workspace SHALL map the
execution engine `type` profile to Pyright and SHALL retain mypy as `mypy_advisory` for a defined
transition period.

#### Scenario: Delegated hard type profile is executed
- **WHEN** the workspace runs the execution-engine `type` profile after migration
- **THEN** it invokes Pyright
- **THEN** a separately invokable `mypy_advisory` profile remains available during the transition period

### Requirement: Type-gate migration remains reversible
The workspace SHALL document how to restore mypy as the execution-engine hard type gate if the
Pyright bake period reveals unacceptable noise or a blocking compatibility issue.

#### Scenario: Migration rollback is needed
- **WHEN** maintainers decide that Pyright cannot remain the execution-engine hard gate
- **THEN** the delegated `type` profile can be restored to mypy without reverting valid SDK-boundary type fixes
