## Why

`cross-sectional-trees` has already moved much of its HK data lifecycle surface to `market-data-platform`, but the research repo still contains compatibility wrappers, data-platform-facing docs, and provider/data-check references that make ownership harder to audit. This change finishes the boundary cleanup so data download, mirroring, health checks, current contracts, registry, and asset release logic have one source of truth in `market-data-platform`.

## What Changes

- Audit `cross-sectional-trees` for remaining data operations surfaces: download/mirror commands, HK asset checks, current contract refresh, registry/catalog generation, universe asset builders, backup/release flows, and docs that describe those as research-owned.
- Migrate or confirm ownership of data production and validation logic in `market-data-platform`, including any remaining wrappers around HK intraday, daily assets, PIT/valuation/industry assets, standardized layers, universe assets, current contracts, health reports, and dataset registries.
- Narrow `cross-sectional-trees` to research-side consumption: resolving platform asset paths, reading local files or explicit provider-online legacy inputs, creating features/labels/backtests/positions, and preserving run provenance.
- Replace research-repo operational runbooks with short sunset/compatibility notes that point to platform-native commands and docs.
- Add or update tests and governance checks that prevent new data-production commands from being added under `cross-sectional-trees`.
- Keep temporary compatibility wrappers only where they protect downstream callers, and document removal criteria in `market-data-platform` compatibility docs.
- **BREAKING**: any remaining non-wrapper `cross-sectional-trees` data asset maintenance command, if found, is removed or converted to a platform-owned command. Research workflows must call `marketdata ...` or platform modules for data lifecycle operations.

## Capabilities

### New Capabilities
- `market-data-ops-ownership`: Defines the ownership boundary for market data production, validation, current-contract, registry, and release workflows across `cross-sectional-trees` and `market-data-platform`.

### Modified Capabilities
- None.

## Impact

- Affected repositories: `cross-sectional-trees`, `market-data-platform`, and the top-level `research-workspace` documentation where it describes module responsibilities.
- Affected code areas: `cross-sectional-trees/src/cstree/{cli,data_tools,research,current_assets,data_providers,data_provider_contracts,intraday_paths,artifacts,repo_paths}.py`, `cross-sectional-trees/docs/**`, `cross-sectional-trees/scripts/README.md`, and platform-side `market_data_platform` HK assets, data warehouse, backup, current contract, and compatibility surfaces.
- Affected user workflows: HK data refresh, health/audit checks, current contract refresh, dataset registry/catalog work, universe asset generation, intraday asset maintenance, and downstream research runs that consume platform assets.
- Dependencies: `cross-sectional-trees` continues depending on `market-data-platform`; optional `rqdata` remains only for explicit provider-online research reads and live allocation needs, not for default data asset maintenance.
