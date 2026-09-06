# Architecture migration closure checklist

> status: all staged parity slices validated; consumer cutover pending
> verified: 2026-09-06

## Target architecture

The intended end state is:

> `quant-platform` provides reusable capability, `quant-research` preserves
> strategy IP, `market-intel` presents and delivers results, and
> `research-workspace` locks compatible versions.

The current repository names remain authoritative until each migration slice
has its own release and rollback evidence. The target mapping is recorded in
`docs/governance/repository-naming-map.md` and
`docs/architecture-model.yml`.

The approved sequence and rollback triggers are recorded in
`docs/migrations/architecture-cutover-runbook.md`.

## Verified gates

- Public platform at `2ba7088`: Apache-2.0, portfolio/data/alpha/microstructure/orchestration/execution framework slices transferred; local full gate is `1146 passed, 3 skipped`, Ruff and format clean. Public GitHub Actions is green in run `34024056490`.
- Private research at `5265b68`: alpha, microstructure, strategy families, and private execution runtime are transferred; legacy `alpha-research`/`strategy-pipeline` dependencies have been removed in favor of the consolidated framework. All six private transfer jobs are green in CI run `34024857688`.
- Public alpha scope intentionally excludes DailyWatch20/Hotsector strategy-specific modules and ownership/result documents; those remain in private research. Public alpha contains 135 source files, 70 tests, and 31 docs.
- Public orchestration/execution foundations and private broker/runtime code are transferred and covered by their scoped suites.
- Public microstructure framework at `2ba7088` contains only generic event-stream/model/simulator machinery; its synthetic suite passes `45 tests`. Real-data coverage, labels, experiments, and results remain private.
- Private strategy-family source, tests, docs, research records, and runtime imports are transferred; import smoke, DailyWatch20 validation, and the strategy-family CI job are green in `34024857688`. Legacy standalone repository-root governance tests remain excluded where their assertions intentionally require the retired repository layout.
- Formal-shaped DailyWatch20 producer → publication contract → `market-intel`
  consumer handoff: passed for both approved artifacts.
- `market-intel` boundary and production-shaped handoff tests pass; synthetic
  DailyWatch20 fixture is pushed at `89a35d9`; CI run `34025080421` is green
  on Python 3.11–3.13.
- Workspace thin-layer doctor tests: `23 passed`; doctor reports `0 errors`.
- Architecture model tests: `7 passed`; architecture scan reports `0 errors`.
- Contract smoke: all checks passed with `0 errors`, `0 warnings`.
- Hard quality profile: all checks passed, including Ruff, format, ty, import
  boundaries, ownership boundaries, architecture, capability registry, trial
  ledger, and secret scan.
- `quant-platform` and `quant-research` GitHub repositories were created and
  pushed. Both public platform CI and private research CI completed
  successfully for the validated slice.

## AI context policy

Agents default to the directly affected package and its local manifest. They
expand to producer, contract, and consumer only for public API changes,
artifact changes, downstream failures, or explicit cross-module work. The
machine-readable routing is provided by `scripts/context_manifest.py`.

## Rollback rehearsal

An isolated temporary release root exercised:

1. failed validation leaves `current` pointing to the old release;
2. a validated candidate is promoted through a temporary symlink and atomic
   replace;
3. the old release is restored through the same atomic mechanism.

The real production pointers were read before and after the rehearsal and were
unchanged:

- `production/market-intel/current` → release `482cb31b...`
- `production/research-workspace/current` → release `9267bbae...`

No production pointer, artifact, remote, or GitHub repository was modified.

## Intentionally pending

- Actual workspace consumer cutover to the new remotes.
- Repository rename/redirect decisions and old-submodule removal.
- Full release-type gate on the final migrated repositories.

These require an explicit publication/rename decision and are not implied by
the local staging evidence.
