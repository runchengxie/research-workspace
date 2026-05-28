## Context

`market-data-platform` is in a post-migration state. The core HK asset, HK depth, release workflow, provider, and compatibility code now live in the platform repository, but the static-check configuration still excludes many of the modules that were migrated last. The existing `scripts/dev/quality_debt.py` already reports that Ruff covers 12,596 of 46,775 source lines and Pyright covers 4,837 of 46,775 source lines, leaving the highest-risk business modules mostly outside normal quality gates.

The repository also preserves compatibility surfaces such as `hkdata`, `hk_data_platform.*`, provider re-export modules, migration commands, and legacy console scripts. `docs/compatibility.md` documents their purpose and cleanup conditions, but the lifecycle is not yet enforced by tests or developer tooling.

The design keeps current runtime behavior stable while adding enough governance to prevent further drift and to make incremental cleanup safe for a team.

## Goals / Non-Goals

**Goals:**

- Make Ruff/Pyright coverage measurable, baseline-backed, and resistant to silent regression.
- Keep existing test and static-check commands green while exposing broader debt through non-blocking reports.
- Give compatibility and migration-only surfaces explicit ownership, audit evidence, and removal criteria.
- Add maintainability metrics for oversized files/functions and public API exports so high-risk refactors can be planned and verified.
- Prefer small, reviewable refactors that preserve data contracts, artifact layouts, CLI behavior, and provider runtime behavior.

**Non-Goals:**

- Do not enable Pyright strict mode across the repository in one step.
- Do not remove public compatibility entry points before repo-local and downstream usage has been audited.
- Do not rewrite HK assets, HK depth, or release workflows into a new architecture in a single change.
- Do not change RQData/TuShare authentication, network access, artifact schemas, or release package formats.
- Do not treat pandas/pyarrow typing noise as a mandatory blocker for unrelated maintenance work.

## Decisions

### Baseline Debt Instead of Immediate Full Enforcement

Current debt is too large to make full Ruff/Pyright coverage blocking immediately. The implementation will add a checked-in baseline for static-check coverage and complexity/type debt, then fail only when coverage drops, exclude lists expand without acknowledgement, or measured debt increases beyond the baseline.

Alternative considered: remove directory-level excludes immediately. This would surface real issues but would create a large, noisy remediation branch and make unrelated work difficult to merge.

### Keep Quality Tooling Repo-Local and Deterministic

Extend repo-local scripts under `scripts/dev/` rather than depending on external hosted tooling. The scripts should support human-readable output for local use and machine-readable JSON for tests/CI.

Alternative considered: rely only on Ruff/Pyright native output. Native output is useful, but it does not answer project-specific questions such as checked-line coverage, compatibility lifecycle state, or file/function size budgets.

### Tier Static Coverage by Risk

Coverage expansion will happen by tier:

1. Low-risk boundary modules such as contracts, paths, registry, manifests, and current assets.
2. Provider contracts and CLI adapters.
3. HK depth and release workflow modules.
4. HK assets pipelines and health/audit modules.

Each tier can move from excluded to included when its Ruff/Pyright issues are either fixed or intentionally documented with narrow per-file ignores.

Alternative considered: enable all `src/` modules at once and add broad inline ignores. That would move debt from config into source files without improving maintainability.

### Compatibility Lifecycle Uses Documentation Plus Tests

`docs/compatibility.md` remains the human-readable inventory. Tests or scripts will verify that each known compatibility surface has a documented purpose, risk, cleanup condition, and current status. New compatibility surfaces must be added to the inventory before they can merge.

Alternative considered: remove compatibility layers based only on repo-local `rg`. Repo-local usage is necessary but insufficient because workspace scripts and downstream repositories may still use legacy paths.

### Maintainability Metrics Guide Refactoring Before Architecture Moves

The first implementation should measure file length, function length, complexity candidates, public API export count, and dependency direction. It should not require an immediate final package split. The metrics identify the worst offenders and prevent new modules from exceeding agreed budgets.

Alternative considered: create a new `hk_assets/domain/providers/pipelines/health/cli` package structure immediately. That structure is directionally useful, but forcing it before establishing tests and baselines risks behavior changes in data production code.

## Risks / Trade-offs

- [Risk] Baselines can normalize bad code if never tightened. → Mitigation: require tasks and docs to name the next files/modules to admit into Ruff/Pyright coverage and keep debt reports visible in CI.
- [Risk] Non-blocking reports may be ignored. → Mitigation: make regressions blocking even while absolute historical debt remains non-blocking.
- [Risk] Compatibility deprecation can break downstream jobs. → Mitigation: require audit evidence, warning period, and rollback path before removal.
- [Risk] Metric thresholds can incentivize mechanical splitting instead of better design. → Mitigation: use budgets as review signals and pair them with cohesive extraction patterns such as plan/fetch/transform/validate/persist/report.
- [Risk] Type checking pandas-heavy code may produce noisy diagnostics. → Mitigation: start at boundaries with Protocols, TypedDict/dataclass config objects, and narrow excludes before increasing Pyright mode.

## Migration Plan

1. Add or extend developer tooling to emit static coverage, maintainability metrics, and compatibility inventory reports.
2. Check in initial baselines using the current repository state.
3. Add tests/CI hooks that fail on coverage regression, undocumented new excludes, undocumented compatibility surfaces, and new severe maintainability outliers.
4. Move the lowest-risk excluded modules into Ruff coverage first, replacing directory excludes with narrower file-level handling where necessary.
5. Begin targeted refactors of the worst long functions by extracting plan/config, provider/fetch, transform, validate, persist, manifest, and report steps behind stable tests.
6. For each compatibility item, run repo-local audit, document downstream status, add deprecation warnings where appropriate, and remove only after the cleanup condition is satisfied.

Rollback is straightforward for the governance phase: remove newly added gating tests or restore the previous baseline file. Runtime behavior is not intended to change during baseline creation.

## Open Questions

- Which external/downstream jobs still call `hkdata`, `rqdata-tick`, `hk_data_platform.*`, or migration commands?
- Should the first Pyright expansion target provider contracts or package/release boundary modules?
- What CI environment will run non-blocking debt reports, and should failures be blocking only on pull requests or also on local pre-commit hooks?
