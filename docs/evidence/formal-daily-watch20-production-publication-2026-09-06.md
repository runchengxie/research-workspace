# Formal DailyWatch20 production publication evidence

> status: production publication verified; workspace T0 still pending
> verified: 2026-09-06

The latest existing DailyWatch20 production artifact was exported through the
private `quant-research` publication adapter into an immutable, versioned
bundle:

```text
/home/richard/data/market-data-platform/published/platform_publications/
  daily_watch20/20260906_production_migration_2b51d33/
```

The source was the existing formal producer output at
`strategy_outputs/watchlist20/latest/`. The source receipt identifies
`source_date=20260903` and `signal_date=20260904`.

## Producer

- repository: `runchengxie/quant-research`
- commit: `2b51d332464895d71c08ec78d08d0c2a722313db`
- run id: `production-migration-20260906`
- publication schema: `research.platform-publication.v1`

## Published artifacts

| Artifact | Relative path | SHA-256 |
| --- | --- | --- |
| `daily_watch20.watchlist_20` | `strategies/daily_watch20/watchlist_20.csv` | `685310ab177023434a0ac80831e5475b7203b6eb3c11999feb9a1f2018f3c9da` |
| `daily_watch20.selection_receipt` | `strategies/daily_watch20/selection_receipt.json` | `217e6ac8243682c56574edef0cc658738a7e36ab8f1ba917db78d5b4521d7229` |

## Consumer acceptance

`market-intel` verified the bundle with `allow_internal=True`, consumer
`market-intel`, and accepted both artifacts. The verifier confirmed the
producer identity, internal audience, consumer declaration, bundle-relative
paths, file existence, and SHA-256 hashes.

This publication does not replace the existing legacy `latest` pointer and
does not yet advance either production code pointer. It is the formal data
publication prerequisite for the workspace T0 promotion.
