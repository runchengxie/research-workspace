## 1. Inventory And Classification

- [x] 1.1 Build an inventory of `cross-sectional-trees` modules, CLI commands, scripts, tests, and docs that mention data download, mirroring, health checks, current contracts, registries, universe asset builders, backup, package, or release workflows.
- [x] 1.2 Classify each inventory item as `platform-owned`, `research-consumer`, or `compat-wrapper`, and record the reason for retained research-side items.
- [x] 1.3 Map each `platform-owned` item to an existing or required `market-data-platform` command/module.
- [x] 1.4 Identify retained compatibility wrappers and document downstream usage assumptions or deletion conditions.

## 2. Code Boundary Cleanup

- [x] 2.1 Move any remaining non-wrapper data production, health, current-refresh, registry, or data-asset release implementation from `cross-sectional-trees` into `market-data-platform`.
- [x] 2.2 Convert retained `cross-sectional-trees` data operations entry points into thin `_mdp_compat` delegating wrappers.
- [x] 2.3 Remove stale research-repo data operations imports, command registrations, scripts, and tests that no longer have a compatibility purpose.
- [x] 2.4 Preserve research-consumer behavior for platform asset reads, provider-online legacy reads, provider overlays, live allocation market reads, run provenance, and research result packaging.
- [x] 2.5 Add or update wrapper smoke tests to prove retained compatibility entry points call platform modules and fail clearly when the platform package is missing.

## 3. Documentation Realignment

- [x] 3.1 Update `market-data-platform` docs so HK/CN data operations, health checks, current contracts, registries, standardized layers, universe assets, and release workflows are documented as platform-owned.
- [x] 3.2 Reduce `cross-sectional-trees` data asset runbooks to consumption guidance, sunset notes, and links or command names for platform-native workflows.
- [x] 3.3 Update top-level `research-workspace` docs where they describe the market-data-to-research workflow and module responsibilities.
- [x] 3.4 Ensure research docs still explain valid consumption modes: `platform_assets`, explicit `provider_online_legacy`, local PIT/standardized files, and current-contract provenance.
- [x] 3.5 Update compatibility or migration docs with wrapper replacement commands, risks, current status, and removal criteria.

## 4. Governance And Regression Checks

- [x] 4.1 Add a static governance check or tests that flag new `cross-sectional-trees` data-production, health-check, current-refresh, registry, or data-asset release implementations unless they are explicit platform-delegating wrappers.
- [x] 4.2 Add documentation regression coverage or review fixtures for research docs that incorrectly describe platform-owned operations as research-owned.
- [x] 4.3 Add allowlists for legitimate research-consumer modules and tests that prove the allowlists do not mask platform-owned command additions.
- [x] 4.4 Wire the new checks into the existing focused test or developer-check workflow for the affected repo.

## 5. Verification

- [x] 5.1 Run focused `cross-sectional-trees` tests for docs, path references, CLI wrappers, data interface behavior, and any changed research-consumer modules.
- [x] 5.2 Run focused `market-data-platform` tests for affected commands, compatibility governance, architecture governance, and docs/path references.
- [x] 5.3 Run top-level workspace smoke or docs checks if workspace documentation changed.
- [x] 5.4 Manually verify that documented data lifecycle commands resolve to platform entry points and that research runs still point users to platform assets by default.
- [x] 5.5 Record any remaining deferred wrappers or open questions in the relevant compatibility documentation.
