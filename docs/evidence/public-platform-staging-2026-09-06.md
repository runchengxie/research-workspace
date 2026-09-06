# Public `quant-platform` staging evidence

> status: staging-only
> verified: 2026-09-06
> source_of_truth: migration rehearsal evidence

## Result

A separate local Git staging repository now exists at:

```text
/home/richard/code/.public-staging/quant-platform
```

The repository contains the public portfolio/backtesting vertical slice and generic publication
primitives. It is committed at `29e114e` (`feat: add public publication bundle primitives`).

It includes a public CI workflow, a public `portfolio-backtester` package slice, a versioned
style-factor backtest contract, generic `research_contracts` publication helpers, synthetic example
data, and migration provenance.

## Verification

Run from the staging repository root:

```bash
uv run pytest -q
uv run ruff check .
```

Result: `31 passed`; Ruff reported `All checks passed!`.

A restricted-file scan found no credentials, environment files, raw parquet/feather data, secrets,
or runtime artifact directories. No GitHub remote was created, nothing was pushed, and the
workspace gitlinks were not changed.

## Release limitation

This is not yet a public release. The staging tree still requires an explicit licensing decision,
stable package/repository naming, and a clean-root export review before remote creation.
