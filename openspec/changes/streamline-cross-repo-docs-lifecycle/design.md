## Context

`research-workspace` is the superproject for data-platform, strategy-research, and execution-engine handoff. Its top-level docs should stay thin and authoritative: cross-repo workflow, contracts, current version combinations, release gates, and market transition rules.

`cross-sectional-trees` has a larger documentation surface because it includes user guides, playbooks, concepts, output references, and historical research notes. The highest-noise area is the Hong Kong market historical research material under `docs/research/notes/`, which is already described as `archived_provenance` but still sits under the active research path. Several Hong Kong market data and RQData pages also repeat sunset or shared-platform boundaries.

The implementation must respect existing repository boundaries:

- Top-level `docs/` stays limited to cross-repo collaboration, contracts, release/checklist topics, and archive entry points.
- Subproject details stay in subproject docs.
- Canonical A-share current contract naming remains `metadata/current_assets/a_share_current.json`.
- Public interfaces, paths, asset keys, provider API names, and historical artifact names are not renamed as cleanup side effects.
- Documentation tests are part of the contract and must be updated intentionally when files move.

## Goals / Non-Goals

**Goals:**

- Make every current documentation entry point clearly distinguish active guidance, stable reference, archived record, and superseded material.
- Reduce `research-workspace` primary reading paths by consolidating overlapping Hong Kong market archive, private archive, public demo, and legacy-surface pages.
- Move process records and one-time handoff documents under archive record paths or structured manifests.
- Move or re-index `cross-sectional-trees` Hong Kong market research notes so they no longer look like active research guidance.
- Replace duplicated Markdown checklists with structured manifests when the content is primarily inventory, evidence, or gate state.
- Preserve traceability for restore, audit, and historical research reproduction.

**Non-Goals:**

- No runtime behavior change in `market-data-platform`, `cross-sectional-trees`, or `quant-execution-engine`.
- No data asset migration, provider download, training run, broker dry-run, or release execution.
- No deletion of archived evidence in the first implementation pass.
- No broad rewrite of unrelated docs for tone or style.
- No renaming of canonical contracts, asset keys, CLI names, provider identifiers, or historical artifact names.

## Decisions

1. Use explicit lifecycle metadata for active and archival docs.

   Add a compact status block to entry-point docs and moved archive pages with fields such as `status`, `owner`, `last_verified`, `source_of_truth`, and `superseded_by`. This is more useful than relying on directory names alone because some archive pages remain important restore references.

   Alternative considered: only move files into `archive/`. That lowers visible noise but does not identify source-of-truth ownership or stale pages when links still point to the old location.

2. Keep Markdown for human routing and use manifests for inventory.

   Pages such as the Hong Kong market archive README should explain the current boundary and link to structured manifests. Itemized keep/move/archive/delete records should live in YAML or JSON manifests where tests can validate them.

   Alternative considered: keep long Markdown tables. That is easy to read casually but duplicates manifest state and creates two places to update.

3. Archive first, delete later.

   The first implementation pass should move or re-index historical material and update links/tests. Deletion of confirmed-unused archive content should be a later change after link checks and consumer references are clean.

   Alternative considered: delete superseded pages immediately. That gives a smaller tree faster but increases the chance of breaking restore evidence and doc contract tests.

4. Treat `cross-sectional-trees/docs/research/notes/` as historical provenance.

   The active research docs should retain only a short index or summary that points to archived Hong Kong market notes. Historical monthly/quarterly reasoning remains discoverable but should not appear as required reading for current A-share work.

   Alternative considered: leave notes in place and add stronger warnings. The current README already does this, and the directory still reads as active because of its path and volume.

5. Update tests to assert lifecycle intent rather than old file locations.

   Tests should continue to protect public CLI tokens, market lifecycle tokens, playbook availability, and doc link integrity. Where paths move, tests should assert the new archive entry, compatibility link, or manifest token instead of the stale active file.

   Alternative considered: weaken tests during cleanup. That would reduce friction but remove the guardrails that make this repository maintainable.

## Risks / Trade-offs

- Link breakage -> Run top-level doc link tests and `cross-sectional-trees/tests/test_docs_contracts.py`; keep compatibility stubs where many internal links still point to old pages.
- Loss of restore evidence -> Move records instead of deleting them; keep manifest references and evidence JSON paths intact.
- Confusing source-of-truth ownership -> Add owner/status metadata to entry pages and reflect ownership in docs indexes.
- Oversized archive summaries -> Cap summary docs to routing and current conclusions; leave detailed historical narrative in archived notes.
- Submodule gitlink drift -> After submodule doc moves, check both submodule status and superproject gitlink status.

## Migration Plan

1. Add lifecycle metadata conventions to top-level and `cross-sectional-trees` docs entry points.
2. Consolidate top-level Hong Kong market archive routing into `docs/archive/hk/README.md`, backed by the existing public split and private archive manifests.
3. Fold or shorten `docs/a-share-production-readiness.md` into `docs/data-transition-playbook.md` if the readiness content repeats the playbook.
4. Move one-time top-level Hong Kong market release notes and handoffs under archive records, preserving links from the archive README.
5. Move `cross-sectional-trees/docs/research/notes/*.md` to an archive path or keep compatibility stubs with a new archive summary/index.
6. Compress overlapping Hong Kong market data/RQData pages and legacy research playbook content into one restore-oriented entry.
7. Merge `model-landscape.md` and `model-selection.md` into a single modeling concept page if no tests require separate active pages.
8. Update README/docs indexes, inline links, manifests, and doc tests.
9. Run focused documentation and workspace tests before considering broader checks.

Rollback is straightforward: restore moved docs and index links from git, then rerun the same doc tests. Because the first pass does not delete evidence or change runtime behavior, rollback does not require data or artifact recovery.

## Open Questions

- Should archived `cross-sectional-trees` research notes remain inside the submodule under `docs/archive/research/hk/notes/`, or move to an external private/archive repository in a later change?
- Should compatibility stubs be kept permanently for high-traffic docs such as `docs/playbooks/hk-selected.md`, or removed after one release window?
- Should lifecycle metadata be enforced by a new test immediately, or introduced as advisory metadata first and made mandatory after the first cleanup pass?
