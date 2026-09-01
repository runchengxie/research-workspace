# Workspace Architecture-as-Code Design

## Goal

Add one machine-readable workspace component registry and one scanner that projects the existing authoritative dependency, artifact, and version sources into inspectable architecture graphs. The scanner must detect structural drift without redefining research algorithms, artifact schemas, or submodule-local dependency pins.

## Context

The workspace already has strong architecture governance, but the relevant facts live in several places:

- `scripts/import_boundary_rules.yml` owns forbidden Python import directions.
- `docs/artifact-contracts.yml` owns cross-repository artifact producer/consumer contracts.
- Git submodule gitlinks own the verified workspace source composition.
- each subrepository `pyproject.toml` may pin different Git revisions for standalone reproducibility.

Those sources are useful independently, but they do not currently produce one combined view of the architecture. This makes it easy to miss artifact-only dependencies, version-resolution divergence, or component coverage gaps.

## Design

### Component registry

Add `docs/architecture-model.yml` as the small component identity registry. It defines only facts that are not already owned elsewhere:

- component identifier;
- repository path;
- architectural plane/role;
- Python source roots and package roots;
- whether the component participates in runtime cycle checks.

The registry deliberately does **not** duplicate forbidden import rules or artifact field schemas. The existing import-boundary and artifact-contract manifests remain authoritative for those concerns.

### Scanner

Add `scripts/workspace_architecture.py` with four projections:

1. **Import graph**: parse Python source with the standard-library AST and resolve first-party package roots to workspace components. Edges are component-to-component imports with source evidence.
2. **Call graph**: conservatively record direct calls through imported first-party symbols or module aliases. Dynamic dispatch and runtime reflection are intentionally omitted and the report labels this graph as conservative.
3. **Artifact graph**: read `docs/artifact-contracts.yml` and project producer/consumer relationships through artifact nodes.
4. **Version graph**: read workspace gitlink revisions with `git ls-tree HEAD` and compare them with repository-local `[tool.uv.sources]` Git `rev` pins. Differences are reported as `standalone_pin_differences`, not hard failures, because repository-local pins intentionally support standalone environments.

The scanner also validates registry coverage, unknown artifact producers/consumers, duplicate package roots, and runtime import cycles.

### Output

`python scripts/workspace_architecture.py --out-dir <dir>` writes:

- `import_graph.json`
- `call_graph.json`
- `artifact_graph.json`
- `version_graph.json`
- `report.md`

`python scripts/workspace_architecture.py --check` performs validation and exits non-zero only for structural architecture issues. Standalone-vs-workspace revision differences remain warnings until the workspace defines an explicit unified-resolution policy.

### Quality integration

The existing `architecture` quality profile will run the scanner in `--check` mode after the current import and ownership boundary checks. This makes the new view additive rather than replacing proven governance in the same PR.

## Error handling

- Missing optional submodule source roots are reported as warnings so the scanner remains useful in partial source snapshots; existing workspace doctor/submodule checks continue to own submodule initialization enforcement.
- Invalid registry shape, duplicate Python package ownership, unknown artifact component references, and runtime component import cycles are errors.
- Missing Git metadata disables gitlink comparison with a warning rather than crashing, so source archives remain readable.
- TOML parse errors in a present component `pyproject.toml` are errors because they make version analysis unreliable.

## Testing

Tests use temporary synthetic workspaces so they do not depend on current submodule implementation details. They cover:

- component-level import edge discovery;
- conservative direct-call edge discovery;
- artifact producer/consumer projection;
- runtime cycle detection;
- standalone package pin differences remaining warnings;
- quality-profile inclusion of the architecture scanner.

## Non-goals

- No full Python runtime call graph. Reflection, dependency injection, monkeypatching, subprocess calls, and generated imports cannot be made complete with a lightweight static scanner.
- No automatic rewriting of subrepository `uv.lock` or Git pins.
- No replacement of `import_boundary_rules.yml` or `artifact-contracts.yml` in this change.
- No new network service or architecture database.
