# quant-platform local migration prototype

This ordinary directory is a local staging tree inside `research-workspace`. It is not a separate Git
repository, has not been pushed or published, and must not be represented as a remotely available
`quant-platform` repository.

The prototype migrates one public vertical slice from `portfolio-backtester`: the standalone
`portfolio_backtester.style_factors_backtest` quantile-portfolio kernel, a deterministic synthetic
CSV example, the `portfolio-style-factor` CLI, and the versioned
`portfolio_backtester.style_factor_backtest.v1` JSON artifact contract. It deliberately excludes
data providers, alpha generation, real strategy inputs, orchestration, and execution runtime.

The source checkout at commit `91a4fa4f1d57c074c991546c381a3d90a3b6adfb` remains the rollback source.
The Python namespace is unchanged. The source repository contains no `LICENSE` or `LICENSE.md`, so
this staging tree intentionally adds no license and is not ready for public distribution until the
owner makes an explicit licensing decision.

Run locally:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run pytest
uv run portfolio-style-factor \
  --input examples/synthetic-style-factor.csv \
  --output /tmp/style-factor-report.json \
  --signal size \
  --quantiles 2
```
