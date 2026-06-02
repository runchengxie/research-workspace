# Deprecations

This register tracks deprecated compatibility surfaces that remain in active
repositories. It does not authorize deletion by itself; removal requires the
evidence listed in [`deprecations.yml`](deprecations.yml) and the split gates in
[`hk-public-split-manifest.yml`](hk-public-split-manifest.yml).

## Current Records

| Entrypoint | Owner | Replacement | Status | Target milestone |
| --- | --- | --- | --- | --- |
| `hkdata` | `market-data-platform` | `marketdata` | blocked pending audit | two releases after zero usage |
| `src/hk_data_platform/*` | `market-data-platform` | `market_data_platform` public modules | blocked pending audit | two releases after clean import audit |
| `rqdata-hk-depth` | `market-data-platform` | `marketdata rqdata hk-depth -- ...` | blocked pending audit | two releases after migration guide |
| `rqdata-tick` | `market-data-platform` | `marketdata rqdata hk-depth -- ...` | blocked pending audit | two releases after migration guide |
| `rqdata-hk-assets` | `market-data-platform` | `marketdata rqdata hk-assets -- ...` | blocked pending audit | two releases after migration guide |
| `cstree alloc-hk` | `cross-sectional-trees` | `cstree alloc` plus `cstree export-targets` | blocked pending audit | after restore drill and consumer audit |
| HK historical configs | `cross-sectional-trees` | `configs/presets/hk.yml` plus archive evidence | follow-up required | after archive manifest remains current |

## Removal Gate

Do not mark a deprecation as removal-ready unless all required evidence exists:

- downstream or repo-local consumer audit;
- replacement documentation;
- rollback path;
- focused tests in the owning repository;
- restore evidence when the surface is restore-sensitive.

Actual deletion must happen in a follow-up change with focused verification in
the owning repo.
