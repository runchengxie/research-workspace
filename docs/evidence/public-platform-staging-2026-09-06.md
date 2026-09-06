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
primitives. It is committed at `95abd65` (`refactor: keep contracts as dedicated public package`).

It includes a public CI workflow, a public `portfolio-backtester` package slice, a versioned
style-factor backtest contract, generic `quant_platform` publication helpers, synthetic example
data, and migration provenance. The handoff API owns the `quant_platform` namespace. The public
staging tree also contains the complete `research-contracts` package under
`packages/research-contracts/`, including `ArtifactEnvelopeV2`, as the intended shared contract
owner; it is deliberately not duplicated inside the portfolio package namespace.

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
