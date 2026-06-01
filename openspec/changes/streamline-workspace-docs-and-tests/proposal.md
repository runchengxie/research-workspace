## Why

The workspace documentation already covers the current data-platform -> research -> execution handoff, but it mixes active guidance, historical handoffs, release notes, vendor references, and research notes in the same primary reading path. The tests are useful, but some of them lock exact Chinese phrasing or current file layout, which makes documentation cleanup harder than the facts being protected.

## What Changes

- Reorganize README, AGENTS, and docs entrypoints so a new maintainer can quickly see what is active, what is reference material, and what is archived history.
- Move dated handoff, freeze, and migration records into archive sections with index pages, while keeping stable links or redirects from active documentation.
- Update `docs/version-matrix.md` and its generator workflow so it reflects the current checkout, submodule initialization state, and git-only requirements.
- Simplify repeated or defensive wording in user-facing docs, especially "不是 / 而是 / 不代表 / 不等于" constructions, while preserving necessary technical caveats.
- Split long mixed-purpose docs where they are now acting as multiple documents, especially large output/reference docs and broad operations pages.
- Adjust documentation tests to protect stable facts, commands, paths, contracts, and parser/doc coverage instead of requiring exact prose.
- Add missing lightweight documentation coverage checks where a subproject exposes CLI or pytest behavior without a corresponding doc consistency guard.

## Capabilities

### New Capabilities
- `workspace-docs-test-governance`: Defines cross-repo documentation structure, archive policy, language quality expectations, version-matrix freshness, and documentation test contracts for the superproject and three submodules.

### Modified Capabilities

None.

## Impact

- Affects top-level `README.md`, `AGENTS.md`, `docs/*.md`, `scripts/print_version_matrix.py`, `scripts/workspace_doctor.py`, and top-level documentation tests.
- Affects documentation and focused documentation tests in `cross-sectional-trees`, especially docs contract tests, research notes indexing, `outputs.md`, and RQData reference placement.
- Affects documentation and governance tests in `market-data-platform`, especially operations docs, session handoff placement, style checks, and CLI documentation coverage.
- Affects documentation and lightweight consistency tests in `quant-execution-engine`, especially testing docs, CLI docs, broker smoke docs, and migration/checklist placement.
- No public runtime API, data contract, or CLI behavior is intended to change.
