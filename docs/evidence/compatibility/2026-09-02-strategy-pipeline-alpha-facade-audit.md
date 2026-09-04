# Strategy Pipeline Alpha Compatibility Facade Audit

Date: 2026-09-02
Scope: five `strategy-pipeline` compatibility facades that delegate to `alpha-research`
Decision: **retain pending the repository's two-release-review removal condition; consumer migration is complete**

## Audited facades

| Pipeline facade | Owner replacement |
| --- | --- |
| `strategy_pipeline.pipeline.freshness_overlay` | `alpha_research.freshness_overlay` |
| `strategy_pipeline.pipeline.train_eval_request_builder` | `alpha_research.train_eval_request_builder` |
| `strategy_pipeline.pipeline.train_eval_result` | `alpha_research.train_eval_result` |
| `strategy_pipeline.pipeline.research_ops.promotion_gate` | `alpha_research.promotion_gate` |
| `strategy_pipeline.pipeline.research_ops.promotion_gate_thresholds` | `alpha_research.promotion_gate_thresholds` |

## Evidence

### Repo-local scan

A 2026-09-02 code search of `strategy-pipeline` found no production caller importing any of the five facade module paths. The remaining references are the facade files themselves, compatibility/governance tests, namespace smoke coverage, test-impact mappings, and historical/evidence text.

The caller migration was already completed by strategy-pipeline commit `dcc4af707724bed09abb930e131db6310b1a3939` / PR #43 on 2026-08-10. That commit explicitly redirected production `promotion_gate` and `freshness_overlay` callers to `alpha_research.*` and recorded that the train/eval and threshold facades were already owner-delegating with production callers ready for removal.

### Downstream scan

A 2026-09-02 code search across the connected repositories below found no runtime import of the five `strategy_pipeline` facade paths:

- `strategy-app`
- `alpha-research`
- `market-data-platform`
- `portfolio-backtester`
- `research-workspace`

Workspace references are governance records, maintainability evidence, and removal checklists rather than runtime consumers.

### Replacement documentation

`docs/compatibility-facades.yml` already records the direct `alpha_research.*` replacement for each facade. No new compatibility package is required.

### Focused tests

Removal must preserve owner tests and pipeline namespace/import smoke. Pipeline tests that intentionally import a facade only to prove compatibility should be deleted or redirected to the owner API in the deletion PR; they are not evidence of a real downstream consumer.

### Rollback

If removal exposes an unobserved external consumer, restore the exact wrapper from the previous `strategy-pipeline` release tag while that consumer migrates to the documented `alpha_research.*` owner API. Do not add a second replacement facade.

## Removal decision

The technical consumer audit is complete and reports zero runtime consumers. The files are therefore **code-ready for deletion**, but the registry's explicit removal condition still requires two release reviews. This audit does not reinterpret elapsed time or ordinary commits as release reviews.

Deletion should occur in the first strategy-pipeline release review that can document satisfaction of the remaining review-count condition. That deletion PR should:

1. delete all five wrapper modules as one compatibility batch;
2. remove/update pipeline tests and namespace smoke entries that protect the wrappers themselves;
3. remove the five records from `docs/compatibility-facades.yml` in the same workspace synchronization;
4. remove any corresponding strategy-pipeline import-boundary debt entries;
5. rerun repo-local and downstream scans before merge;
6. retain this audit as evidence rather than rewriting history.

## Separate unregistered root wrappers

`strategy_pipeline.return_metrics`, `strategy_pipeline.sharpe_stats`, and `strategy_pipeline.liquidity_proxy` were also inspected. Searches found no real downstream runtime consumers; current references are migration/archive documentation, boundary rules, or ownership tests. They are not part of the five registered alpha facades above and require their own registry/release-policy decision before deletion.
