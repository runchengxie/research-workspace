## ADDED Requirements

### Requirement: Deprecation Governance
The workspace SHALL maintain a versioned deprecation register for deprecated compatibility surfaces that remain in active repositories.

Each deprecation record MUST include owner repo, deprecated entrypoint, replacement, current consumer status, removal condition, target milestone or release window, rollback path, required focused tests, and whether restore evidence is required. Records for restore-sensitive HK surfaces MUST NOT be marked removal-ready until restore evidence, consumer audit, replacement docs, rollback notes, and focused tests are complete.

#### Scenario: Deprecated HK entrypoint is reviewed
- **WHEN** a maintainer reviews `hkdata`, `rqdata-hk-*`, `src/hk_data_platform`, or `cstree alloc-hk`
- **THEN** the deprecation register identifies its owner, replacement path, consumer status, target milestone, removal condition, rollback path, and required tests

#### Scenario: Removal-ready record lacks evidence
- **WHEN** a deprecation record is marked removal-ready without completed consumer audit, replacement docs, rollback notes, or focused tests
- **THEN** the deprecation governance check fails with the affected entrypoint

### Requirement: Script Lifecycle Metadata
The workspace SHALL classify non-trivial scripts and project tools by lifecycle and safety.

Each tracked script MUST record owner, purpose, lifecycle, safe-to-run-local status, write targets, external dependencies, and removal condition. Valid lifecycle values MUST include `dev`, `ci`, `release`, `migration`, and `archive`. New scripts outside tests MUST either appear in the lifecycle manifest or include equivalent metadata in a checked header.

#### Scenario: New operational script is added
- **WHEN** a new script is added under `scripts/`, `scripts/internal/`, `scripts/dev/`, or `project_tools/`
- **THEN** script lifecycle checks fail until owner, purpose, lifecycle, safety, write targets, dependencies, and removal condition are documented

#### Scenario: Migration script reaches removal condition
- **WHEN** a migration script's removal condition is satisfied
- **THEN** the lifecycle manifest identifies whether it should move to archive, remain release-only, or be deleted in a follow-up change

### Requirement: Maintainability Baseline
The workspace SHALL maintain reproducible maintainability baseline reports for the superproject and each submodule.

The baseline MUST report Python file count, source line count, HK-related file count, files over configured line thresholds, functions over configured length thresholds, cyclomatic complexity hotspots, Ruff ignore debt, Pyright include/exclude coverage, and one-off script inventory. Baseline thresholds MUST be documented and tests MUST detect missing baseline sections.

#### Scenario: Baseline is refreshed
- **WHEN** maintainability baseline commands run
- **THEN** each repo report includes large-file, long-function, complexity, quality-coverage, and script-inventory sections with current thresholds

#### Scenario: New hotspot appears
- **WHEN** a new file or function exceeds configured maintainability thresholds
- **THEN** the baseline check reports the path and requires either a task owner, an accepted exception, or a refactor plan

### Requirement: Quality Coverage Expansion
The workspace SHALL expand Ruff and Pyright coverage using staged, measurable gates.

Each submodule MUST define current quality coverage, next include targets, allowed excludes, and promotion criteria from advisory to hard gate. Quality excludes MUST be registered with owner and next action. Execution-critical modules in `quant-execution-engine` and contract-critical modules in data/research repos MUST have stricter staged targets than archived provenance code.

#### Scenario: Quality config excludes a broad source tree
- **WHEN** Ruff or Pyright excludes an entire active source tree such as HK assets, release tools, or liveops code
- **THEN** the quality governance check requires a registered exception with owner, reason, next include target, and review milestone

#### Scenario: Low-risk module is promoted into coverage
- **WHEN** a low-risk model, schema, public API, contract, or pure validation module is added to Pyright or Ruff coverage
- **THEN** focused tests and the quality baseline record the new coverage before broader modules are attempted

### Requirement: Complexity Refactor Roadmap
The workspace SHALL maintain a refactor roadmap for oversized modules and long functions before performing broad rewrites.

The roadmap MUST identify priority files, proposed module splits, risk level, first safe extraction type, tests to run, and non-goals. The first safe extraction types MUST include schema/model extraction, path resolution, pure validation, rendering/reporting, CLI parser extraction, and workflow orchestration separation.

#### Scenario: Oversized HK data module is prioritized
- **WHEN** `asset_health.py`, `audit_assets.py`, `hk_asset_workflow.py`, or `hk_depth/downloader.py` appears in the roadmap
- **THEN** the roadmap states the first safe extraction, target module layout, and focused tests before implementation starts

#### Scenario: Large research or execution module is prioritized
- **WHEN** `pipeline/eval.py`, `summarize_runs.py`, `exposure.py`, `commands/tune.py`, `cli.py`, or `broker/longport.py` appears in the roadmap
- **THEN** the roadmap states the owner repo, risk level, split plan, and focused tests needed for the first refactor pass

### Requirement: Team Collaboration Guardrails
The workspace SHALL provide team-level contribution guardrails without copying submodule implementation policy into top-level docs.

The superproject MUST include CODEOWNERS, CONTRIBUTING, an architecture entrypoint, and a PR checklist. The PR checklist MUST cover deprecated surfaces, one-off scripts, new quality excludes, `targets.json` contract impact, provider/broker credentials, migration notes, and submodule-focused tests.

#### Scenario: Contributor opens the workspace
- **WHEN** a maintainer opens the top-level collaboration docs
- **THEN** they can identify repo responsibilities, owner boundaries, PR expectations, and where submodule-specific rules live

#### Scenario: PR introduces maintainability debt
- **WHEN** a PR adds a deprecated surface, one-off script, broad quality exclude, provider credential dependency, or `targets.json` contract change
- **THEN** the PR checklist requires an owner, rationale, migration note, and focused verification command

### Requirement: Boundary-Ordered Verification
Maintainability governance changes SHALL be verified at the owning repository boundary before broad workspace checks.

Implementation summaries MUST report status in the order data platform -> strategy research -> trading execution -> top-level docs/doctor -> remaining limitations. If a submodule is not edited, the summary MUST state that no focused tests were required for that repo.

#### Scenario: Governance touches multiple submodules
- **WHEN** quality configs, scripts, docs, or tests are changed in more than one submodule
- **THEN** focused checks run in each touched submodule before final top-level doctor and docs checks

#### Scenario: Check cannot run
- **WHEN** a check cannot run because of credentials, optional dependencies, network limits, missing shared data roots, or incomplete submodule state
- **THEN** the final summary states the concrete command, reason, and prerequisite needed to run it later
