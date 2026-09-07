# Quant supersession parity audit

> status: active
> owner: workspace
> last_verified: 2026-09-06

## Counts

The audit includes the complete checked-out `research-workspace` tree,
including its initialized submodules, and both staging repositories.

| Area | New repositories | Research workspace | Difference |
| --- | ---: | ---: | ---: |
| Python files | 2,386 | 2,139 | +247 |
| Python LOC | 481,565 | 436,058 | +45,507 |
| Nonblank Python LOC | 424,318 | 383,941 | +40,377 |
| Markdown files | 627 | 772 | -145 |
| Markdown LOC | 49,674 | 70,653 | -20,979 |
| Nonblank Markdown LOC | 36,740 | 52,115 | -15,375 |

The extra Python volume does not prove complete transfer. The target layout
uses different paths and includes public/private splits, so exact path matches
are intentionally low. The audit report records basename and AST symbol
matches as heuristics requiring component-level review.

## Confirmed transfer work

1. `strategy-research` has moved from migration source commit `087b5df` to
   current workspace commit `fe8ebff`. The intervening history contains 93
   changed paths and about 6,061 insertions, dominated by cashflow research,
   ML universe studies, PIT audits, capacity diagnostics, OOS evaluation,
   production gates, tests, and decision documents. The current
   `quant-research` target already contains these paths, so they are not a
   simple missing-file transfer. They still require semantic parity review.
2. The current target review found 35 same-path content differences against
   the source checkout: two implementation modules, three research scripts,
   two documentation indexes, and 28 tests. Most are intentional namespace,
   dependency, or font-portability adaptations. One substantive gap remains:
   `build_cni_980092_full_candidate_panel.py` in the target lacks the source's
   `availability_lag_days` parameter and point-in-time lag behavior.
3. The current workspace root owns integration tooling that is not part of the
   two target repositories. This includes workspace doctor, version
   composition, submodule checks, governance checks, quality gates, contract
   smoke tests, and their root tests. The architecture plan assigns these to a
   retained thin workspace integration layer rather than duplicating them in
   the platform or private research package.
4. Active workspace documentation is larger than the combined target
   documentation by about 21,000 physical Markdown lines. Architecture,
   governance, migration, release, operations, research evidence, and current
   cashflow documents require ownership decisions and compatibility pointers.

## Intentional exclusions

The public platform manifests intentionally exclude credentials, provider SDKs,
raw data, real-data manifests, private labels and universes, private runtime
configuration, experiment outputs, and promoted-model results. These belong in
the private target or outside Git, not in `quant-platform`.

## Cutover rule

Supersession is not complete until every required gap is classified as one of
`TRANSFER_REQUIRED`, `PUBLICLY_EXCLUDED_PRIVATE_TARGET_REQUIRED`,
`RETAIN_IN_WORKSPACE`, `DOCUMENTATION_RELOCATE`, `HISTORICAL_ARCHIVE`, or
`REVIEW_REQUIRED`, and all `TRANSFER_REQUIRED` items have component-level
source, target, symbol, test, and documentation evidence.
