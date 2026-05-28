## Why

`market-data-platform` has absorbed substantial migrated code, but its static checks currently exclude many of the highest-risk modules and compatibility surfaces remain open-ended. This change makes maintenance debt explicit and enforceable so the project can move from individual-owner maintenance toward team-safe evolution without attempting a disruptive all-at-once rewrite.

## What Changes

- Add quality governance for Ruff/Pyright coverage so configured checks cannot stay green by silently excluding core business code.
- Add non-blocking debt reporting for complexity and typing debt, with stable baselines that make regressions visible before they become CI-breaking.
- Define a lifecycle for compatibility layers and migration-only commands, including audit, deprecation, documentation, and removal criteria.
- Introduce maintainability boundaries for oversized files/functions, public API exports, and command/workflow coupling.
- Prioritize incremental refactors for high-risk areas such as `hk_assets`, `hk_depth/downloader.py`, and `release_tools` workflows, without changing data contracts or release outputs.
- Keep legacy entry points functional during the first implementation phase unless repo-local/downstream usage has been audited and removal is explicitly scheduled.

## Capabilities

### New Capabilities

- `static-quality-governance`: Defines truthful Ruff/Pyright coverage reporting, debt baselines, and regression prevention for static quality checks.
- `compatibility-lifecycle`: Defines how migration commands, old package names, provider re-export modules, and legacy console scripts are audited, deprecated, documented, and removed.
- `maintainability-boundaries`: Defines file/function size budgets, public API boundaries, and architecture checks that reduce coupling across CLI, provider, workflow, validation, persistence, and reporting code.

### Modified Capabilities

- None.

## Impact

- Affected project: `market-data-platform`.
- Affected configuration: `pyproject.toml`, static-check settings, and any CI or developer commands that run Ruff, Pyright, tests, or debt reporting.
- Affected tooling: `scripts/dev/quality_debt.py` and related developer documentation in `docs/`.
- Affected compatibility surfaces: `hk_data_platform.*`, `market_data_platform.rqdata_cn`, `market_data_platform.tushare_cn`, migration CLI commands, legacy console scripts, and release presets.
- Affected high-risk implementation areas: `src/market_data_platform/hk_assets`, `src/market_data_platform/hk_depth`, `src/market_data_platform/release_tools`, and `src/market_data_platform/cli.py`.
- No intended change to published asset schemas, existing artifact layouts, provider credentials, or RQData/TuShare runtime behavior in the initial governance phase.
