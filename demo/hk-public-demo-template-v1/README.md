# Archived HK Cross-Sectional Strategy Demo

Historical reference implementation for a small China Hong Kong market
cross-sectional workflow. Maintenance is paused.

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

## Disclaimer

This repository is an engineering portfolio demo, not investment advice. It
must not be used for live trading without independent data, research,
execution, and risk validation.
