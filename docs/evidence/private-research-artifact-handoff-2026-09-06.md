# Private research artifact handoff evidence

> status: migration rehearsal
> verified: 2026-09-06

## Scenario

The staged DailyWatch20 strategy specification from the local private repository
`/home/richard/code/.private-staging/quant-research` was published as an internal
`research.platform-publication.v1` bundle. The bundle was then verified using the existing
`market-intel` consumer implementation.

The producer identity was:

```text
repository: runchengxie/quant-research
commit:     63ed835
run_id:     migration-rehearsal-daily-watch20
```

The published projection was:

```text
artifact_id:    daily_watch20.strategy-spec
schema_version: daily_watch20.strategy-spec.v1
audience:       internal
consumer:       market-intel
```

## Result

The consumer verified the publication schema, producer identity, declared audience, relative path,
and SHA-256 content digest successfully. The bundle contained one artifact and was written under a
temporary directory only; no production artifact, `latest` pointer, workspace gitlink, or remote
repository was changed.

This proves the repository boundary and publication mechanism. It does not yet replace the formal
`watchlist_20.csv` / `selection_receipt.json` producer, which remains the orchestration layer until
the private strategy logic is integrated into that runtime and the full DailyWatch20 contract is
validated.

The current formal publisher was also checked from the `strategy-app` source worktree:

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_publication_contracts.py \
  tests/test_daily_watch20_publication_orchestration.py \
  tests/test_daily_watch20_publication_validation_core.py -q
```

Result: `13 passed`. This validates the existing owner’s publication safeguards; it is not evidence
that the formal producer has already moved to `quant-platform`.
