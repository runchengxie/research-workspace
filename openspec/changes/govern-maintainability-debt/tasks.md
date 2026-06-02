## 1. Baseline Inventory

- [x] 1.1 Record current maintainability findings for all four repos: HK surfaces, deprecated entrypoints, large files, long functions, complexity hotspots, quality excludes, and script inventory.
- [x] 1.2 Confirm whether `split-hk-public-demo` artifacts are present, and link its split manifest as an input rather than duplicating its records.
- [x] 1.3 Create or refresh a top-level maintainability evidence directory for generated JSON baseline reports.
- [x] 1.4 Add a baseline command that can scan Python files with stdlib AST and report file LOC, function length, approximate complexity, and HK-related file counts.
- [x] 1.5 Add focused tests for the baseline command schema and threshold reporting.

## 2. Deprecation Governance

- [x] 2.1 Add `docs/deprecations.md` with records for `hkdata`, `hk_data_platform.*`, `rqdata-hk-depth`, `rqdata-tick`, `rqdata-hk-assets`, `cstree alloc-hk`, and HK historical config/archive surfaces.
- [x] 2.2 Include owner, replacement, current consumers, target milestone, removal condition, rollback path, restore evidence requirement, and focused tests in every deprecation record.
- [x] 2.3 Add a machine-readable deprecation manifest or checked table parser for `docs/deprecations.md`.
- [x] 2.4 Add tests that reject removal-ready deprecations without consumer audit, replacement docs, rollback notes, and focused tests.
- [x] 2.5 Link deprecation governance from `docs/hk-legacy-surface-inventory.md`, `docs/hk-public-split-manifest.yml`, and top-level docs.

## 3. Script Lifecycle Governance

- [x] 3.1 Create a script lifecycle manifest covering top-level scripts, `cross-sectional-trees/scripts/internal/*`, `market-data-platform/scripts/internal/*`, and `quant-execution-engine/project_tools/*`.
- [x] 3.2 Classify scripts as `dev`, `ci`, `release`, `migration`, or `archive`.
- [x] 3.3 Add owner, purpose, safe-to-run-local status, write targets, external dependencies, and removal condition for each tracked script.
- [x] 3.4 Add tests that detect unclassified non-trivial scripts and invalid lifecycle metadata.
- [x] 3.5 Update script docs or README entrypoints so maintainers can distinguish daily commands from release-only, migration, and archive tools.

## 4. Quality Coverage Governance

- [x] 4.1 Add or refresh per-repo quality baseline files that report Ruff selected rules, Ruff excludes, Pyright includes, Pyright excludes, and advisory versus hard gates.
- [x] 4.2 Update `cross-sectional-trees` Ruff rules to include staged low-risk rule families such as `E`, `F`, `I`, `UP`, `B`, `C4`, `RET`, `SIM`, `RUF`, and `C90`, while registering remaining exceptions.
- [x] 4.3 Expand `cross-sectional-trees` Pyright include scope to low-risk pipeline/liveops contract modules before broader research modules.
- [x] 4.4 Reduce `market-data-platform` broad HK Ruff exclusion by including low-risk HK modules first, and register remaining HK asset/release excludes with owner and next action.
- [x] 4.5 Expand `market-data-platform` Pyright coverage first for small HK model/shared/public modules, then record deferred heavy workflow/downloader modules.
- [x] 4.6 Add `quant-execution-engine` staged strictness targets for execution-critical modules such as targets, risk, preflight, rebalance, execution state, broker base, and execution service.
- [x] 4.7 Add tests that fail when a broad quality exclude is added without owner, reason, review milestone, and next include target.

## 5. Complexity Refactor Roadmap

- [x] 5.1 Add a roadmap section or document listing priority large files in `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine`.
- [x] 5.2 For each priority file, record first safe extraction type, target module layout, owner repo, risk level, non-goals, and focused tests.
- [x] 5.3 Add roadmap entries for HK data asset modules: `asset_health.py`, `audit_assets.py`, `hk_asset_workflow.py`, and `hk_depth/downloader.py`.
- [x] 5.4 Add roadmap entries for strategy research modules: `pipeline/eval.py`, train/eval orchestration, `summarize_runs.py`, `exposure.py`, and `commands/tune.py`.
- [x] 5.5 Add roadmap entries for execution modules: `cli.py`, `broker/longport.py`, and smoke harness project tools.
- [x] 5.6 Add tests that ensure every hotspot above threshold is either in the roadmap or explicitly accepted with owner and next action.

## 6. Team Collaboration Guardrails

- [x] 6.1 Add top-level `CODEOWNERS` with repo-boundary ownership for the superproject and submodules.
- [x] 6.2 Add top-level `CONTRIBUTING.md` that explains branch scope, submodule boundaries, verification order, and how to handle dirty submodule gitlinks.
- [x] 6.3 Add top-level `ARCHITECTURE.md` or equivalent docs entrypoint that summarizes active code, compatibility code, archive/provenance, demo staging, and private runtime boundaries.
- [x] 6.4 Add a PR checklist covering deprecated surfaces, one-off scripts, quality excludes, `targets.json`, provider/broker credentials, migration notes, and focused tests.
- [x] 6.5 Add docs/tests that ensure the PR checklist and contribution docs mention the required maintainability governance topics.

## 7. Verification

- [x] 7.1 Run data-platform focused governance tests and any touched Ruff/Pyright checks; record exact command output.
- [x] 7.2 Run strategy-research focused governance tests and any touched Ruff/Pyright checks; record exact command output.
- [x] 7.3 Run execution-engine focused governance tests and any touched Ruff/Pyright/mypy checks; record exact command output.
- [x] 7.4 Run top-level docs, manifest, baseline, root quality, docs links, and workspace doctor tests.
- [x] 7.5 Run `python scripts/workspace_doctor.py` and capture warning/error counts.
- [x] 7.6 Review `git status --short` in the superproject and each submodule, including submodule gitlink state.
- [x] 7.7 Summarize results in the required order: data platform -> strategy research -> trading execution -> top-level docs/doctor -> remaining limitations.
