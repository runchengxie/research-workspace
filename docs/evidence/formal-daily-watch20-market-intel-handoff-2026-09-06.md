# Formal DailyWatch20 to `market-intel` handoff evidence

> status: staging-only
> verified: 2026-09-06

This is a synthetic, formal-shaped runtime handoff. It uses the production
publisher's expected `latest/` layout, but it does not use production data,
publish a remote artifact, change a `latest` pointer, or modify any remote.

## Versions

- public `quant-platform`: `fb7ea0e539359b8e0a162066cd827eb55af64f2a`
- private `quant-research`: `e4ebde81a21e4a824b155d588dee9815da6a3a9d`
- `market-intel` consumer validation: `312efa2448ac58e6db9b76cf3b8d3b5130019537`

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

This closes the staging end-to-end producer → contract → consumer gate. It
does not authorize remote repository creation, publication, renaming, or
workspace gitlink changes.
