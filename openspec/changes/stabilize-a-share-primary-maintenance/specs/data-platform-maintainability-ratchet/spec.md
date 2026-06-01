## ADDED Requirements

### Requirement: Maintainability regression must be repaired without increasing the baseline
The data platform MUST pass `scripts/dev/maintainability_metrics.py --check-baseline` against the
existing committed baseline. The implementation MUST NOT increase the baseline merely to accept
new long functions or new functions with ten or more arguments.

#### Scenario: Existing baseline passes after refactor
- **WHEN** the maintainability check runs after the refactor
- **THEN** `functions_over_100` and `functions_with_10_plus_args` are no greater than the committed baseline values
- **THEN** the command exits successfully without rewriting the baseline

### Requirement: A 股 refresh planning remains auditable after decomposition
The data platform SHALL preserve the existing A 股 current refresh plan schema, stage ordering,
validation-before-publication policy, and no-write planning behavior while decomposing the planner
into narrower helpers.

#### Scenario: Refresh plan is generated
- **WHEN** an operator builds an A 股 current refresh plan with all required raw datasets
- **THEN** the plan contains raw backfill, daily clean build and validation, universe build and validation, and publish-current stages in order
- **THEN** latest aliases and the current contract are updated only by the publication stage

### Requirement: Fundamentals download options are represented by a bounded internal interface
The data platform SHALL replace broad fundamentals downloader argument lists with a bounded
options or context interface and SHALL preserve restart state, retry behavior, failure reports,
raw manifest fields, and entitlement-aware behavior.

#### Scenario: Restartable fundamentals download is resumed
- **WHEN** a raw fundamentals download resumes with completed and failed query units
- **THEN** non-stale completed units are reused
- **THEN** failed or stale units are retried according to the configured policy
- **THEN** state, failure report, and manifest outputs preserve their existing schemas

### Requirement: Large test setup is factored without reducing behavioral assertions
The data platform SHALL extract reusable fixture or helper setup from oversized tests while
retaining assertions for copied contracts, resolved assets, manifests, and overlap pruning.

#### Scenario: Backup snapshot tests run after fixture extraction
- **WHEN** focused backup tests run
- **THEN** they still prove that a 港股 current-contract snapshot copies the contract and resolved assets
- **THEN** they still prove that overlapping universe selections are pruned correctly
