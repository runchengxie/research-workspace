## Context

The workspace already has good boundary concepts: data platform -> strategy research -> trading execution, `targets.json` as the handoff, and HK cold-storage restore evidence. The `split-hk-public-demo` change adds a public demo staging manifest, but the remaining audit findings are broader than demo separation.

Current weak points are visible in local project configuration and repo structure:

- `cross-sectional-trees` Ruff only selects a small set of syntax/import/complexity rules and Pyright includes only three source files.
- `market-data-platform` still excludes `src/market_data_platform/hk_assets` from Ruff and excludes large HK/data-provider/release surfaces from Pyright.
- `quant-execution-engine` has Ruff/Pyright/mypy, but Pyright remains basic and execution-critical modules are not independently strict-gated.
- Deprecated HK compatibility entrypoints still exist without hard owner/milestone/removal fields.
- Long scripts and internal tools are present, but their lifecycle, safety, write targets, and removal conditions are not uniformly documented.
- There is no top-level CODEOWNERS, CONTRIBUTING, architecture entrypoint, or PR checklist enforcing maintainability concerns before new debt enters.

The implementation should improve governance and measurable quality first. Large code splits, CLI removals, and strict type-checking of heavily indebted modules should be staged behind baselines and focused tests.

## Goals / Non-Goals

**Goals:**

- Add cross-repo deprecation governance with owners, replacement paths, removal milestones, and deletion evidence.
- Add script lifecycle metadata for superproject scripts and representative submodule internal/project tools.
- Add maintainability baseline reporting for large files, long functions, complexity hotspots, quality excludes, and Ruff/Pyright coverage.
- Expand Ruff/Pyright coverage in low-risk increments and record remaining debt explicitly.
- Add team collaboration guardrails: CODEOWNERS, CONTRIBUTING, ARCHITECTURE, and PR checklist.
- Keep verification ordered by repository boundary: data platform -> strategy research -> trading execution -> top-level docs/doctor -> limitations.

**Non-Goals:**

- Do not delete HK compatibility commands in the first implementation pass.
- Do not refactor every large module immediately.
- Do not force Pyright strict across all modules at once.
- Do not change provider APIs, broker behavior, `targets.json`, current asset contracts, or CLI runtime semantics.
- Do not move licensed data, provider cache, research outputs, or trading audit logs.

## Decisions

1. Treat governance artifacts as source-of-truth inputs to tests.

   Add top-level documents and JSON/YAML-subset manifests that tests can validate. Prose-only guidance is not enough because it cannot catch missing owners, missing removal milestones, or unclassified scripts.

   Alternative considered: only expand docs. That improves readability but does not stop new debt from entering.

2. Use staged quality expansion.

   For each submodule, first add or refresh baseline metrics. Then include low-risk modules in Ruff/Pyright. Then tighten execution-critical or contract-critical modules. Remaining excludes must be registered with owner and next action.

   Alternative considered: enable broad Ruff/Pyright strictness immediately. That is likely to produce a large diff and can block work on legacy modules before the team agrees on priorities.

3. Keep HK compatibility deletion separate from governance.

   The first implementation should add deprecation records and removal conditions for `hkdata`, `rqdata-hk-*`, `src/hk_data_platform`, `cstree alloc-hk`, and HK historical configs. Actual deletion requires restore evidence, consumer audit, replacement docs, rollback notes, and focused tests.

   Alternative considered: delete deprecated entrypoints now. That conflicts with existing restore-sensitive and downstream-audit constraints.

4. Add lifecycle metadata before moving scripts.

   Scripts should be classified as `dev`, `ci`, `release`, `migration`, or `archive`, with safety and write-target metadata. Physical directory reshuffles can follow after the metadata exists and tests know what to expect.

   Alternative considered: move scripts into new directories first. That creates link churn and can break existing automation without improving safety immediately.

5. Use cross-repo collaboration docs, but keep ownership local.

   Top-level CODEOWNERS and CONTRIBUTING should name repo boundaries and PR requirements. Submodule-specific implementation details remain in submodule docs and AGENTS files.

   Alternative considered: copy all submodule rules into the superproject. That violates the workspace boundary and makes docs drift more likely.

## Risks / Trade-offs

- Broad governance can become paperwork -> Make every required field testable and tied to a review or deletion decision.
- Baselines can normalize debt -> Require owner, threshold, and next action for every allowed exception.
- Quality expansion can break CI -> Start with advisory/focused checks, then promote only selected modules to hard gates.
- Script metadata can get stale -> Derive tests from script inventory and fail when new non-trivial scripts lack metadata.
- CODEOWNERS can be too coarse -> Start with repo-boundary ownership, then refine package-level ownership only where maintainers exist.
- Applying this while `split-hk-public-demo` is unarchived can create overlapping docs -> Preserve split manifest links and treat it as an input, not a replacement.

## Migration Plan

1. Add governance docs and manifests: deprecations, script lifecycle, maintainability baseline, CODEOWNERS, CONTRIBUTING, architecture overview, and PR checklist.
2. Add top-level tests validating deprecation fields, script metadata, baseline schema, doc links, and PR checklist coverage.
3. Update submodule quality configs in low-risk increments:
   - `cross-sectional-trees`: broaden Ruff rule families and extend Pyright include to pipeline/liveops modules that already have contracts or export boundaries.
   - `market-data-platform`: stop permanently excluding all HK assets from Ruff; include small HK model/shared/public modules in Pyright first.
   - `quant-execution-engine`: define strict or near-strict Pyright/mypy targets for execution-critical modules while keeping optional broker runtime imports handled.
4. Add or update submodule focused tests for quality governance and maintainability baselines.
5. Add script metadata comments or sidecar manifest entries for top-level scripts and representative internal/project tools.
6. Run focused tests per boundary, then root doctor and doc/link/quality checks.
7. Leave actual removal/refactor work as follow-up changes once governance evidence is in place.
