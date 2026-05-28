## ADDED Requirements

### Requirement: Static check coverage reporting
The system SHALL report Ruff and Pyright source coverage using the repository's configured include and exclude settings. The report MUST include checked files, excluded files, checked lines, excluded lines, total lines, and checked-line percentage for each tool.

#### Scenario: Developer inspects configured coverage
- **WHEN** a developer runs the static quality coverage report
- **THEN** the report shows Ruff and Pyright coverage counts derived from `pyproject.toml`
- **AND** the report distinguishes checked source lines from excluded source lines

#### Scenario: Coverage report is consumed by automation
- **WHEN** CI or a test invokes the coverage report in machine-readable mode
- **THEN** the system returns structured output with stable keys for Ruff and Pyright metrics

### Requirement: Static quality baseline enforcement
The system SHALL maintain a checked-in static quality baseline for Ruff and Pyright coverage. The system MUST fail the governance check when checked-line coverage decreases, excluded-line coverage increases, or configured source excludes expand without an explicit baseline update.

#### Scenario: Exclude list grows without acknowledgement
- **WHEN** a change adds a new source path to Ruff or Pyright excludes without updating the baseline
- **THEN** the governance check fails and identifies the new excluded path

#### Scenario: Coverage improves
- **WHEN** a change removes an exclude or admits additional source lines into Ruff or Pyright coverage
- **THEN** the governance check passes and reports the coverage improvement

### Requirement: Non-blocking debt scans
The system SHALL provide non-blocking debt scans for full-source Ruff diagnostics, complexity diagnostics, and Pyright basic diagnostics outside the configured blocking gate. These scans MUST be runnable locally and in CI without changing the blocking status of existing tests unless debt increases beyond an accepted baseline.

#### Scenario: Developer runs debt scan before refactoring
- **WHEN** a developer runs the debt scan for all source modules
- **THEN** the system reports diagnostic counts by tool and rule category
- **AND** the command exits successfully unless regression enforcement is explicitly requested

#### Scenario: CI detects debt regression
- **WHEN** the debt scan is run with baseline enforcement enabled
- **THEN** the system fails only if measured debt exceeds the checked-in baseline or an allowed threshold

### Requirement: Tiered static coverage admission
The system SHALL define staged admission tiers for excluded modules. Each tier MUST identify the modules to admit, the target tool coverage, and the accepted handling for remaining diagnostics.

#### Scenario: Low-risk boundary module enters Ruff coverage
- **WHEN** a low-risk module such as a path, contract, registry, manifest, or current-assets module is removed from Ruff excludes
- **THEN** the module is checked by the normal Ruff gate
- **AND** any remaining exception is documented as a narrow per-file or inline ignore with a reason

#### Scenario: Pandas-heavy module remains excluded
- **WHEN** a pandas-heavy HK asset, HK depth, or release workflow module cannot yet enter Pyright coverage
- **THEN** the module remains tracked in the staged admission plan with a reason and next remediation target
