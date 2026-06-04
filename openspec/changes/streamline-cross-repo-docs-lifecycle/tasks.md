## 1. Inventory And Lifecycle Rules

- [x] 1.1 Inventory active and archive Markdown entry points in `research-workspace/docs` and `cross-sectional-trees/docs`, including current inbound links from README files and docs tests.
- [x] 1.2 Define the lifecycle status block format for active, reference, archived, and superseded docs.
- [x] 1.3 Add lifecycle guidance to the relevant docs index or governance page without copying submodule-specific rules into the superproject.
- [x] 1.4 Identify compatibility stubs required before moving high-traffic documents.

## 2. Superproject Documentation Cleanup

- [x] 2.1 Update `docs/archive/hk/README.md` to be the single Hong Kong market archive routing entry for frozen data assets, archived research outputs, public demo split state, private archive state, restore evidence, and removal gates.
- [x] 2.2 Reduce `docs/hk-private-archive.md`, `docs/hk-public-demo-export.md`, and `docs/hk-legacy-surface-inventory.md` to manifest-backed references, archive records, or compatibility pointers as appropriate.
- [x] 2.3 Fold duplicated A-share readiness guidance from `docs/a-share-production-readiness.md` into `docs/data-transition-playbook.md`, or replace it with a short roadmap pointer.
- [x] 2.4 Move one-time Hong Kong market release notes and session handoffs under archive record paths, preserving links from `docs/archive/hk/README.md`.
- [x] 2.5 Update top-level `README.md`, `docs/README.md`, governance docs, and manifests so active links point to current source-of-truth pages.

## 3. Cross-Sectional Trees Documentation Cleanup

- [x] 3.1 Create an archive summary/index for Hong Kong market historical research notes with current conclusions, authority precedence, and reproduction pointers.
- [x] 3.2 Move `cross-sectional-trees/docs/research/notes/*.md` to an archive path or replace the active path with compatibility stubs that point to the archive summary.
- [x] 3.3 Update `cross-sectional-trees/docs/research/README.md` so active research guidance appears before archived Hong Kong market provenance.
- [x] 3.4 Compress `docs/playbooks/hk-selected.md` into a legacy restore recipe or compatibility entry that links to the archive summary for detailed historical evidence.
- [x] 3.5 Consolidate overlapping Hong Kong market data/RQData pages such as `hk-data-assets.md`, `hk-intraday-assets.md`, `hk-rqdata-status.md`, and `rqdata/hk-health-checks.md` into one boundary entry or archive routing page.
- [x] 3.6 Merge or clearly separate `docs/concepts/model-landscape.md` and `docs/concepts/model-selection.md` so they no longer duplicate modeling guidance.
- [x] 3.7 Update `cross-sectional-trees/docs/README.md`, concept/playbook indexes, inline links, and any archive manifests for moved or superseded paths.

## 4. Tests And Verification

- [x] 4.1 Update top-level docs link and manifest tests for any moved or consolidated `research-workspace` docs.
- [x] 4.2 Update `cross-sectional-trees/tests/test_docs_contracts.py` so it asserts lifecycle routing and replacement links instead of obsolete active paths.
- [x] 4.3 Run `uv run --with pytest python -m pytest tests/test_workspace_doctor.py -q` from `research-workspace`.
- [x] 4.4 Run focused top-level docs tests such as `uv run --with pytest python -m pytest tests/test_docs_links.py tests/test_hk_public_split_manifest.py -q`.
- [x] 4.5 Run `uv run python -m pytest tests/test_docs_contracts.py -q` from `cross-sectional-trees`.
- [x] 4.6 Check `git status --short` in both the submodule and superproject and record any submodule gitlink change caused by the docs cleanup.

## 5. Rollout Review

- [x] 5.1 Review all remaining active docs for clear `source_of_truth` and `superseded_by` values where applicable.
- [x] 5.2 Confirm no runtime code, provider API, asset key, broker integration, or canonical contract name changed.
- [x] 5.3 Summarize completed work in data platform -> strategy research -> trading execution -> top-level docs/doctor -> remaining limitations order.
