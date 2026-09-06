# Private publication adapter evidence

> status: staging-only
> verified: 2026-09-06

The private staging repository `quant-research` is committed at
`12f80ebb1bfa42820112a78be298b3dbefa74b92`. Its `scripts/export_publication.py` adapter depends on
the public staging repository `quant-platform` at
`95abd65a04b370e947728e46f91e173aa5165187`.

The adapter accepts exactly these private projections from the formal publisher's `latest`
directory:

- `strategies/daily_watch20/watchlist_20.csv`
- `strategies/daily_watch20/selection_receipt.json`

It creates a `research.platform-publication.v1` bundle with `audience: internal` and
`consumers: ["market-intel"]`. The manifest contains the producer repository and commit, but no
local source paths. Focused verification:

```bash
uv run --extra dev pytest -q tests/test_export_publication.py
uv run ruff check scripts tests/test_export_publication.py
```

Result: `3 passed`; Ruff clean. This proves the target namespace and private-to-application handoff
shape, including the formal `latest` layout, but it is not yet a full runtime migration because the
copied private suite still has an older `portfolio-backtester` API pin.
