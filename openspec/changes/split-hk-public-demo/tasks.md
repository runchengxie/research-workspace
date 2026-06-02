## 1. Baseline And Split Manifest

- [x] 1.1 Search HK-related surfaces across the superproject, `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine`, and record the reviewed commands.
- [x] 1.2 Create `docs/hk-public-split-manifest.yml` with schema version, action vocabulary, public-safety vocabulary, and one record per known HK surface.
- [x] 1.3 Classify each manifest record as `keep_in_main`, `move_to_public_demo`, `archive_in_public_demo`, `delete_after_split`, or `private_do_not_export`.
- [x] 1.4 Add restore dependency, consumer-audit status, replacement path, required redactions, and removal condition fields for every manifest record.
- [x] 1.5 Cross-check the manifest against `docs/hk-legacy-surface-inventory.md`, `docs/hk-public-demo-export.md`, and the demo allowlist.

## 2. Manifest And Boundary Validation

- [x] 2.1 Add a top-level test module that validates manifest YAML structure, required fields, allowed enum values, and duplicate record IDs.
- [x] 2.2 Validate that each manifest path or glob resolves to at least one repo-local file unless explicitly marked as external evidence or future placeholder.
- [x] 2.3 Add a demo dependency-boundary check that rejects imports from `market_data_platform`, `hk_data_platform`, `cstree`, and `quant_execution_engine` in active demo code.
- [x] 2.4 Add scan coverage for broker/provider/runtime markers such as `rqdata`, `tushare`, `longport`, `ibkr`, and provider cache terminology in the exported public tree.
- [x] 2.5 Add tests for manifest deletion gates so records cannot be marked deletion-ready without restore evidence, consumer audit, replacement docs, rollback notes, and focused-test evidence.

## 3. Public Demo Repo Candidate

- [x] 3.1 Expand `demo/hk-public-demo-template-v1/pyproject.toml` with Ruff and Pyright configuration for active demo code.
- [x] 3.2 Update the demo CI workflow to run the offline workflow, unit tests, Ruff, and Pyright in a clean public checkout.
- [x] 3.3 Refactor `src/hk_strategy_demo/pipeline.py` into cohesive modules for synthetic data loading, ranking/research summary, allocation, and `targets.json` export.
- [x] 3.4 Preserve the current CLI behavior of `scripts/run_demo.py` and generated `samples/summary.json` and `samples/targets.json`.
- [x] 3.5 Add focused unit tests for data loading, ranking tie-breaks, target weights, invalid `top_n`, and generated schema versions.
- [x] 3.6 Add a demo `docs/README.md` or equivalent index that distinguishes active workflow docs from archived provenance.
- [x] 3.7 Add a demo `archive/README.md` placeholder explaining that archived material is public-safe historical provenance and not an active workflow.

## 4. Exporter And Allowlist Hardening

- [x] 4.1 Update `demo/hk-public-demo-allowlist-v1.txt` to include any new active demo files, docs, archive placeholders, and quality configuration.
- [x] 4.2 Update `scripts/export_hk_public_demo.py` to load and validate the split manifest before exporting.
- [x] 4.3 Record split manifest schema version and relevant manifest record IDs in `export-manifest.json`.
- [x] 4.4 Run demo quality commands from the exporter and record their status in `export-manifest.json`.
- [x] 4.5 Ensure `--scan-only` applies the strengthened public-tree scan without requiring workspace submodules.
- [x] 4.6 Extend `tests/test_export_hk_public_demo.py` to cover quality evidence, manifest evidence, workspace-import rejection, provider/broker marker rejection, and allowlist drift.

## 5. Documentation And Cleanup Gates

- [x] 5.1 Update `docs/hk-public-demo-export.md` to describe the staging model, split manifest, quality gates, and publication review order.
- [x] 5.2 Update `docs/hk-legacy-surface-inventory.md` to link to the split manifest and explain that deletion still requires follow-up changes.
- [x] 5.3 Update `docs/archive/hk/README.md` so maintainers can find restore evidence, split manifest, export command, and post-split cleanup gates.
- [x] 5.4 Update root docs only where needed to keep active workflow direction as data platform -> strategy research -> trading execution, with the HK public demo as an external frozen reference.
- [x] 5.5 Add a deprecation or cleanup-gate section that lists compatibility entrypoints eligible for future removal only after manifest evidence passes.

## 6. Verification

- [x] 6.1 Run the demo template commands locally: offline workflow, unit tests, Ruff, and Pyright.
- [x] 6.2 Run top-level focused tests for demo export, manifest validation, docs links, root quality, and workspace doctor.
- [x] 6.3 Run data-platform focused tests only if this change edits data-platform files; otherwise record that no data-platform code changed.
- [x] 6.4 Run strategy-research focused tests only if this change edits `cross-sectional-trees`; otherwise record that no strategy-research code changed.
- [x] 6.5 Run execution-engine focused tests only if this change edits `quant-execution-engine`; otherwise record that no execution-engine code changed.
- [x] 6.6 Review `git status --short` in the superproject and any touched submodules, including submodule gitlink state.
- [x] 6.7 Summarize completion in the required order: data platform -> strategy research -> trading execution -> top-level docs/doctor -> remaining limitations.
