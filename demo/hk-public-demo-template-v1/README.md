# Archived HK Cross-Sectional Strategy Demo

Paused-maintenance engineering portfolio demo for a small synthetic China
Hong Kong market cross-sectional workflow.

This repository is a clean-room public snapshot extracted from a larger private
research workspace. The active workspace has moved toward A-share
data/research/execution work; this HK demo remains as a frozen public reference
and is not an active trading or research lane.

This public demo is intentionally narrow:

- It uses synthetic prices only.
- It does not contain licensed market data, provider credentials, private
  research outputs, broker integration, or production performance claims.
- It demonstrates a reproducible offline flow from synthetic prices to a
  summary and a standard `targets.json` handoff file.

Run the demo:

```bash
python scripts/run_demo.py --out-dir samples
python -m unittest discover -s tests -v
```

The generated files are:

```text
samples/summary.json
samples/targets.json
```

See [docs/architecture.md](docs/architecture.md) for the small workflow map.

## Relationship To Active Work

The active private workspace continues to maintain data-platform, research, and
execution boundaries for A-share work. This public repository is independent of
that workspace and is not used as a submodule, dependency, CI target, release
input, or source of production data.

## Intentionally Omitted

- Licensed market data and data-provider adapters.
- Real universe membership, historical research output, and production
  performance claims.
- Broker integration, live-trading code, and execution audit logs.
- Local machine paths, private artifacts, and credential material.

## Disclaimer

This repository is an engineering portfolio demo, not investment advice. It
must not be used for live trading without independent data, research,
execution, and risk validation.
