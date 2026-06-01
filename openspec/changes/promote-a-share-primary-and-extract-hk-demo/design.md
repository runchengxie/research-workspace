## Context

The workspace coordinates three repositories with distinct ownership:

- `market-data-platform` produces and validates shared market-data assets.
- `cross-sectional-trees` consumes published assets, runs research, and exports standard execution targets.
- `quant-execution-engine` parses `targets.json`, builds dry-run plans, applies broker-specific controls, and owns any future order submission path.

The A-share data platform is beyond an empty scaffold. The active contract at `metadata/current_assets/a_share_current.json` points to TuShare assets through `2026-05-29`, including raw daily data, adjustment factors, daily valuation metrics, limit status, `daily_clean`, and a monthly by-date full-market universe. The current `cross-sectional-trees` candidate does not yet consume that by-date universe: `configs/presets/a_share.yml` still declares `research_universe.mode: static`, lists ten symbols, and asks for data from `2015-01-01` even though the published daily-clean window starts on `2024-01-02`.

The historical HK lane has already been frozen at the data and research-output layers. Both freeze markers record remote release restoration prerequisites because the local cold snapshots have been removed. HK code remains large because it includes research history in `cross-sectional-trees` and data production, depth, and release workflows in `market-data-platform`. That code cannot be deleted as one block: some of it is historical research material, some is restore support, and some is valid multi-market execution behavior.

`cross-sectional-trees` already has market-agnostic research evidence tools: `promotion-gate`, `cpcv`, `benchmark-ladder`, and `feature-evidence`. The A-share migration should reuse them with A-share-specific assets and policies.

## Goals / Non-Goals

**Goals:**

- Establish testable readiness levels for an A-share reproducible baseline, an A-share promoted research default, and the separately governed broker-trading boundary.
- Make the promoted A-share default consume point-in-time inputs with declared provenance and a data window consistent with published assets.
- Reuse existing generic research evidence tools for A-share benchmark, walk-forward, CPCV, feature, and promotion evidence.
- Preserve only intentionally supported HK restore, compatibility, and multi-market surfaces in active repositories.
- Produce a separate, clean-room HK public demo export that is runnable without licensed provider data and does not become an active workspace dependency.

**Non-Goals:**

- Claim or enable unattended A-share broker order submission.
- Delete HK data-platform restore support before a restore drill and dependency retirement audit.
- Copy private market data, provider caches, private research outputs, credentials, or original Git history into a public repository.
- Require the HK public demo to track future A-share framework changes.
- Treat daily valuation overlays as point-in-time financial statement data.

## Decisions

### 1. Use three readiness levels instead of one ambiguous "formal run" label

The workspace SHALL report:

1. `baseline_reproducible`: A-share contract, registry, daily-clean validation, by-date universe validation, candidate research output, target export lineage, and execution dry-run evidence exist.
2. `research_default_promotable`: the baseline passes and the candidate additionally uses point-in-time universe, point-in-time fundamentals where fundamental features are enabled, historical industry semantics where industry features or constraints are enabled, A-share benchmark evidence, side-aware trading semantics, and research promotion evidence.
3. `broker_trading_enabled`: a separate execution-owned state requiring an explicitly supported broker adapter, account permissions, supervised smoke evidence, and operational approval.

The top-level workspace gate will aggregate machine-readable evidence from existing repository commands and artifacts. It will report missing or failed evidence without starting heavyweight downloads, model training, or broker submission.

Alternative considered: change `default` as soon as `daily_clean` runs. Rejected because it collapses data availability, research credibility, and broker execution into one misleading status.

### 2. Keep data production and data semantics in `market-data-platform`

The data platform remains authoritative for:

- `metadata/current_assets/a_share_current.json`
- `metadata/dataset_registry.csv`
- `daily_clean` validation
- by-date universe assets and provenance
- future point-in-time fundamentals assets
- future historical industry assets

The A-share current contract will expose the asset keys needed by the promoted default and their manifest summaries. A promoted config must use an effective date range covered by its published assets. The initial active window may remain medium-length; expanding history is a separate data operation after the contract and research semantics are stable.

Alternative considered: assemble A-share financial and industry overlays inside `cross-sectional-trees`. Rejected because it would recreate the data-ops split that the workspace has already removed from the HK research repository.

### 3. Reuse the existing generic research evidence tools

`cross-sectional-trees` will add A-share presets and report configs for:

- benchmark ladder
- feature evidence
- walk-forward evidence
- CPCV audit for shortlisted candidates
- promotion gate

The migration does not require every exploratory run to execute CPCV. CPCV remains a shortlist audit, and the final promotion bundle records the selected evidence.

Alternative considered: create A-share-only promotion scripts. Rejected because the existing tools are already generic and duplicating them would increase maintenance debt.

### 4. Replace coarse tradability filtering with explicit A-share side semantics

The research and dry-run evidence must distinguish buy and sell constraints:

- limit-up blocks buys
- limit-down blocks sells
- suspended holdings cannot be assumed sellable
- T+1 availability must be represented or explicitly approximated
- ST, listing-age, board-lot, and board-specific rules must be recorded

The research layer documents simulation assumptions. The execution engine remains responsible for any broker-side enforcement once a real A-share broker project exists.

Alternative considered: drop every limit-up and limit-down row before modeling and call the strategy executable. Rejected because it hides asymmetric execution risk and can overstate realizable turnover.

### 5. Promote `default` only through an explicit alias switch

`default_next` remains the stable migration candidate while evidence is incomplete. Once `research_default_promotable` passes, `default.yml` will resolve to the promoted A-share preset and the named `hk.yml` preset will remain the HK compatibility entry.

The default switch is intentionally breaking and must update docs, catalog lifecycle fields, focused tests, and release notes together. Rollback is an alias change, not a restoration of deleted HK code.

### 6. Govern HK code by ownership class before removal

Create a tracked inventory that assigns HK surfaces to:

- `shared_active`: market-agnostic code still used by A-share or other markets
- `frozen_compatibility`: named HK presets, restore instructions, and compatibility commands still needed for bounded reproduction
- `archived_provenance`: bulky HK experiments, notes, and historical evidence intended for archive or demo extraction
- `retire_after_audit`: code with no supported downstream dependency after a documented restore and compatibility review

`market-data-platform` keeps HK freeze/hydrate and restore-critical code until retirement conditions pass. `quant-execution-engine` keeps HK parsing and broker support because it is a multi-market execution engine. `cross-sectional-trees` is the first repository where bulky HK research history should leave the active lane.

Alternative considered: split all HK code into a new repository immediately. Rejected because data-platform restore and execution support have different ownership and would be damaged by a strategy-level extraction.

### 7. Build the public HK demo as a clean-room export

The demo export uses an allowlist and creates a new repository snapshot without source Git history. It includes only curated framework code, a minimal HK strategy path, synthetic fixtures, sample outputs derived from synthetic fixtures, docs, license/disclaimer text, and minimal CI.

The export process must scan the staged tree for secrets, provider data, caches, generated private outputs, forbidden local absolute paths, and oversized files. Publication remains an explicit maintainer action after review. The active workspace links to the external demo but does not add it as a submodule.

Alternative considered: push the current HK repository or cold-storage archive directly to GitHub. Rejected because both can contain licensed data, historical paths, private outputs, and irrelevant maintenance history.

## Risks / Trade-offs

- [Risk] Requiring point-in-time fundamentals and historical industry assets delays the default switch. -> Keep `baseline_reproducible` as a useful intermediate state and leave `default_next` in place until the stronger gate passes.
- [Risk] The published A-share window is shorter than the current preset implies. -> Derive and report the effective window from current-contract manifests, align promoted presets, and reject misleading promotion evidence.
- [Risk] Removing HK files breaks hidden restore or compatibility dependencies. -> Inventory references first, deprecate before removal, keep a reproducible tag, and run focused restore/compatibility tests.
- [Risk] A public demo leaks licensed or sensitive content. -> Use a clean-room allowlist, synthetic fixtures, automated scans, size limits, and manual publication approval.
- [Risk] Users interpret a research dry-run as real A-share trading support. -> Keep broker enablement as a separate execution-owned readiness level and explicitly reject unsupported broker claims in docs and status output.
- [Risk] The HK release restore path is not actually usable after local snapshots were removed. -> Perform a documented restore drill before retiring restore-critical code.

## Migration Plan

1. Add the workspace A-share readiness report and capture the current `baseline_reproducible` gaps without switching aliases.
2. Stabilize A-share platform refresh and validation, align the candidate date window, and wire the published by-date universe into an A-share candidate.
3. Add point-in-time fundamentals, historical industry assets, A-share benchmark configs, side-aware trading semantics, and research evidence bundles.
4. Run the A-share research promotion review. Switch `default` only if `research_default_promotable` passes; keep `hk.yml` as the named compatibility route.
5. Build the HK ownership inventory, perform the restore drill, and extract or retire audited HK research-only surfaces from the active strategy repository.
6. Generate and review the clean-room HK demo snapshot, publish it as a separate paused-maintenance repository, and add an external workspace link.

Rollback:

- Before default promotion, keep using `default_next` and make no alias change.
- After default promotion, restore the prior `default.yml` alias and lifecycle documentation if A-share evidence regresses.
- Keep the HK freeze release, research freeze release, reproducible source tag, and export manifest so archive or demo extraction does not remove the recovery path.

## Open Questions

- Which A-share primary universe should be the first promoted research default: the existing lagged-liquidity full-market by-date universe, an index family such as CSI 300/500/800, or a layered set with one primary universe and comparison cohorts?
- Which licensed source and schema should provide A-share point-in-time fundamentals and historical industry changes?
- After dependency audit, should `alloc-hk` remain as a deprecated compatibility command in `cross-sectional-trees`, move to an optional legacy package, or exist only in the HK demo?
- What public repository name, license, and owner should be used for the HK demo after the staged export passes review?
