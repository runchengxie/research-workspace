# Formal DailyWatch20 to `market-intel` handoff evidence

> status: staging-only; current target commits validated
> verified: 2026-09-06

This is a synthetic, formal-shaped runtime handoff. It uses the production
publisher's expected `latest/` layout, but it does not use production data,
publish a remote artifact, change a `latest` pointer, or modify any remote.

## Versions

- public `quant-platform`: `b67618ca243c7c3bfffd41720ae2b191a1c26378`
- private `quant-research`: `a77fb73` (same parity code; private CI green)
- `market-intel` consumer validation: `83172a38c26f7f7811d46c48539fa04d48838123`

## Handoff

1. Created a temporary formal-shaped source root containing:
   `latest/watchlist_20.csv` and `latest/selection_receipt.json`.
2. Ran `quant-research/scripts/export_publication.py`.
3. Verified the resulting `research.platform-publication.v1` bundle with
   `market-intel`'s `verify_platform_publication` using
   `consumer="market-intel"` and `allow_internal=True`.

The consumer accepted:

- `daily_watch20.watchlist_20`
- `daily_watch20.selection_receipt`

The verifier also confirmed the `runchengxie/quant-research` producer
identity, producer commit, internal audience, bundle-relative paths, and
SHA-256 hashes.

The same rehearsal was rerun against these current commits after both target
repositories were pushed. It accepted both approved artifacts:

```text
runchengxie/quant-research a77fb73
run-formal
daily_watch20.watchlist_20, daily_watch20.selection_receipt
```

This closes the staging end-to-end producer → contract → consumer gate. It
does not authorize remote repository creation, publication, renaming, or
workspace gitlink changes.
