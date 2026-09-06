# Architecture migration closure checklist

> status: one parity slice validated; consumer cutover pending
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

- Public platform at `507628e`: Apache-2.0, full portfolio source/tests/docs/scripts/config transfer, `586 passed`, Ruff and ty clean; public CI green at `34020081799`.
- Private research staging at `a77fb73`: complete DailyWatch20 parity suite `122 passed` locally; publication adapter included; private CI green after validating private dependency access.
- Formal-shaped DailyWatch20 producer → publication contract → `market-intel`
  consumer handoff: passed for both approved artifacts.
- `market-intel` boundary: boundary `2 passed`; broader contract/freshness/recovery
  gate `112 passed`; public CI green on Python 3.11–3.13 at `83172a3`.
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
