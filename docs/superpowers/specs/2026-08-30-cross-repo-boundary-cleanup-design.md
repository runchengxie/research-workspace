# Cross-repository boundary cleanup design

- Date: 2026-08-30
- Status: proposed
- Scope: `research-workspace` superproject and the affected owner repositories
- Related decisions: ADR-0006, ADR-0007, strategy-boundary refactor roadmap, maintainability refactor roadmap

## 1. Problem statement

The workspace has already completed several ownership migrations, but a small set of cross-repository boundaries still carry duplicate production logic or transitional ownership. The remaining issues are concentrated rather than systemic:

1. `alpha-research` and `portfolio-backtester` both implement nearly identical `freshness_overlay` score adjustment logic.
2. `alpha-research` and `portfolio-backtester` both carry nearly identical benchmarking helpers.
3. repository-local maintainability wrappers and some tests remain similar, although the stable scanner algorithm has already been extracted to the existing `research-code-quality` package.
4. StyleReplica still has transitional mixed ownership. ADR-0007 defines the target split, but existing code intentionally remains partially compatible while the migration is incomplete.
5. `strategy-research/src/style_factors/` contains reusable runtime capabilities that cross the documented owner boundaries, including portfolio replay preparation, execution diagnostics, data loaders, signal/backtest helpers, and a `portfolio_backtester_adapter.py` that performs more than thin adaptation.
6. the superproject now tracks eight submodules, including `strategy-research`, while `ARCHITECTURE.md` still describes seven submodules and an earlier non-submodule state.

The primary risk is semantic drift: two repositories can evolve different implementations of the same financial rule while each repository's local test suite remains green.

## 2. Goals

This change series will:

- establish one owner for each reusable financial-domain rule;
- remove confirmed cross-repository business-logic duplication;
- keep compatibility entry points where removal would create unnecessary breakage and where compatibility does not violate dependency direction;
- complete the highest-value parts of the ADR-0007 StyleReplica split without a big-bang rewrite;
- reduce `strategy-research` to research-specific orchestration, evidence, experiments, reports, and thin adapters where reusable capabilities already have an owner repository;
- preserve the existing roles of `research-contracts` and `research-code-quality` rather than inventing replacement shared layers;
- update the superproject's architecture documentation and gitlinks only after owner repositories have merged their changes;
- add regression coverage so the same duplicate/ownership drift is harder to reintroduce.

## 3. Non-goals

This series will not:

- introduce a new shared `common-utils` repository solely to remove small amounts of boilerplate;
- place research algorithms in `research-contracts`, whose existing scope is lightweight artifact/schema/hash/lineage contracts rather than research logic;
- replace `research-code-quality`, which already owns the stable cross-repository maintainability scanner algorithm;
- mechanically move every research experiment into a domain repository;
- require all affected repositories to merge simultaneously;
- remove compatibility APIs before consumers have migrated when a safe facade is possible;
- introduce a reverse `portfolio-backtester -> alpha-research` runtime dependency merely to eliminate a duplicate file;
- change trading semantics as part of code relocation unless a pre-existing inconsistency is discovered and separately documented;
- refactor unrelated maintainability hotspots merely because they are large.

## 4. Design principles

### 4.1 Domain owner beats call-site convenience

Reusable logic belongs to the repository that owns its semantics, even when another repository is the most convenient place to call it.

### 4.2 Preserve dependency direction

Ownership cleanup must not create a worse dependency graph. In particular, generic portfolio infrastructure must remain usable without importing alpha implementation packages. When a portfolio workflow needs an alpha-derived score, the score transformation happens upstream and the portfolio layer consumes the resulting score/artifact through its public contract.

### 4.3 Experiments may compose; reusable capabilities migrate

`strategy-research` may contain experiment-specific glue and one-off exploration code. Once a capability is reused across experiments or expresses a stable data/alpha/portfolio rule, it moves to the corresponding owner repository and the research code calls the owner API.

### 4.4 Compatibility is a facade, not a second implementation

During migration, old imports may remain only where they can delegate to the owner implementation without violating dependency direction. Compatibility modules must not retain a forked copy of the algorithm.

### 4.5 Financial semantics require parity tests before relocation

Before deleting a duplicate implementation that has active consumers, tests will pin current behavior using representative frames, edge cases, and relevant result metadata. Consumers then move to the owner API or receive the already-transformed artifact. The duplicate is deleted only after parity is proven.

### 4.6 PRs remain independently reviewable

Each PR should alter one ownership boundary or one supporting concern. Cross-repository dependencies are documented explicitly in PR descriptions rather than hidden in a single large change.

## 5. Target ownership matrix

| Capability | Owner | Allowed consumers / facades | Notes |
| --- | --- | --- | --- |
| factor, score, signal semantics | `alpha-research` | `strategy-app`, `strategy-research`, pipeline callers through public APIs | includes freshness-related score semantics when they modify alpha ranking/score |
| strategy identity and frozen strategy-specific policy | `strategy-app` | pipeline and research workflows | includes StyleReplica A80/B20 identity, theme quotas, strategy-version contracts |
| generic target/position construction, turnover, buffer, replacement, overlap, weights, replay periods | `portfolio-backtester` | `strategy-app`, `strategy-research`, `strategy-pipeline` | strategy-specific parameters are inputs, not hard-coded identities |
| portfolio execution simulation and execution diagnostics | `portfolio-backtester` | research and pipeline callers | broker-independent only |
| live brokerage, approvals, order state, reconciliation, recovery | `quant-execution-engine` | `strategy-pipeline` | no research repository may become an alternate live execution runtime |
| published market assets and stable data access contracts | `market-data-platform` | all research/strategy consumers | research-local data transforms remain allowed when experiment-specific |
| strategy thesis, lifecycle, evidence, research decisions, experiment orchestration | `strategy-research` | superproject navigation and research workflows | no second owner implementation of reusable alpha/portfolio/data capabilities |
| run orchestration, runtime directories, external calls, gates, publication | `strategy-pipeline` | operational entry points | no duplicate owner contracts |
| artifact envelope/schema/hash/lineage contracts | `research-contracts` in `research-workspace` | producer/consumer repositories | remains algorithm-free |
| stable cross-repository maintainability scanning | `research-code-quality` | repository-local governance wrappers | local budgets and repo-specific fields stay local |

## 6. Change set A: freshness overlay ownership

### Current state

`alpha-research` and `portfolio-backtester` contain nearly identical `freshness_overlay.py` implementations. The function changes a score using freshness/volume ranking information, so duplicated behavior creates a direct risk of score semantic drift.

`portfolio-backtester` does not currently declare `alpha-research` as a runtime dependency, and this cleanup must not add that reverse dependency just to share an implementation.

### Target state

`alpha-research` owns the canonical freshness score transformation. `portfolio-backtester` consumes scores that have already had alpha-owned transformations applied.

The migration will:

1. pin the current behavior in `alpha-research` with focused tests, including disabled mode, empty frames, missing columns, lambda bounds, rank behavior, output-column preservation, and metadata;
2. expose/confirm a stable public owner entry point in `alpha-research`;
3. audit all `portfolio-backtester` call sites for its duplicate module;
4. if the portfolio copy is dead, delete it and add a boundary regression test;
5. if active portfolio call sites exist, move the score adjustment to the upstream alpha/strategy caller and pass the adjusted score into portfolio APIs;
6. do not preserve a compatibility implementation inside `portfolio-backtester` if doing so would require either copied algorithm code or a new reverse dependency on `alpha-research`.

If evidence shows a genuinely portfolio-owned freshness concept, it must use a distinct name and contract rather than silently forking the alpha score transform.

## 7. Change set B: portfolio capabilities currently implemented in strategy-research

### Current state

`strategy-research/src/style_factors/portfolio_backtester_adapter.py` currently includes both thin calls into `portfolio-backtester` and generic portfolio/execution-domain logic such as:

- target frame normalization and validation;
- rebalance/entry/exit period construction;
- delayed-fill attribution;
- execution receipt summarization.

The same package also contains reusable backtest/execution modules and data loaders whose long-term ownership is ambiguous relative to the workspace's documented owner model.

### Target state

Generic portfolio contracts and diagnostics move to `portfolio-backtester`. `strategy-research` keeps only research-specific translation and experiment orchestration.

The migration will:

1. search `portfolio-backtester` for existing public equivalents before adding any new API;
2. add owner APIs and tests only for generic pieces that do not already have a public equivalent;
3. migrate `strategy-research` to those APIs;
4. shrink `portfolio_backtester_adapter.py` to schema translation and thin delegation;
5. inventory `style_factors` modules by owner category: research-only, alpha candidate, portfolio candidate, data-access candidate;
6. move only clearly reusable capabilities in this series; leave one-off experiment code in place and record remaining extraction debt explicitly.

The adapter may depend on public `portfolio-backtester` APIs. It must not reach into private underscore modules merely to avoid defining a proper owner API.

## 8. Change set C: StyleReplica ADR-0007 closure

ADR-0007 remains the governing decision. This series does not replace it.

The target split is:

- `alpha-research`: factor, score, signal, research labels and diagnostics;
- `strategy-app`: StyleReplica identity and frozen strategy-specific policy;
- `portfolio-backtester`: generic candidate-to-position construction and replay;
- `strategy-pipeline`: orchestration only;
- `market-data-platform`: published data contracts;
- `quant-execution-engine`: live execution responsibilities.

Implementation proceeds in small slices:

1. freeze existing public results with fixtures/parity tests;
2. move or delegate strategy identity parameters to the existing `strategy-app/style_replica/policy.py` contract;
3. move/delegate generic buffer, replacement, overlap, weighting, and validation behavior to `portfolio-backtester` APIs;
4. keep `alpha_research.style_replica` compatibility entry points as thin facades while consumers migrate, provided the facade can use the target owner APIs without introducing forbidden dependency cycles;
5. where a thin cross-owner facade would create a cycle, migrate the caller first and deprecate/remove the old composite entry point instead of retaining a second implementation;
6. add boundary tests that forbid new strategy-policy or final-position construction logic from being added to the alpha compatibility surface.

The migration is ratchet-only: mixed responsibilities may decrease, but no new mixed responsibility is accepted in the compatibility package.

## 9. Change set D: lower-risk non-domain duplication

### Benchmarking helpers

The duplicate benchmarking helpers in `alpha-research` and `portfolio-backtester` are lower risk than financial-rule duplication. They will be handled after the semantic owner work.

The audit will first determine whether these helpers are runtime API, repository-local instrumentation, or accidental historical copies. The preferred result is the smallest change that produces one maintained behavior without adding a new repository or an inappropriate dependency edge.

### Maintainability tooling

The stable scanner algorithm is already centralized in `research-code-quality`; current repository-local `maintainability_metrics.py` files intentionally keep local ratchet budgets, local metric fields, and local CLI formatting.

Therefore this series will not mechanically merge those wrappers. It will only:

- verify that remaining cross-repository-identical logic is already delegated to `research-code-quality`;
- remove or reduce truly redundant wrapper/test code only where doing so preserves standalone repository checks;
- keep repository-specific budgets and governance values local.

This item may produce no code PR if the audit confirms the current split is already appropriate.

## 10. Superproject changes

After the owner-repository PRs merge:

1. update the affected submodule gitlinks in a dedicated `research-workspace` integration PR;
2. correct `ARCHITECTURE.md` to describe the current eight-submodule state and the `strategy-research` role;
3. ensure `.gitmodules`, architecture docs, ownership docs, CODEOWNERS, scanner exclusions, and `research-contracts` dependency documentation agree;
4. add a lightweight cross-repository boundary/duplicate regression check for the specific classes of drift fixed here;
5. update relevant roadmap/ADR status notes without rewriting historical decisions.

## 11. Proposed PR stack

The expected stack is:

1. **research-workspace design PR**: this document only.
2. **alpha-research PR A1**: canonical freshness owner API plus behavior tests.
3. **portfolio-backtester PR A2**: audit/delete the duplicate freshness implementation or remove active call sites by requiring upstream-adjusted scores; no `portfolio-backtester -> alpha-research` dependency.
4. **portfolio-backtester PR B1**: expose any missing generic position-period/execution-diagnostic owner APIs needed by `strategy-research`.
5. **strategy-research PR B2**: shrink portfolio adapter, remove migrated duplicate capabilities, and record remaining extraction debt.
6. **strategy-app / alpha-research / portfolio-backtester StyleReplica PRs C1..Cn**: small ADR-0007 migration slices with compatibility facades and parity tests where dependency direction permits.
7. **optional tooling PRs D1..Dn**: benchmarking and residual governance duplication, only after domain-semantic work is stable and only where the audit proves a real duplicate remains.
8. **research-workspace integration PR**: update gitlinks, `ARCHITECTURE.md`, governance checks, and roadmap status.

PR numbering is conceptual; repositories may require more than one small PR if a boundary is too large to review safely.

## 12. Compatibility and dependency strategy

A dependent repository must not require an unmerged branch from another repository for its default branch to remain usable.

Therefore:

- provider PRs merge before consumer PRs whenever a new public API is required;
- compatibility facades preserve existing import paths only when they can delegate without copying logic or creating forbidden dependency cycles;
- where safe delegation is impossible, migrate consumers first and remove/deprecate the old composite API in a later PR;
- the superproject gitlink update happens only after the referenced owner commits exist on their repository default branches;
- compatibility removals are deferred until repository search confirms no remaining consumers.

## 13. Testing strategy

Each ownership move uses three layers of tests:

1. **owner unit tests** for the canonical behavior and edge cases;
2. **consumer parity tests** demonstrating that delegation or upstream transformation preserves existing results;
3. **boundary tests** preventing the displaced implementation or forbidden dependency direction from returning.

For financial logic, parity tests compare both primary outputs and meaningful metadata/diagnostics. Tests should use fixed fixtures and avoid relying on mutable external data.

The superproject integration PR additionally runs the existing workspace doctor/governance checks and maintainability gates against the final gitlink set.

## 14. Rollback strategy

Because the series uses provider-first APIs and compatibility facades where safe, each consumer migration can be reverted independently.

If a parity mismatch is discovered before duplicate deletion:

- keep the old implementation temporarily on the migration branch while investigating;
- document the mismatch as a semantic bug or intentional difference;
- resolve it in the owner repository before merging the cleanup that removes the duplicate.

The merged target state must not retain two canonical financial implementations merely to satisfy compatibility.

## 15. Completion criteria

This cleanup is complete when:

- only one canonical implementation remains for the currently duplicated freshness score transform;
- `portfolio-backtester` has not gained a reverse runtime dependency on `alpha-research` as a side effect of freshness cleanup;
- `strategy-research` no longer owns generic portfolio period construction or execution-attribution capability where a portfolio owner API exists;
- ADR-0007 mixed responsibilities have materially decreased and any retained compatibility surfaces are thin delegators;
- no affected consumer depends on another repository's private/internal module path;
- `ARCHITECTURE.md` matches the eight-submodule reality;
- the final superproject gitlinks point to merged owner commits;
- targeted boundary/duplicate tests prevent the fixed drift patterns from being reintroduced;
- existing `research-contracts` and `research-code-quality` boundaries remain intact;
- any intentionally deferred extraction debt is explicitly recorded with an owner and deletion/migration condition.
