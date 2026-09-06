# Private `quant-research` staging evidence

> status: staging-only
> verified: 2026-09-06
> source_of_truth: migration rehearsal evidence

## Result

A local private Git repository now exists at:

```text
/home/richard/code/.private-staging/quant-research
```

It contains one DailyWatch20 vertical slice extracted from the current
`strategy-research` and `strategy-app` gitlinks. The staging repository is committed at
`52cfcc2` (`feat: add private publication adapter`).

The slice includes:

- strategy identity and lifecycle documentation;
- a private registry entry;
- the strategy-specific `strategy_app.daily_watch20` implementation;
- a frozen campaign specification;
- selected direct regression tests;
- provenance and rollback documentation.

## Safety checks

- Existing workspace gitlinks were not changed.
- No GitHub repository was created.
- Nothing was pushed or published.
- No credentials, raw datasets, parquet files, CSV data, or provider secrets were copied.
- JSON metadata parsed successfully.
- The migrated Python package compiled successfully with `compileall`.

## Remaining integration work

The private staging repo now has a tested adapter that consumes the public `quant_platform`
publication API. It requires `watchlist_20.csv` and `selection_receipt.json`, emits an internal
manifest for `market-intel`, and excludes source paths. Focused adapter verification passed (`2
passed`; Ruff clean). The formal producer has not yet been moved into this staging repo, so the old
`strategy-research` and `strategy-app` repositories remain authoritative and are the rollback
source.

The copied alpha dependency set also exposes an existing compatibility prerequisite: the resolved
`research-contracts` package is missing `ArtifactEnvelopeV2`, so the full copied private suite
cannot run until its dependency pins are aligned. This is recorded as a migration gate rather than
silently weakening the test scope.
