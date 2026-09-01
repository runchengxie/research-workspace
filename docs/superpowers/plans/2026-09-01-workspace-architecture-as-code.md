# Workspace Architecture-as-Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and validate import, conservative call, artifact, and version architecture graphs from the workspace's existing authoritative sources.

**Architecture:** A small component registry supplies stable component/package identity. A standard-library AST/TOML scanner projects source imports/calls, the existing artifact manifest supplies file handoff edges, and Git gitlinks plus local `uv.sources` supply version-resolution evidence. Existing boundary manifests remain authoritative and the scanner is added to the current architecture quality profile.

**Tech Stack:** Python 3.12 standard library (`ast`, `argparse`, `json`, `subprocess`, `tomllib`, `pathlib`), PyYAML already declared by the root project, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-workspace-architecture-as-code-design.md`

## Global Constraints

- Do not duplicate artifact field schemas from `docs/artifact-contracts.yml`.
- Do not duplicate forbidden import rules from `scripts/import_boundary_rules.yml`.
- Git submodule gitlinks remain the authoritative workspace source composition.
- Repository-local Git pins remain valid for standalone reproducibility; differences are warnings, not failures.
- Static call discovery is conservative and must not claim completeness.

---

### Task 1: Component registry and graph scanner tests

**Files:**
- Create: `docs/architecture-model.yml`
- Create: `tests/test_workspace_architecture.py`

**Interfaces:**
- Consumes: existing workspace component names and package roots.
- Produces: test expectations for `load_model`, `build_import_graph`, `build_call_graph`, `build_artifact_graph`, `build_version_graph`, and `build_report` in `scripts/workspace_architecture.py`.

- [ ] **Step 1: Add the component registry**

Define the workspace components, their repo paths, planes, Python package roots, Python source roots, and runtime-cycle participation. Keep artifact and forbidden-import policy out of this file.

- [ ] **Step 2: Write failing scanner tests**

Use a temporary synthetic workspace with `producer`, `consumer`, and `research-contracts` components. Assert that:

```python
assert {edge["source"], edge["target"]} == {"producer", "consumer"}
```

for an import, that an imported `consumer.api.run()` call produces a conservative call edge, that an artifact manifest produces producer -> artifact -> consumer edges, and that a repository-local `uv.sources` revision different from the gitlink is a warning.

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
pytest tests/test_workspace_architecture.py -q
```

Expected: collection/import failure because `scripts/workspace_architecture.py` does not exist yet.

- [ ] **Step 4: Commit the failing tests and registry**

```bash
git add docs/architecture-model.yml tests/test_workspace_architecture.py
git commit -m "test: specify workspace architecture projections"
```

### Task 2: Implement architecture projections

**Files:**
- Create: `scripts/workspace_architecture.py`

**Interfaces:**
- Consumes: `docs/architecture-model.yml`, `docs/artifact-contracts.yml`, Python source roots, component `pyproject.toml`, and Git gitlinks.
- Produces:
  - `load_model(root: Path, model_path: Path | None = None) -> ArchitectureModel`
  - `build_import_graph(root: Path, model: ArchitectureModel) -> dict[str, object]`
  - `build_call_graph(root: Path, model: ArchitectureModel) -> dict[str, object]`
  - `build_artifact_graph(root: Path, model: ArchitectureModel, manifest_path: Path | None = None) -> dict[str, object]`
  - `build_version_graph(root: Path, model: ArchitectureModel) -> dict[str, object]`
  - `build_report(root: Path, model_path: Path | None = None) -> dict[str, object]`

- [ ] **Step 1: Implement model loading and validation**

Parse YAML into frozen dataclasses. Reject duplicate component ids and duplicate Python package roots.

- [ ] **Step 2: Implement AST import and conservative call projection**

Resolve `import package`, `import package.module as alias`, and `from package.module import member` against known first-party package roots. Record file/line evidence. Calls are limited to imported names and attributes rooted in imported aliases.

- [ ] **Step 3: Implement artifact projection**

Load the existing JSON-compatible `artifact-contracts.yml`. Validate owner/producer/consumer component references when they refer to pinned workspace repositories, while retaining explicitly external producers/consumers as external nodes.

- [ ] **Step 4: Implement version projection**

Use `git ls-tree HEAD` when Git metadata is present to collect gitlinks. Parse `[tool.uv.sources]` from component `pyproject.toml` with `tomllib` and report per-consumer standalone pins. Differences from workspace gitlinks are warning records.

- [ ] **Step 5: Implement cycle detection, markdown rendering, CLI, and JSON outputs**

`--check` exits 1 only when the report has errors. `--out-dir` writes four graph JSON files plus `report.md`.

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
pytest tests/test_workspace_architecture.py -q
```

Expected: PASS.

- [ ] **Step 7: Run lint on the new files**

```bash
ruff check scripts/workspace_architecture.py tests/test_workspace_architecture.py
ruff format --check scripts/workspace_architecture.py tests/test_workspace_architecture.py
```

Expected: PASS.

- [ ] **Step 8: Commit implementation**

```bash
git add scripts/workspace_architecture.py
git commit -m "feat: add workspace architecture graph scanner"
```

### Task 3: Quality-gate integration and operator docs

**Files:**
- Modify: `scripts/run_quality_checks.py`
- Create: `docs/architecture-as-code.md`
- Modify: `ARCHITECTURE.md`
- Test: `tests/test_root_quality.py`

**Interfaces:**
- Consumes: `scripts/workspace_architecture.py --check`.
- Produces: architecture profile command `workspace-architecture` and human usage documentation.

- [ ] **Step 1: Write a failing quality-profile test**

Assert `plan_commands("architecture")` includes a command named `workspace-architecture` invoking `scripts/workspace_architecture.py --check`.

- [ ] **Step 2: Run focused test and verify RED**

```bash
pytest tests/test_root_quality.py -q
```

Expected: FAIL because the command is not registered.

- [ ] **Step 3: Add the architecture command to the existing profile**

Append the scanner after the import and ownership boundary checks.

- [ ] **Step 4: Add operator documentation**

Document the four graphs, the distinction between hard errors and standalone pin warnings, and example `--out-dir` usage. Link it from `ARCHITECTURE.md`.

- [ ] **Step 5: Run focused tests and architecture check**

```bash
pytest tests/test_root_quality.py tests/test_workspace_architecture.py -q
python scripts/workspace_architecture.py --check
```

Expected: tests PASS; scanner exits 0 and may report standalone pin warnings.

- [ ] **Step 6: Run root architecture profile dry-run**

```bash
python scripts/run_quality_checks.py --profile architecture --dry-run
```

Expected: output includes `workspace-import-boundaries`, `workspace-ownership-boundaries`, and `workspace-architecture`.

- [ ] **Step 7: Commit integration**

```bash
git add scripts/run_quality_checks.py tests/test_root_quality.py docs/architecture-as-code.md ARCHITECTURE.md
git commit -m "chore: gate workspace architecture projections"
```
