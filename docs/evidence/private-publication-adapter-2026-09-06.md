# Private publication adapter evidence

> status: staging-only
> verified: 2026-09-06

The private staging repository `quant-research` is committed at
`e4ebde81a21e4a824b155d588dee9815da6a3a9d`. Its `scripts/export_publication.py` adapter depends on
the public staging repository `quant-platform` at
`fb7ea0e539359b8e0a162066cd827eb55af64f2a`.

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
shape, including the formal `latest` layout. The full copied private suite also passes (`26 passed`)
against the staged public platform and contract packages. The resulting formal-shaped bundle was
also accepted by the actual `market-intel` verifier; see
`formal-daily-watch20-market-intel-handoff-2026-09-06.md`.
