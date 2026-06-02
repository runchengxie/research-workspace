# Architecture

This workspace coordinates the handoff from data platform to strategy research
to trading execution:

```text
market-data-platform
  produces and publishes data assets
        |
        v
cross-sectional-trees
  consumes data assets and exports targets.json
        |
        v
quant-execution-engine
  parses targets.json, dry-runs, gates risk, and executes under broker controls
```

## Code Boundaries

- Active code: current A-share data, research, and execution flows plus shared
  multi-market contracts.
- Compatibility code: deprecated HK compatibility entrypoints that remain until
  consumer audit, replacement docs, rollback notes, restore evidence, and focused
  tests are complete.
- Archive/provenance: dated handoffs, freeze records, restore drill evidence, and
  historical research context.
- Demo staging: clean-room synthetic public demo under `demo/`, independent from
  the active workspace and not a submodule or release gate.
- Private runtime: provider adapters, broker adapters, credentials, local data roots,
  and execution audit logs. These do not enter the public demo.

## Governance Entrypoints

- Deprecations: [docs/deprecations.md](docs/deprecations.md)
- HK public split: [docs/hk-public-split-manifest.yml](docs/hk-public-split-manifest.yml)
- Script lifecycle: [docs/script-lifecycle.yml](docs/script-lifecycle.yml)
- Quality coverage: [docs/quality-coverage-governance.yml](docs/quality-coverage-governance.yml)
- Refactor roadmap: [docs/maintainability-refactor-roadmap.yml](docs/maintainability-refactor-roadmap.yml)
- Current contracts: [docs/contracts.md](docs/contracts.md)
