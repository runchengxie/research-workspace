## Context

The workspace is a multi-repo integration layer for data platform, strategy research, and trading execution. Current active work is centered on A-share data/research/execution handoff, while 中国香港市场 assets and research outputs are preserved through cold-storage restore evidence, legacy compatibility entrypoints, and a clean-room public demo export.

The existing public demo is intentionally small. `scripts/export_hk_public_demo.py` copies an allowlisted template tree, runs an offline synthetic workflow, runs `unittest`, scans the staged tree for private files and local paths, and writes `export-manifest.json`. This is a good public safety base, but it does not yet provide a full migration manifest for HK legacy surfaces, independent Ruff/Pyright quality gates, or a repo-candidate structure that can absorb public-safe demo logic without becoming an unclassified legacy dump.

The change should treat `demo/hk-public-demo-template-v1` as a staging area for a future independent paused-maintenance public repository. It should not treat `demo/` as a general destination for all HK-specific code.

## Goals / Non-Goals

**Goals:**

- Define a machine-readable split manifest for 中国香港市场 surfaces across the superproject and submodules.
- Make the public demo staging tree independently understandable and testable with synthetic data only.
- Add quality gates for the staging tree: offline smoke, unit tests, Ruff, Pyright, allowlist validation, dependency boundary checks, and private-data scans.
- Provide a safe path to move or reimplement public-safe HK demo logic while preserving cold-storage restore and consumer-audit gates.
- Document when main-workspace compatibility entrypoints can be deleted after split evidence is available.

**Non-Goals:**

- Do not export real market data, provider cache, broker adapters, private outputs, credentials, execution audit logs, or local machine paths.
- Do not rewrite the production data platform, research pipeline, or execution engine as part of this proposal.
- Do not remove restore-sensitive HK compatibility code in the first implementation pass.
- Do not make the public demo a workspace submodule, package dependency, required CI target, or release gate.
- Do not preserve private Git history in the public repository candidate.

## Decisions

1. Use a split manifest as the source of truth.

   Add `docs/hk-public-split-manifest.yml` with one record per HK-related surface. Each record includes owner repo, path or pattern, action, public safety classification, required redactions, restore dependency, consumer-audit status, replacement path, and removal condition.

   Alternative considered: continue using prose-only inventory. Prose is useful for maintainers, but it cannot reliably drive checks or expose missing classifications.

2. Keep the public demo active code small and clean.

   Public-safe logic should be reimplemented or extracted into cohesive demo modules such as `assets`, `research`, `allocation`, and `data`, with synthetic fixtures and stable `targets.json` output. Historical configs and notes belong under demo `archive/` only when they are public-safe and clearly marked as provenance.

   Alternative considered: copy existing HK implementation files directly into demo. That would preserve too much production coupling and would likely carry old complexity, provider assumptions, and maintenance debt into the public repo candidate.

3. Separate active demo code from archived provenance.

   The demo staging tree should have strict checks for `src/`, `tests/`, `scripts/`, and active docs. `archive/` may contain public-safe historical context, but it must be excluded from strict style/type gates or checked with archive-specific rules.

   Alternative considered: enforce identical checks everywhere. That wastes effort on frozen material and makes archival evidence harder to preserve.

4. Strengthen the export contract instead of relying only on manual review.

   The exporter should validate the split manifest, the allowlist, generated samples, scan result, offline smoke result, and demo quality commands. The exported `export-manifest.json` should record all checks that passed and the manifest version used.

   Alternative considered: leave publication review as manual checklist only. Manual review is still required before push, but automated evidence reduces repeated mistakes.

5. Gate deletion of main-workspace HK surfaces behind evidence.

   Compatibility entrypoints such as legacy HK data commands or `alloc-hk` should remain until their manifest records show restore evidence, downstream consumer audit, public split evidence when applicable, replacement docs, and rollback notes. Deletion should happen in follow-up changes with explicit test coverage.

   Alternative considered: delete after copying demo files. That is unsafe because public demo staging does not replace restore-sensitive production or historical reproducibility responsibilities.

6. Prefer clean-room public repository creation after staging is complete.

   The future public repo should be created from the staged tree by squashed import or explicit maintainer action, not by pushing private Git history. The workspace exporter should never create the remote repository or push.

   Alternative considered: use git history filtering from the demo subdirectory. That can preserve history, but it increases the risk of leaking private paths, commit messages, or removed artifacts.

## Risks / Trade-offs

- Manifest scope creep -> Keep required fields small, and classify unknown surfaces as `needs_audit` rather than blocking the first manifest on perfect certainty.
- Public demo becomes a second production codebase -> Mark the repository as frozen/paused-maintenance, keep fixtures synthetic, and reject provider or broker dependencies in checks.
- Reimplementation diverges from historical behavior -> Preserve only the public demo contract and examples; keep real reproducibility evidence in cold-storage restore docs.
- Over-strict scanners reject harmless text -> Keep scan rules explainable and allow narrow, documented exceptions only in non-exported workspace docs.
- Deleting main-workspace code too early breaks restore or old consumers -> Require manifest gates and follow-up deletion changes after focused tests pass.
- Adding Ruff/Pyright increases setup cost -> Use no runtime dependencies and keep quality commands focused on active demo code, with archive paths excluded.

## Migration Plan

1. Create `docs/hk-public-split-manifest.yml` and seed it from `docs/hk-legacy-surface-inventory.md`, current demo export docs, and repo-local HK surface searches.
2. Add tests that validate manifest schema, every listed path/pattern, allowed action values, public-safety decisions, and documentation links.
3. Expand `demo/hk-public-demo-template-v1` into an independent repo candidate: package layout, docs index, archive placeholder, quality config, and CI commands.
4. Refactor or reimplement the current demo pipeline into cohesive modules while preserving generated `samples/summary.json` and `samples/targets.json`.
5. Update `scripts/export_hk_public_demo.py` so export evidence records split manifest version, quality checks, allowlist validation, and dependency-boundary scan results.
6. Update top-level docs and archive docs to describe the split staging model, the future independent repository boundary, and non-goals.
7. Run focused top-level tests for demo export, manifest validation, docs links, root quality, and workspace doctor.
8. After the staged public repo candidate passes, open follow-up changes to delete or archive main-workspace HK compatibility surfaces whose manifest gates are complete.

Rollback is straightforward for the first implementation pass: remove the new manifest, revert demo staging additions, and restore the existing export config and docs. No runtime production API changes are intended in this phase.

## Open Questions

- Should the future public repository name stay `hk-cross-sectional-strategy-demo`, or should it be renamed to emphasize frozen archive status?
- Should public-safe historical experiment configs be included in demo `archive/`, or should they stay only in cold-storage/release evidence?
- Should Ruff/Pyright be hard CI gates immediately for the demo candidate, or introduced as local checks first and then made required after the first cleanup pass?
