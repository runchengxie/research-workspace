# Repository parity inventory

> status: maintained audit; portfolio parity complete, remaining owners pending
> verified: 2026-09-06
> authority: legacy submodules remain authoritative until each row reaches parity

This inventory compares the current repositories with the target architecture.
`Partial` means a validated migration slice exists; it does not mean the
legacy repository can be retired.

| Legacy repository | Target | Code | Tests/CI | Docs/config | Current migration state | Main missing work |
| --- | --- | --- | --- | --- | --- | --- |
| `market-data-platform` | `quant-platform/data` + private providers | private baseline complete; public contract/core/quality slice transferred | private transfer CI green at `34021009249`; public CI green at `34020846558` | 290 source files, 110 tests/fixtures, 50 docs, 44 scripts transferred privately | private baseline migrated and private consumers repinned; public-safe core and deterministic quality tools validated | complete consumer integration before cutover; keep providers private |
| `deep-learning-tick-data-prediction` | `quant-platform/microstructure` + `quant-research/microstructure` | private baseline plus public generic framework transferred | private CI green at `34023679429`; public CI queued at `34024056490` | private 99 source files/88 tests/59 docs; public 26 source files/10 tests/3 docs | public synthetic suite `45 passed`; private research corpus preserved | finish public CI confirmation and keep real-data labels, experiments, configs, and results private |
| `alpha-research` | `quant-platform/alpha` + private feature selections | public framework and private edge split transferred | public local full suite includes 70 alpha tests; private alpha suite `84 passed` | public 135 source files/31 docs; private baseline retains 155 source files and 84 tests | public edge review completed; CI rerun pending | preserve private DailyWatch20/Hotsector modules and finish private strategy-family audit |
| `portfolio-backtester` | `quant-platform/portfolio` | complete for current legacy baseline | public CI green at `507628e` (`586 passed`) | full transferred docs/config/scripts | parity-complete public portfolio package | retain `91a4fa4` as rollback authority; do not retire legacy source yet |
| `strategy-research` | `quant-research/registry` and `research` | DailyWatch20 parity complete locally | local full slice tests green (`122 passed`); remote CI dependency access pending | DailyWatch20 slice documented | DailyWatch20 slice migrated | transfer all remaining strategy identities, evidence, experiments, and lifecycle records |
| `strategy-app` | `quant-research/strategies` | DailyWatch20 parity complete locally | local full slice tests green (`122 passed`); remote CI dependency access pending | DailyWatch20 slice documented | DailyWatch20 slice migrated | transfer remaining strategy logic, specs, tests, and runtime dependencies |
| `strategy-pipeline` | `quant-platform/orchestration` + private adapters | public control-plane slice transferred | public orchestration tests and full suite pass locally; remote CI rerun pending | 27 source files, 28 tests, 25 docs; parity manifest added | reusable CLI/publication/control-plane behavior transferred | finish private strategy adapters and confirm remote CI |
| `quant-execution-engine` | `quant-platform/execution` + private runtime | public interface foundation transferred | 5 public test files and full suite pass locally | 67 public source files and execution README; broker adapters/runtime remain private | public foundation validated | transfer private broker adapters, credentials boundary, audit runtime, and live configuration |
| `market-intel` | `market-intel` | boundary complete | boundary `2 passed`; consumer gate `112 passed`; remote CI green | artifact boundary documented | pushed at `83172a3` | validate a production-shaped migrated publication before cutover |
| `research-workspace` | `research-workspace` thin layer | governance partial | doctor/architecture gates green | target architecture documented | legacy submodules still authoritative | update manifest only after parity and consumer gates; remove submodules only after rollback window |

## Repository-by-repository evidence matrix

Counts below are from the pinned legacy commits in the first column. They are
an inventory baseline, not a claim that every file should move unchanged. A
target marked `slice` has only the validated DailyWatch20/public-platform
portion migrated; `pending` means no target parity has been established.

| Repository | Code baseline | Tests baseline | Docs baseline | Config baseline | CI baseline | Runtime dependencies | Target evidence / rollback |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `market-data-platform` | 290 `src` files | 110 | 50 | `pyproject.toml`, `uv.lock`, provider/data config | private transfer job green at `34021009249`; public core/quality job green at `34020846558` | NumPy, PyYAML, DuckDB, Pandas, Polars, PyArrow, research quality; private data/provider runtime | private `quant-research` commit `5971d8b`; public `quant-platform` commit `bb4c9a3`; keep legacy `0f1c4ce` |
| `deep-learning-tick-data-prediction` | 99 | 88 | 59 | `pyproject.toml`, `uv.lock`, model/config corpus | private `microstructure-transfer` job added; remote result pending | LightGBM, Torch, Polars, PyArrow, scikit-learn | private `quant-research` commit `e5e702c`; keep legacy commit `2dd4701` |
| `alpha-research` | 155 | 84 | 33 | `pyproject.toml`, `uv.lock`, research-contract source pin | private `alpha-transfer` job added; remote result pending | NumPy, Pandas, XGBoost, research contracts, optional Qlib | private `quant-research` commit `6350f67`; keep legacy commit `631ee15` |
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
- The pinned market-data baseline is now present privately with its original
  namespace. Public `quant-platform` contains only the credential-free,
  deterministic contract/core subset and has a separate boundary test.
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
