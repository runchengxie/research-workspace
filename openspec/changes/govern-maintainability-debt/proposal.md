## Why

The previous `split-hk-public-demo` change made the public demo boundary explicit, but it did not pay down the broader maintainability debt in the three active subprojects. Deprecated HK compatibility paths, one-off scripts, long orchestration modules, narrow Ruff/Pyright coverage, and missing team-level contribution guardrails still make the workspace harder to maintain as a team project.

This change turns the audit findings into enforceable governance: record what is deprecated and when it can be removed, classify scripts by lifecycle, baseline complexity hotspots, expand quality coverage in staged steps, and add collaboration entrypoints that prevent new debt from entering quietly.

## What Changes

- Add a cross-repo maintainability governance plan that distinguishes active code, compatibility code, archive/provenance, demo staging, and private runtime surfaces.
- Add `docs/deprecations.md` with owner, replacement command, current consumers, removal condition, target milestone, rollback path, and required tests for deprecated HK surfaces such as `hkdata`, `rqdata-hk-*`, and `cstree alloc-hk`.
- Add script lifecycle metadata and checks for non-trivial scripts: owner, purpose, lifecycle (`dev`, `ci`, `release`, `migration`, `archive`), safe-to-run status, write targets, external dependencies, and removal condition.
- Add maintainability baseline checks for large files, long functions, high complexity, Ruff/Pyright coverage, and registered ignores across all three submodules.
- Expand quality gates incrementally rather than all at once: first measure, then include low-risk modules, then tighten strictness for execution-critical and contract-critical modules.
- Add team collaboration documents such as `CODEOWNERS`, `CONTRIBUTING.md`, an architecture entrypoint, and a PR checklist focused on deprecated surfaces, one-off scripts, quality excludes, `targets.json`, provider credentials, and migration notes.
- Do not remove production HK compatibility code in the first pass; deletion remains gated by restore evidence, consumer audit, replacement docs, focused tests, and rollback notes.

## Capabilities

### New Capabilities

- `maintainability-debt-governance`: Defines deprecation milestones, script lifecycle metadata, complexity and quality baselines, staged Ruff/Pyright expansion, and team contribution guardrails across the workspace and submodules.

### Modified Capabilities

None.

## Impact

- Affects top-level docs and tests for maintainability governance, deprecations, script lifecycle, quality baseline reporting, and PR/contribution workflow.
- Affects `market-data-platform` quality governance around HK assets, HK depth, legacy `hk_data_platform` wrappers, and `rqdata-hk-*` scripts.
- Affects `cross-sectional-trees` governance around `alloc-hk`, HK research/config provenance, Ruff rule selection, Pyright include scope, and C901 debt tracking.
- Affects `quant-execution-engine` governance around core execution type checking, LongPort/private runtime boundaries, CLI size, and broker smoke tooling lifecycle.
- No runtime API, data contract, provider API, broker behavior, or CLI removal is intended in the first implementation pass.
