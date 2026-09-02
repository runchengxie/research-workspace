# Platform asset registry

The platform asset registry is the machine-readable alternative to creating another Git superproject around `research-workspace`, `market-intel`, and `trading-research-dashboard`.

It describes logical assets independently from repository nesting:

```text
market.a_share_daily_clean
  -> features.dailywatch20.v17
  -> signals.dailywatch20
  -> publication.dashboard
  -> report.morning
```

Each asset records:

- stable asset id;
- owner repository;
- output schema version;
- internal asset dependencies;
- external inputs;
- declared consumers;
- a small freshness policy (`none`, `market_days`, `calendar_hours`);
- optional description.

`PlatformAssetRegistry` validates missing dependencies and dependency cycles and provides a deterministic topological order. It does not clone repositories, run jobs, or become a second orchestration engine.

This lets platform-level docs and tooling answer questions such as:

- which owner produces a broken artifact;
- which downstream surfaces depend on it;
- what should be refreshed first;
- which schema/freshness contract applies;

The registry complements the platform-publication contract. Asset definitions describe the logical dependency graph; publication manifests describe one concrete produced handoff.
