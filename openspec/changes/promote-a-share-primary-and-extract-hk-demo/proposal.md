## Why

The workspace has already frozen the China Hong Kong market data lane into cold storage and introduced an A-share `default_next` candidate, but the active research default still points to the historical HK starter and the A-share lane is still a `daily_clean` / static-universe baseline. The next change should turn that partial migration into an evidence-backed A-share primary lane while preserving the useful HK history as a bounded legacy reference and a curated public portfolio demo.

## What Changes

- Define three explicit A-share readiness levels: reproducible baseline, promoted research default, and broker-enabled trading. The first two are workspace deliverables; broker-enabled A-share order submission remains a separately approved execution project.
- Add an A-share promotion gate that verifies the canonical `metadata/current_assets/a_share_current.json` contract, registry rebuild, `daily_clean` quality, point-in-time universe, point-in-time fundamentals, historical industry semantics, A-share benchmark evidence, trading-rule treatment, research outputs, `targets.json` lineage, and execution-engine dry-run evidence.
- Switch `cstree run --config default` to the A-share primary preset only after the promoted-research gate passes. **BREAKING**: once promoted, the compatibility default no longer resolves to the historical HK/RQData starter.
- Classify retained HK code and assets by ownership and lifecycle: shared market-agnostic core, frozen HK compatibility surface, archived HK research provenance, and candidate extraction/removal surface.
- Keep HK data freeze/hydrate support in `market-data-platform` until restore obligations and downstream dependencies are retired; do not remove multi-market HK parsing or broker support from `quant-execution-engine`.
- Reduce the active `cross-sectional-trees` surface by moving bulky HK experiments, notes, and HK-specific research/demo material out of the primary lane after a dependency audit. Keep only the intentionally supported compatibility surface needed for reproducibility or restore.
- Add a clean-room public HK strategy demo export: no original Git history, licensed provider data, credentials, local absolute paths, private reports, or active-workspace dependency. Include synthetic fixtures, a minimal runnable pipeline, sample `summary.json`, sample `targets.json`, documentation, license/disclaimer, and minimal CI.
- Document that the public HK demo is a paused-maintenance historical reference and is linked from the workspace as an external portfolio project, not tracked as an active submodule.

## Capabilities

### New Capabilities
- `a-share-strategy-readiness`: Define evidence-backed gates for A-share baseline reproducibility, research-default promotion, and the separate broker-trading boundary.
- `hk-legacy-lane-governance`: Define how HK code, data lifecycle support, research provenance, compatibility commands, and multi-market execution support are retained, frozen, extracted, or retired.
- `hk-public-demo-export`: Define a clean, reproducible, license-safe public demo export for the historical HK strategy lane.

### Modified Capabilities

None. The workspace does not yet have existing OpenSpec capability specs.

## Impact

- `market-data-platform`: A-share current-contract refresh, validation, registry, PIT data assets, historical industry assets, HK freeze/hydrate lifecycle support, and focused contract tests.
- `cross-sectional-trees`: A-share presets, benchmark ladder, PIT consumers, side-aware trading semantics, promotion evidence, `default` alias, HK experiment and documentation inventory, `alloc-hk` compatibility decision, project metadata, and focused research/export tests.
- `quant-execution-engine`: CN `targets.json` dry-run evidence and capability documentation; existing HK and CN multi-market parsing remain in scope. Real A-share broker submission is explicitly out of scope for this change.
- Superproject: migration-status documentation, workspace doctor checks, release checklist, external demo link policy, and cross-repository focused verification.
- Public export process: a separate clean-room repository snapshot with synthetic fixtures and minimal CI, produced without publishing private data or carrying source repository history.
