# Repository parity inventory

> status: initial audit
> verified: 2026-09-06
> authority: legacy submodules remain authoritative until each row reaches parity

This inventory compares the current repositories with the target architecture.
“Partial” means a validated migration slice exists; it does not mean the
legacy repository can be retired.

| Legacy repository | Target | Code | Tests/CI | Docs/config | Current migration state | Main missing work |
| --- | --- | --- | --- | --- | --- | --- |
| `market-data-platform` | `quant-platform/data` + private providers | not migrated | legacy only | legacy only | not started | split reusable data mechanisms from providers, credentials, datasets, and runtime configuration |
| `deep-learning-tick-data-prediction` | `quant-platform/microstructure` + `quant-research/microstructure` | not migrated | legacy only | legacy only | not started | separate generic event/model abstractions from proprietary labels, experiments, configs, and results |
| `alpha-research` | `quant-platform/alpha` + private feature selections | not migrated | legacy only | legacy only | not started | classify reusable research machinery versus edge-bearing features, labels, and model choices |
| `portfolio-backtester` | `quant-platform/portfolio` | partial | public staging green (`31 passed`) | public slice documented | validated vertical slice | transfer remaining portfolio modules, APIs, docs, and release compatibility |
| `strategy-research` | `quant-research/registry` and `research` | DailyWatch20 parity complete locally | local full slice tests green (`122 passed`); remote CI dependency access pending | DailyWatch20 slice documented | DailyWatch20 slice migrated | transfer all remaining strategy identities, evidence, experiments, and lifecycle records |
| `strategy-app` | `quant-research/strategies` | DailyWatch20 parity complete locally | local full slice tests green (`122 passed`); remote CI dependency access pending | DailyWatch20 slice documented | DailyWatch20 slice migrated | transfer remaining strategy logic, specs, tests, and runtime dependencies |
| `strategy-pipeline` | `quant-platform/orchestration` + private adapters | partial | legacy and staged checks exist | publication boundary documented | generic handoff slice validated | transfer the full control plane, run manifests, publication, and compatibility behavior |
| `quant-execution-engine` | `quant-platform/execution` + private runtime | not migrated | legacy only | legacy only | not started | split public interfaces from broker adapters, credentials, audit runtime, and live configuration |
| `market-intel` | `market-intel` | boundary complete locally | boundary `2 passed`; consumer gate `112 passed` | artifact boundary documented | locally integrated, not pushed | push approved boundary commit and validate against the first real migrated publication |
| `research-workspace` | `research-workspace` thin layer | governance partial | doctor/architecture gates green | target architecture documented | legacy submodules still authoritative | update manifest only after parity and consumer gates; remove submodules only after rollback window |

## Release-readiness gaps

The new repositories are published, but they are not yet full replacements:

- `quant-platform` still needs an explicit licensing decision before being
  described as an open-source release.
- `quant-research` has no complete strategy-family parity audit yet.
- `market-intel`'s validated boundary commit is local; the remote branch still
  points to the previous commit.
- The workspace version manifest intentionally reports
  `consumer-cutover-pending`.
- Old repositories have not received deprecation notices, because they remain
  the rollback and authoritative sources.

## First cutover slice

The first slice is `DailyWatch20`:

```text
quant-research strategy registry + strategy logic
        ↓ private publication adapter
research.platform-publication.v1
        ↓ hash/audience/path verification
market-intel consumer
```

Before calling this slice complete, the next audit must compare the legacy
DailyWatch20 publisher against the private staging implementation for:

- source files and imports;
- strategy specifications and configuration;
- tests and expected artifacts;
- publication and receipt fields;
- runtime dependencies and CLI entry points;
- documentation and rollback instructions.

Only after that comparison passes should the workspace manifest or production
consumer be switched to the new repositories.
