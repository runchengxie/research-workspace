# Supersession ownership matrix

> status: active
> owner: workspace
> last_verified: 2026-09-06

| Legacy area | Target owner | Status | Evidence or action |
| --- | --- | --- | --- |
| `market-data-platform` | `quant-market-data-platform` | `REVIEW_REQUIRED` | Independent owner is fixed in `migration/supersession-component-map.json`; the `quant-research` copy is compatibility-only and pending removal after consumer repinning and rollback observation. |
| `deep-learning-tick-data-prediction` | `quant-platform` public microstructure plus `quant-research` private `ticknet` | `REVIEW_REQUIRED` | Private parity manifest claims 99 source, 88 test, 59 documentation, 16 script, and 39 config files. |
| `alpha-research` | `quant-platform` public alpha plus `quant-research` private alpha | `REVIEW_REQUIRED` | Private parity manifest claims exact source, test, documentation, and script counts; public target is framework-only. |
| `portfolio-backtester` | `quant-platform` | `REVIEW_REQUIRED` | Public migration is a published slice; verify all remaining backtest, portfolio, cost, capacity, risk, and reporting APIs. |
| `strategy-research` | `quant-research` | `REVIEW_REQUIRED` | Current target contains the migrated research tree; current source and target differ in 35 files, including one substantive PIT lag behavior gap now patched on the target branch. |
| `strategy-app` | `quant-research` | `REVIEW_REQUIRED` | Private strategy application parity is present in the target; validate current source and target revisions together. |
| `strategy-pipeline` | `quant-platform` | `REVIEW_REQUIRED` | Reusable orchestration is public; private adapters and runtime configuration remain private. |
| `quant-execution-engine` | `quant-platform` public foundation plus `quant-research` private runtime | `REVIEW_REQUIRED` | Public target excludes concrete broker adapters, SDK integrations, credentials, and private runtime. |
| Workspace root scripts/tests | `research-workspace` integration layer | `RETAIN_IN_WORKSPACE` | Version composition, contracts, doctor, governance, quality, and integration smoke checks are cross-repository responsibilities. |

## Status rule

No legacy repository or submodule is retired until every `REVIEW_REQUIRED`
component has a current source revision, target revision, symbol/test review,
documentation owner, consumer compatibility result, and rollback reference.
