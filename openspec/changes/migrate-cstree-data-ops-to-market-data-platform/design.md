## Context

`market-data-platform` already owns the major HK data operations surface: RQData HK assets, tick-depth, intraday, PIT/valuation/industry assets, current contracts, dataset registry, health/audit checks, and release workflows. `cross-sectional-trees` has also been moved toward a read-only downstream role, but it still contains platform-delegating modules, compatibility CLI surfaces, and documentation that must be kept consistent.

The remaining work is a boundary hardening change, not a wholesale deletion of every file that mentions data. `cross-sectional-trees` still needs runtime data consumption for research: resolving platform paths, reading local parquet/csv inputs, optional provider-online legacy reads, live allocation price/lot reads, run provenance, and research output packaging.

## Goals / Non-Goals

**Goals:**

- Produce an auditable inventory of remaining `cross-sectional-trees` data operations surfaces.
- Move any remaining non-wrapper data production/check/release logic into `market-data-platform`.
- Keep or convert legacy research-repo entry points into thin wrappers only when downstream compatibility justifies them.
- Update docs so platform docs contain operational runbooks and research docs describe consumption boundaries.
- Add governance tests that catch new platform-owned logic reappearing in `cross-sectional-trees`.

**Non-Goals:**

- Remove research-side data consumption, feature engineering, provider overlay, live allocation market reads, or run provenance.
- Move research reports such as benchmark attribution, intraday slippage analysis, or strategy run packaging to the platform.
- Migrate large local parquet/cache/report artifacts through Git.
- Remove all compatibility wrappers immediately; deletion should follow documented downstream usage and replacement checks.

## Decisions

### Decision: Classify Before Moving

Each candidate surface is classified as one of:

- `platform-owned`: download, mirror, build shared assets, health/audit/coverage, current contract, registry/catalog, data asset backup/release.
- `research-consumer`: path resolution, configured input reads, provider-online research reads, feature/label/model/backtest/position outputs, run provenance, research result packaging.
- `compat-wrapper`: a thin `cross-sectional-trees` surface that delegates to `market-data-platform` for backwards compatibility.

Rationale: simple keyword deletion would remove legitimate research reads and live allocation support. Classification gives reviewers a defensible reason for each retained surface.

Alternative considered: delete all `data_tools` and provider-related modules from `cross-sectional-trees`. That is too risky because current tests and research flows still rely on consumer-side interfaces.

### Decision: Platform Commands Are The Canonical User Interface

Operational docs and examples will prefer `marketdata ...` command families. Legacy commands in `cross-sectional-trees` may remain only as wrappers that import or invoke `market_data_platform`.

Rationale: users need one runbook for data operations, while old callers need a migration path.

Alternative considered: keep duplicate docs in both repos. That increases drift and makes later cleanup harder.

### Decision: Compatibility Is Tracked From The Platform Side

Retained wrappers are listed with replacement command, risk, status, and deletion condition in platform compatibility or migration docs. Wrapper tests live with the wrapper or platform governance tests depending on what they validate.

Rationale: the platform owns the target API and should own the lifecycle plan, while `cross-sectional-trees` tests ensure old imports/commands still delegate correctly.

Alternative considered: leave wrappers undocumented until removal. That hides migration debt and makes it difficult to know whether a wrapper is intentional.

### Decision: Governance Checks Are Narrow And Allowlisted

Static checks should flag new research-repo data operations patterns while allowlisting known wrappers and research consumers. The check should focus on command registration, module names, and prohibited operation verbs near provider/asset/current/release contexts.

Rationale: ownership regression is the main long-term risk. A narrow check is more useful than a broad grep that fails on legitimate research docs and feature names.

Alternative considered: rely only on human review. The codebase already has many similarly named data concepts, so review alone is brittle.

## Risks / Trade-offs

- [Risk] A wrapper is removed while a downstream script still calls it -> Mitigation: keep wrappers until compatibility docs and usage audit show a safe removal point.
- [Risk] Governance checks produce false positives for research consumer code -> Mitigation: classify and allowlist explicit research-consumer modules, then tune checks with tests.
- [Risk] Documentation links drift between repositories -> Mitigation: update cross-repo docs in the same change and run existing docs/path reference tests.
- [Risk] Platform-side commands are missing parity for a retained research wrapper -> Mitigation: do not remove the wrapper until the equivalent `marketdata ...` path is tested.
- [Risk] Provider-online legacy reads are mistaken for data operations -> Mitigation: keep source-mode docs explicit: provider-online reads are opt-in research inputs, not shared asset production.

## Migration Plan

1. Inventory `cross-sectional-trees` data-related modules, CLI entries, scripts, tests, and docs; label each as `platform-owned`, `research-consumer`, or `compat-wrapper`.
2. For every `platform-owned` item still implemented in `cross-sectional-trees`, move the implementation to `market-data-platform` or confirm an existing platform equivalent.
3. Convert retained research-repo entry points to thin delegation wrappers using the existing `_mdp_compat` pattern, or remove them if no compatibility need remains.
4. Update `market-data-platform` docs as the authoritative runbook and reduce `cross-sectional-trees` docs to consumption/sunset notes.
5. Add governance tests/checks and wrapper smoke tests.
6. Run focused tests in both repos plus docs/path checks.

Rollback is straightforward for wrappers and docs: restore the previous wrapper while keeping the platform implementation. Data artifacts are not modified by this change; no artifact rollback is required.

## Open Questions

- Which retained `cross-sectional-trees` wrappers still have real external callers and therefore need a deprecation window?
- Should `cstree data ...` remain indefinitely as a convenience alias, or should it be removed after `marketdata data ...` has stable downstream adoption?
- Should `cstree backup-data` remain a research snapshot helper, or be renamed/documented more narrowly to avoid confusion with platform data asset backup?
