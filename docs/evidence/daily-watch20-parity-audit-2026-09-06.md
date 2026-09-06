# DailyWatch20 parity audit — 2026-09-06

Status: **not yet cutover-ready**

This audit compares the first `quant-research` migration slice with the pinned
source commits recorded in `quant-research/migration/provenance.json`.

## Result

The implementation source and regression suite are now complete for the
selected DailyWatch20 package:

- `strategy-app` source: 104 DailyWatch20 modules and the campaign specification
- `quant-research`: the same 104 modules and campaign specification, plus the
  six shared `strategy_app` package modules required by the slice

The implementation parity is now complete. Remaining gates concern dependency
ownership, independent CI, and consumer/cutover validation.

| Area | Source baseline | Target | Status |
|---|---:|---:|---|
| Strategy implementation modules | 104 | 104 | complete |
| Campaign specification | 1 | 1 | complete |
| Direct regression tests | 32 | 32 | complete |
| Strategy-app documentation | 10 | 10 | complete |
| Strategy-research evidence/configuration | 11 related files | 11 | complete |
| Packaging/dependency declaration | legacy package | target package | requires reconciliation |
| CI workflow | none in source | target workflow added | first remote run pending |

## Remaining release gates

### Dependencies and runtime

The target package still declares legacy package names and a legacy
`strategy-pipeline` Git dependency. Before cutover, replace these with the
intended target package boundaries or explicitly document why each dependency
remains external. The private CI workflow now installs the target package and
runs the full DailyWatch20 suite plus the publication-adapter test; its first
remote run is still required.

## Cutover decision

Do not update `research-workspace` gitlinks or retire the legacy repositories
yet. The old `strategy-app` and `strategy-research` commits remain the
authoritative rollback sources until all items above are restored, tests pass,
the private publication handoff is revalidated, and the production manifest has
a tested rollback path.
