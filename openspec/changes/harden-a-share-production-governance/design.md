## Context

The superproject coordinates three Python submodules but intentionally does not own their internal tool rules. Current delegated checks already show the split: `market-data-platform` uses Ruff + Pyright, `cross-sectional-trees` uses Ruff + Pyright with a narrow include set, and `quant-execution-engine` uses Ruff + mypy. The superproject has lightweight scripts and tests but no root `pyproject.toml`.

A 股 has been promoted as the research default, yet it remains a staged research baseline: daily-clean assets, by-date universe, research outputs, `targets.json`, and CN dry-run evidence exist, while complete PIT fundamentals, historical industry, longer-window strategy evidence, and real broker enablement remain separate work.

The public `runchengxie/tushare-a-share-fundamentals` repository is useful as a downloader reference because it documents dataset specs, TuShare VIP/non-VIP behavior, SQLite state, failure reports, Parquet cache layout, and special handling for dividend and audit downloads. It should not be copied wholesale because this workspace needs platform manifests, current-contract keys, registry rows, and strict PIT semantics.

港股 has been moved out of the default lane. The workspace already has cold-storage evidence and a clean-room public demo exporter, but the active strategy repository still contains substantial 港股 configs, research notes, and specialized helper code.

## Goals / Non-Goals

**Goals:**

- Define a repo-by-repo quality policy that is enforceable from the superproject without overwriting submodule ownership.
- Keep `quant-execution-engine` mypy hard-gated while evaluating Pyright as advisory before any migration decision.
- Add a staged quality-hardening roadmap: top-level Ruff for scripts/tests, secret scanning, dependency audit, optional dependency hygiene, and selective coverage ratchets.
- Define the remaining evidence needed before A 股 can be described as a complete production research stack or a broker-enabled execution stack.
- Add a TuShare A 股基本面 raw-to-PIT ingestion design that fits `market-data-platform` contracts and prevents look-ahead bias.
- Reduce 港股 active-lane weight while retaining restore, compatibility, and public-demo value.

**Non-Goals:**

- Force a single root Ruff/Pyright configuration across all submodules.
- Replace `quant-execution-engine` mypy with Pyright in one step.
- Claim real A 股 broker trading support from CN `targets.json` dry-run evidence.
- Import `tushare-a-share-fundamentals` as a vendored subproject or copy its storage layout verbatim.
- Delete 港股 restore-critical data-platform code or multi-market execution support.
- Publish real market data, credentials, private research outputs, or historical Git history in the public demo.

## Decisions

### 1. Standardize quality checks by profile, not by identical tool

The superproject SHALL keep `smoke`, `lint`, `test`, `type`, and `full` profile names as the stable management surface. Each submodule continues to own its tool implementation. This avoids cross-scanning submodules with the wrong Python target, optional extras, or ignore rules.

Alternative considered: add a root `pyproject.toml` that scans every submodule. Rejected because the repositories have different Python versions, dependency groups, optional SDKs, and type-checking maturity.

### 2. Keep mypy hard-gated in `quant-execution-engine`; add Pyright advisory

`quant-execution-engine` already has stable mypy config and docs. It is execution-critical, so replacing the hard gate should require evidence that Pyright catches useful issues with acceptable noise. The first step is an advisory Pyright profile with `typeCheckingMode=basic`, optional SDK stub warnings disabled, and no replacement of the current `type` profile.

Alternative considered: switch directly to Pyright for consistency with the other two submodules. Rejected because consistency at the profile level already exists, while checker semantics and optional broker SDKs make a direct migration risky.

### 3. Add security and dependency checks in stages

Secret scanning has the highest risk-reduction value because the workspace handles provider and broker credentials. Dependency audit and dependency-hygiene checks should begin advisory because optional extras, provider SDKs, and local broker environments can create false positives. Security linting for execution code should start scoped to high-confidence findings.

Alternative considered: add every recommended tool as a hard CI gate. Rejected because it would block migration on noise before baselines and suppression policies are reviewed.

### 4. Treat A 股 production readiness as four distinct states

The workspace should distinguish:

1. reproducible research baseline,
2. complete PIT research data stack,
3. production-grade strategy evidence,
4. broker-enabled trading.

The current state satisfies the first two-way handoff loop but not complete PIT data, long-window strategy evidence, or broker trading. Docs and readiness reports must keep these separate.

Alternative considered: use one “正式 A 股” label. Rejected because it hides materially different risks in data, research, and execution.

### 5. Build TuShare 基本面 ingestion as platform-native raw-to-PIT layers

The downloader should be split into dataset specs, raw acquisition, normalized assets, PIT conversion, validation, and current-contract publication. Raw data should preserve query provenance and retrieved timestamps. PIT outputs should require report period, disclosure date, availability delay, and selected field mappings.

Alternative considered: copy the standalone downloader output layout into the platform root. Rejected because platform assets must use existing manifest, registry, validation, and current-contract conventions.

### 6. Slim 港股 by lifecycle class, not by text search

Shared pipeline/execution code remains active. Explicit `hk` presets and `alloc-hk` remain frozen compatibility until consumer evidence supports removal. Bulky experiments, historical notes, and research-only helpers should leave active navigation first, then move to archive or public-demo extraction after restore and rollback evidence is recorded.

Alternative considered: delete all HK-named files after A 股 default promotion. Rejected because that would damage restore, reproducibility, and multi-market execution behavior.

## Risks / Trade-offs

- [Risk] Advisory checks never become actionable. → Give each advisory tool an owner, a review command, and a promotion criterion before adding it.
- [Risk] Pyright advisory creates duplicate type-ignore noise. → Keep mypy as the only hard gate and record Pyright findings before deciding on migration.
- [Risk] TuShare 基本面 raw data is accidentally used as PIT data. → Require separate raw, normalized, and PIT asset keys; research configs may only use PIT outputs for statement fundamentals.
- [Risk] VIP/non-VIP TuShare behavior silently drops datasets. → Encode entitlement policy in dataset specs and write skipped/failed datasets into machine-readable reports.
- [Risk] Longer A 股 evidence reveals the promoted baseline is weak. → Treat that as a research result; do not let default alias status imply strategy profitability.
- [Risk] 港股 code removal breaks hidden users. → Require inventory, focused tests, source reference, archive manifest, restore evidence, and rollback docs before removing public surfaces.
- [Risk] Public demo creates maintenance or compliance expectations. → Keep synthetic-only fixtures, first-screen paused-maintenance wording, scans, and no real performance claims.

## Migration Plan

1. Record the quality matrix across all repositories and update the superproject delegated profiles.
2. Add top-level Ruff for superproject `scripts/` and `tests/` only, then add secret scanning and dependency audit in advisory mode.
3. Add `quant-execution-engine` Pyright advisory config and profile while preserving mypy as the hard `type` profile.
4. Add `market-data-platform` TuShare 基本面 dataset specs, state tracking, raw downloader, validation, manifests, and tests.
5. Add normalized and PIT builders, publish current-contract keys only after validation passes, and wire `cross-sectional-trees` configs behind explicit feature flags.
6. Expand A 股 evidence to longer history, benchmark ladder, CPCV/final OOS, feature evidence, turnover/capacity, and execution dry-run reports.
7. Move 港股 active documentation/navigation to legacy/archive indexes, keep minimal compatibility tests, and publish or refresh the clean-room public demo through explicit maintainer action.

Rollback:

- Quality tooling: remove advisory profiles or keep them non-blocking if noise exceeds value.
- Pyright advisory: leave mypy hard gate unchanged and remove the advisory profile if it blocks local development.
- A 股 fundamentals: do not add current-contract keys until validation passes; raw downloads can remain unpublished.
- 港股 slimming: use the source reference, archive manifest, and restore drill to rehydrate or relink removed provenance.

## Open Questions

- Which TuShare entitlement level is the minimum supported for production basic fundamentals: VIP-only batch APIs, non-VIP per-symbol fallbacks, or both?
- Which A 股 primary benchmark family should be required before production research evidence: full A equal weight, CSI 300/500/1000, or a layered benchmark ladder?
- What review period should be required before promoting `quant-execution-engine` Pyright from advisory to hard gate, if ever?
- Which 港股 surfaces have active human users after default promotion, especially `alloc-hk` and specialized research scripts?
