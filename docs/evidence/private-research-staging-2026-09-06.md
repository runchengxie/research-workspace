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
`12f80eb` (`feat: export formal DailyWatch20 publication`).

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
publication API. It consumes the formal publisher's `latest/watchlist_20.csv` and
`latest/selection_receipt.json`, emits an internal manifest for `market-intel`, and excludes source
paths. Focused adapter verification passed (`3 passed`; Ruff clean). The formal producer code is
present in the staging slice, but the old `strategy-research` and `strategy-app` repositories
remain authoritative and are the rollback source until the full runtime suite is aligned.

The staging resolver now overrides alpha’s old Git URL with the public staging
`research-contracts` package, restoring the expected `ArtifactEnvelopeV2` API. The full copied
suite then reaches a second existing compatibility prerequisite: the resolved
`portfolio-backtester` package lacks the `name_turnover` API required by the copied strategy slice.
That dependency pin must be aligned before the full private suite can run; the focused adapter gate
remains green and no tests were silently weakened.
