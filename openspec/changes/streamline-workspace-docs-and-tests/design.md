## Context

The current checkout has all three submodules initialized and clean. `scripts/workspace_doctor.py` reports no errors and one expected warning when `DATA_PLATFORM_ROOT` is unset, while `scripts/print_version_matrix.py` prints the current commits as `3039a39` for the workspace, `ca765df` for `market-data-platform`, `6773a1f` for `cross-sectional-trees`, and `3c9903f` for `quant-execution-engine`.

Focused checks passed in the initialized local checkout:

- Top-level docs, root quality, and doctor tests: 11 passed.
- `cross-sectional-trees` documentation contract tests: passed.
- `market-data-platform` quality governance tests: 13 passed.
- `quant-execution-engine` CLI unit tests: 44 passed.

The main issue is not a failing local checkout. The issue is long-term maintainability: the documentation tree has 21k+ Markdown lines across the workspace, with dated handoff notes, release notes, large vendor references, current operational guidance, and newcomer entrypoints sharing the same visible path. Some tests also require fixed wording such as exact Chinese phrases, which makes prose cleanup risky even when the protected fact remains true.

## Goals / Non-Goals

**Goals:**

- Make the first reading path clear for a new maintainer across data platform, strategy research, execution engine, and top-level governance.
- Separate active guidance, reference material, and archived history in every repo that needs those categories.
- Preserve current data and execution contract facts, especially `metadata/current_assets/a_share_current.json`, `targets.json`, and the data-platform -> research -> execution handoff.
- Update tests so they protect commands, paths, contract names, parser coverage, pytest marker coverage, archive indexes, and link integrity.
- Reduce defensive or translated-sounding prose in active docs while allowing precise technical caveats where they prevent unsafe interpretation.

**Non-Goals:**

- No CLI behavior changes.
- No data asset, provider API, schema, or current contract changes.
- No deletion of historical research notes or release evidence.
- No broker capability claim changes.
- No full rewrite of every research note; archived notes only need enough structure and indexing to stay findable.

## Decisions

1. Use a three-part documentation taxonomy: active, reference, archive.

   Active docs explain current work and first-run workflows. Reference docs describe stable APIs, commands, contracts, outputs, and provider details. Archive docs keep dated handoffs, release notes, historical research, and migration records. This keeps current guidance short without losing provenance.

2. Keep top-level docs focused on cross-repo boundaries.

   The superproject should explain clone/bootstrap, submodule roles, contract handoff, version matrix, release checklist, and quality delegation. Submodule internals stay in the owning repo. This matches the root AGENTS rule and avoids copying submodule policy into the superproject.

3. Treat document moves as migrations with indexes.

   Dated files should move under archive folders with an index that explains status and reading order. Existing links must be updated. When a moved document is likely to be referenced externally, leave a short forwarding stub for one release cycle; otherwise update internal links directly.

4. Make version matrix output generated-first.

   `docs/version-matrix.md` should include a generated current-checkout table or clear instructions to regenerate it. The generator should distinguish initialized submodules, missing submodules, dirty repos, and non-git source snapshots. Plain zip/source snapshots should get a clear limitation message instead of a stack trace.

5. Make style checks advisory by default and strict only for active docs.

   Active README, AGENTS, and primary docs should avoid unnecessary "不是 / 而是 / 不代表 / 不等于" phrasing. Archived research notes can retain historical prose unless they are touched for another reason. Tests should report offenders with enough context and allow documented exceptions for safety caveats.

6. Replace exact-prose tests with fact-based tests.

   Documentation contract tests should check stable facts: command names, module entrypoints, public/private CLI layering, current contract paths, pytest markers, parser leaf commands, archive index membership, and link targets. They should not require a particular Chinese sentence to appear.

7. Add focused doc consistency checks where coverage is missing.

   `market-data-platform` should gain CLI documentation coverage similar to `cross-sectional-trees`. `quant-execution-engine` should gain lightweight checks that top-level CLI commands are documented, pytest markers in `pyproject.toml` are listed in `docs/testing.md`, and broker smoke docs cover known broker backends.

8. Split only documents that are already doing multiple jobs.

   Good candidates are `cross-sectional-trees/docs/outputs.md`, `cross-sectional-trees/docs/rqdata/hk-stock-data-reference.md`, `market-data-platform/docs/operations.md`, and `quant-execution-engine/docs/testing.md`. Small docs should stay small; moving files without reducing reader effort is churn.

## Risks / Trade-offs

- Link churn can break local or external references. Mitigation: update all internal Markdown links and add forwarding stubs only for high-value historical entrypoints.
- Overly broad style lint can block legitimate safety caveats. Mitigation: make archive docs exempt by default and allow explicit exceptions for technical negation.
- Restructuring `cross-sectional-trees` research notes can produce a large diff. Mitigation: move notes in batches and keep metadata/index tests as the guardrail.
- Generated version matrix content can become stale again if edited manually. Mitigation: mark generated sections clearly and test that the documented command still runs in a git checkout.
- Adding doc coverage tests in submodules can make future CLI changes noisier. Mitigation: derive expected commands from parsers and keep the required docs tokens factual.

## Migration Plan

1. Update top-level documentation first: README, docs index, version matrix, HK archive entrypoint, and top-level link tests.
2. Update `cross-sectional-trees`: archive or demote historical research/vendor references, split output references, and loosen prose-locked doc tests.
3. Update `market-data-platform`: split operations, archive dated session handoff, expand recursive style scanning, and add CLI doc coverage.
4. Update `quant-execution-engine`: separate stable testing guidance from migration notes, archive phase checklists, and add lightweight CLI/marker/smoke doc tests.
5. Run focused tests at each boundary, then run the superproject doctor and delegated submodule checks needed by the touched areas.

## Open Questions

- Should moved top-level dated HK documents keep one-release forwarding stubs, or should internal link updates be enough?
- Should archived `cross-sectional-trees` research notes stay under `docs/research/archive/` or move to `docs/archive/hk-research-notes/`?
- Should style lint fail on active docs immediately, or run as an advisory report for one cleanup pass before becoming a hard gate?
