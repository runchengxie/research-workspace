## Why

中国香港市场相关能力目前仍分散在数据平台、策略研究、交易执行和公开 demo 之间；虽然已有 clean-room demo export 和 legacy surface inventory，但代码目录还没有把 active、compat、archive、public demo staging 的边界表达清楚。

这个变更把公开 demo 定位为未来独立仓库的 staging 区，并给中国香港市场 legacy 代码建立可审计的迁出、归档、保留和禁止公开清单，减少主项目维护负担，同时保留可复现证据和作品集展示价值。

## What Changes

- Add a versioned 中国香港市场 public split manifest that classifies each HK-related surface as `keep_in_main`, `move_to_public_demo`, `archive_in_public_demo`, `delete_after_split`, or `private_do_not_export`.
- Expand `demo/hk-public-demo-template-v1` from a narrow demo template into a self-contained public repo candidate with source, tests, fixtures, docs, archive stubs, CI, quality checks, and export metadata expectations.
- Move or reimplement only public-safe HK demo logic into the demo staging tree; production provider data, credentials, broker adapters, private outputs, and local paths remain excluded.
- Add checks that prevent the public demo staging tree from depending on workspace packages, licensed/private data, provider cache, broker integrations, absolute local paths, or secret-like material.
- Define deletion and deprecation gates for HK compatibility entrypoints that stay in the main workspace until restore evidence, consumer audit, and public split evidence are complete.
- Update top-level docs so the data platform -> strategy research -> trading execution path remains the active mainline, while the 中国香港市场 public demo is documented as an external frozen/paused-maintenance reference.
- No breaking runtime API changes are planned in the first implementation pass; removal of compatibility entrypoints will require follow-up changes after the manifest gates pass.

## Capabilities

### New Capabilities

- `hk-public-demo-split`: Defines the public demo staging boundary, export safety requirements, split manifest contract, independent quality gates, and post-split cleanup gates for 中国香港市场 legacy surfaces.

### Modified Capabilities

None.

## Impact

- Affects top-level docs under `docs/`, especially 中国香港市场 legacy/demo/archive guidance and release/checklist references.
- Affects `demo/hk-public-demo-template-v1/` by adding repo-candidate structure, quality tooling, tests, docs, and public-safe extracted or reimplemented logic.
- Affects `scripts/export_hk_public_demo.py`, demo allowlist files, secret/path scan rules, and top-level quality or doctor checks that reason about demo staging.
- Affects cross-repo inventory documents that classify HK surfaces across `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine`.
- Does not copy real market data, provider caches, credentials, broker adapters, trading audit logs, or private research outputs into the public demo.
