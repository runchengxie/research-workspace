# Repository parity inventory

> status: maintained audit; portfolio parity complete, remaining owners pending
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
| `portfolio-backtester` | `quant-platform/portfolio` | complete for current legacy baseline | public CI green at `507628e` (`586 passed`) | full transferred docs/config/scripts | parity-complete public portfolio package | retain `91a4fa4` as rollback authority; do not retire legacy source yet |
| `strategy-research` | `quant-research/registry` and `research` | DailyWatch20 parity complete locally | local full slice tests green (`122 passed`); remote CI dependency access pending | DailyWatch20 slice documented | DailyWatch20 slice migrated | transfer all remaining strategy identities, evidence, experiments, and lifecycle records |
| `strategy-app` | `quant-research/strategies` | DailyWatch20 parity complete locally | local full slice tests green (`122 passed`); remote CI dependency access pending | DailyWatch20 slice documented | DailyWatch20 slice migrated | transfer remaining strategy logic, specs, tests, and runtime dependencies |
| `strategy-pipeline` | `quant-platform/orchestration` + private adapters | partial | legacy and staged checks exist | publication boundary documented | generic handoff slice validated | transfer the full control plane, run manifests, publication, and compatibility behavior |
| `quant-execution-engine` | `quant-platform/execution` + private runtime | not migrated | legacy only | legacy only | not started | split public interfaces from broker adapters, credentials, audit runtime, and live configuration |
| `market-intel` | `market-intel` | boundary complete | boundary `2 passed`; consumer gate `112 passed`; remote CI green | artifact boundary documented | pushed at `83172a3` | validate a production-shaped migrated publication before cutover |
| `research-workspace` | `research-workspace` thin layer | governance partial | doctor/architecture gates green | target architecture documented | legacy submodules still authoritative | update manifest only after parity and consumer gates; remove submodules only after rollback window |

## Repository-by-repository evidence matrix

Counts below are from the pinned legacy commits in the first column. They are
an inventory baseline, not a claim that every file should move unchanged. A
target marked `slice` has only the validated DailyWatch20/public-platform
portion migrated; `pending` means no target parity has been established.

| Repository | Code baseline | Tests baseline | Docs baseline | Config baseline | CI baseline | Runtime dependencies | Target evidence / rollback |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `market-data-platform` | 290 `src` files | 110 | 50 | `pyproject.toml`, `uv.lock`, provider/data config | 1 workflow | NumPy, PyYAML, research quality; private data/provider runtime | `quant-platform/data` pending; keep commit `0f1c4ce` |
| `deep-learning-tick-data-prediction` | 99 | 88 | 59 | `pyproject.toml`, `uv.lock`, model/config corpus | 2 workflows | LightGBM, Torch, Polars, PyArrow, scikit-learn | microstructure split pending; keep commit `2dd4701` |
| `alpha-research` | 155 | 84 | 33 | `pyproject.toml`, `uv.lock`, research-contract source pin | 3 workflows | NumPy, Pandas, XGBoost, research contracts | alpha split pending; keep commit `631ee15` |
| `portfolio-backtester` | 163 | 97 | 40 | `pyproject.toml`, `uv.lock`, public package metadata | public workflow green at `507628e` | NumPy, Pandas, PyArrow, SciPy, scikit-learn, XGBoost, research contracts, pinned public quality tooling | `quant-platform` commit `507628e`; keep legacy commit `91a4fa4` |
| `strategy-research` | 65 `src` files plus research records | 94 | 37 | `pyproject.toml`, `uv.lock`, catalog/evidence/config records | 2 workflows | alpha, market data, portfolio, strategy app, contracts | DailyWatch20 local/remote parity; private rollback commit `087b5df` |
| `strategy-app` | 186 `src` files | 78 | 50 | `pyproject.toml`, `uv.lock`, campaign specs/runtime config | 1 workflow | alpha, market data, portfolio, pipeline, scientific stack | DailyWatch20 local/remote parity; private rollback commit `f6f58bf` |
| `strategy-pipeline` | 26 | 25 | 24 | `pyproject.toml`, `uv.lock`, run/publication configs | 2 workflows | alpha, market data, portfolio, NumPy, Pandas, YAML | generic publication slice only; keep commit `87175c6` |
| `quant-execution-engine` | 88 | 40 | 31 | `pyproject.toml`, `uv.lock`, broker/runtime config | 2 workflows | PyYAML plus broker/runtime environment | execution split pending; keep commit `2f0675a` |
| `market-intel` | independent application | local consumer 112 + boundary 2; remote CI green | boundary and consumer docs | own `pyproject.toml`, workflows, deployment config | public CI green on 3 Python versions | public contracts plus deployment/data environment | boundary pushed at `83172a3`; unrelated local changes preserved |
| `research-workspace` | governance/scripts plus submodule gitlinks | doctor, architecture, contract, root gates | architecture, ADR, migration docs | `.gitmodules`, manifests, architecture model | root pre-push gate | legacy submodule pins and local production environment | audit branch `05bc7f7`; gitlinks unchanged |

### Dependency and CI interpretation

- The private DailyWatch20 slice is locally reproducible against the pinned
  public platform and private data dependency, but its GitHub Actions job needs
  approved read access to `market-data-platform`.
- The public platform is still not a complete replacement for the eight legacy
  owners, but the portfolio-backtester baseline itself is now transferred with
  source, tests, docs, scripts, dependency lock, and CI evidence.
- The independent `market-intel` CI proves consumer packaging and boundary
  behavior, not that production data has been switched to the new producer.
- Every pending row retains a concrete legacy commit so rollback does not rely
  on an unpinned branch or an archived repository.

## Release-readiness gaps

The new repositories are published, but they are not yet full replacements:

- `quant-platform` has Apache-2.0 licensing for the public framework contents;
  proprietary research remains outside this repository.
- `quant-research` has no complete strategy-family parity audit yet.
- `market-intel`'s boundary commit is pushed and remotely green, but production
  still consumes the legacy producer path.
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

The local parity audit has compared the legacy DailyWatch20 publisher against
the private staging implementation for:

- source files and imports;
- strategy specifications and configuration;
- tests and expected artifacts;
- publication and receipt fields;
- runtime dependencies and CLI entry points;
- documentation and rollback instructions.

The remaining slice gates are remote private CI access, a production-shaped
consumer run using the new producer, a license decision for the public
platform, and a defined rollback window.

Only after that comparison passes should the workspace manifest or production
consumer be switched to the new repositories.
