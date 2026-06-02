# Contributing

This workspace is the integration layer for three submodules. Most feature work
belongs in the owning submodule; top-level changes should focus on contracts,
submodule versions, workspace health, release checklists, governance, and cross-repo
documentation.

## Scope

- Data platform changes belong in `market-data-platform`.
- Strategy research changes belong in `cross-sectional-trees`.
- Trading execution changes belong in `quant-execution-engine`.
- Top-level docs and scripts should only cover cross-repo handoff, contract,
  release, health, and governance concerns.

When a change edits submodule contents, review the submodule `AGENTS.md` and
include the submodule `git status --short` in the final summary. Do not revert
unrelated submodule changes or dirty gitlinks.

## Verification Order

Report verification in this order:

1. Data platform.
2. Strategy research.
3. Trading execution.
4. Top-level docs and doctor.
5. Remaining limitations.

If a repo is not touched, state that no focused tests were required for it.

## Maintainability Gate

Before opening a PR, check whether the change:

- introduces or extends a deprecated surface;
- adds a one-off script or migration tool;
- adds a Ruff, Pyright, or mypy exclude;
- changes the `targets.json` handoff contract;
- reads provider or broker credentials;
- needs a migration note, rollback path, or restore evidence.

Use [`docs/deprecations.md`](docs/deprecations.md),
[`docs/script-lifecycle.yml`](docs/script-lifecycle.yml),
[`docs/quality-coverage-governance.yml`](docs/quality-coverage-governance.yml),
and [`docs/maintainability-refactor-roadmap.yml`](docs/maintainability-refactor-roadmap.yml)
as the source of truth for those checks.
