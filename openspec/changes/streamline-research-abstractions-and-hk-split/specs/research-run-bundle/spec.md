## ADDED Requirements

### Requirement: Research run object resolves canonical artifacts
`cross-sectional-trees` SHALL provide a lightweight `ResearchWorkspace` / `ResearchRun` object model that resolves a run directory into typed accessors for `summary.json`, `config.used.yml`, `inputs.lock.json`, datasets, canonical signals, positions, exported targets, and lineage sidecars without callers hard-coding run-relative paths.

#### Scenario: Existing run is loaded
- **WHEN** a caller constructs a research run from `artifacts/runs/<run>` containing `summary.json` and `config.used.yml`
- **THEN** the run object returns typed path/status metadata for known artifacts and preserves the resolved absolute run directory

#### Scenario: Optional artifact is missing
- **WHEN** a caller asks for an optional artifact that is not present in the run directory
- **THEN** the run object reports a missing optional artifact status without inventing fallback paths or raising an unrelated file error

### Requirement: Run validation reports actionable completeness
The run object MUST expose a validation summary that separates required reproducibility inputs from optional research artifacts and execution handoff artifacts.

#### Scenario: Reproducibility files are incomplete
- **WHEN** `summary.json`, `config.used.yml`, or `inputs.lock.json` is absent from a completed run
- **THEN** validation marks the run as incomplete for reproducibility and identifies the missing file names

#### Scenario: Execution handoff is absent
- **WHEN** a run has model, signal, and position artifacts but no `targets.json`
- **THEN** validation marks execution handoff as absent while keeping the research run readable

### Requirement: Run export uses existing target contract
The run object SHALL delegate execution target export to the existing `cstree export-targets` contract and MUST preserve `targets.json` plus `targets.json.lineage.json` semantics.

#### Scenario: Targets are exported from current positions
- **WHEN** a caller exports targets through the run object using a valid long-only current positions artifact
- **THEN** the generated target file conforms to `quant-execution-engine.targets/v2` and the lineage sidecar records the selected positions file and upstream run metadata

### Requirement: Method map documents the six-stage flow
The workspace documentation SHALL include a concise six-stage map: Data Contract, Research Dataset, Model, Signal, Portfolio, and Execution Handoff.

#### Scenario: New maintainer follows the map
- **WHEN** a maintainer reads the top-level workflow documentation
- **THEN** they can identify which repository owns each stage and which canonical file or object is the handoff between stages
