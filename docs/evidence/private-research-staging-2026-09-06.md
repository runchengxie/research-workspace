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
`63ed835` (`feat: stage private DailyWatch20 research slice`).

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

This is not yet a production-ready `quant-research` repository. The next gate is to connect a
versioned DailyWatch20 artifact export to the existing `market-intel` consumer, validate the
artifact contract, and only then decide whether to create a remote private repository and update
the workspace manifest. Until that gate passes, the old `strategy-research` and `strategy-app`
repositories remain authoritative and are the rollback source.
