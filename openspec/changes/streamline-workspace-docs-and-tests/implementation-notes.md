# Implementation Notes

## Baseline Inventory

Current Markdown scan scope: root `README.md` / `AGENTS.md`, root `docs/`, and the three initialized submodules' `README.md` / `AGENTS.md` / `docs/` trees.

- Markdown files: 116
- Total Markdown lines: 21,626
- Largest hotspots:
  - `cross-sectional-trees/docs/rqdata/hk-stock-data-reference.md`: 2,602 lines
  - `cross-sectional-trees/docs/outputs.md`: 1,233 lines
  - `cross-sectional-trees/docs/research/notes/hk-monthly-ranker-ab-and-next-sweep-20260413.md`: 841 lines
  - `cross-sectional-trees/docs/metrics.md`: 698 lines
  - `cross-sectional-trees/docs/config.md`: 622 lines
  - `cross-sectional-trees/docs/cli.md`: 498 lines
  - `cross-sectional-trees/docs/playbooks/hk-selected.md`: 429 lines
  - `market-data-platform/docs/session-handoff-a-share-backfill-20260531.md`: 295 lines
  - `market-data-platform/docs/operations.md`: 289 lines
  - `quant-execution-engine/docs/testing.md`: 221 lines

## Archive Paths

- Superproject HK history:
  - `docs/archive/hk/README.md`
  - `docs/archive/hk/release-notes/`
  - `docs/archive/hk/session-handoffs/`
- `market-data-platform` dated handoffs:
  - `docs/archive/session-handoffs/`
- `cross-sectional-trees` HK research:
  - Keep dated notes in `docs/research/notes/` for link stability.
  - Treat `docs/research/README.md` as the HK legacy research archive index.
  - Move large vendor snapshots to `docs/archive/vendor-rqdata/`.
- `quant-execution-engine` completed phase material:
  - `docs/archive/`

## Forwarding Stubs

Internal links will be updated directly. Forwarding stubs are only kept when a top-level historical file is likely to have been referenced externally. For this pass, moved dated root docs do not keep stubs because they remain discoverable from `docs/archive/hk/README.md`.

## Style Scope

Hard style checks cover active docs only:

- `README.md`
- `AGENTS.md`
- primary `docs/**/*.md`

Archive paths are exempt by default. Required safety caveats can stay in active docs if they are explicitly listed in a test allowlist with file and phrase context.
