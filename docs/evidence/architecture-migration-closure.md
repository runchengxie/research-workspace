# Architecture migration closure checklist

> status: staging-only; remote migration not authorized
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

## Verified gates

- Public platform staging at `a1de2f9b`: `31 passed`, Ruff clean and formatted.
- Private research staging: `26 passed`; publication adapter `3 passed`, Ruff clean.
- Formal-shaped DailyWatch20 producer → publication contract → `market-intel`
  consumer handoff: passed for both approved artifacts.
- Locally integrated `market-intel` boundary: boundary `2 passed`; broader
  contract/freshness/recovery gate `112 passed`.
- Workspace thin-layer doctor tests: `23 passed`; doctor reports `0 errors`.
- Architecture model tests: `7 passed`; architecture scan reports `0 errors`.
- Contract smoke: all checks passed with `0 errors`, `0 warnings`.
- Hard quality profile: all checks passed, including Ruff, format, ty, import
  boundaries, ownership boundaries, architecture, capability registry, trial
  ledger, and secret scan.

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

- Remote creation or rename of `quant-platform` and `quant-research`.
- Actual public/private repository cutover and old-submodule removal.
- Full release-type gate on the final migrated repositories.

These require an explicit publication/rename decision and are not implied by
the local staging evidence.
