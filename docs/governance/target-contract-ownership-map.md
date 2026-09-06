# Target contract ownership map

> status: migration target
> verified: 2026-09-06
> source_of_truth: target-state governance map

This map separates strategy IP from the artifact producer and the artifact consumer. The current
repository names remain authoritative until the corresponding migration gate passes.

| Contract or responsibility | Current owner | Target owner | Consumer | Boundary rule |
| --- | --- | --- | --- | --- |
| Strategy identity, thesis, lifecycle and evidence navigation | `strategy-research` | `quant-research/registry` | research users and governance | Private; never inferred from runtime code location |
| DailyWatch20 strategy-specific calculation | `strategy-app` | `quant-research/strategies/daily_watch20` | orchestration layer | Private; keeps the transitional `strategy_app.daily_watch20` namespace initially |
| `watchlist_20.csv` and `selection_receipt.json` | `strategy-pipeline` | `quant-platform/orchestration` | `market-intel` | Versioned artifact; producer validates strategy output and publishes atomically |
| DailyWatch20 rendering and delivery | `market-intel` | `market-intel` | end users | Independent application; no import from `quant-research` |
| Version combination and compatibility smoke tests | `research-workspace` | `research-workspace` thin layer | release process | Records compatible commits and rollback pointers; does not own strategy logic |

## Consequence

`quant-research` does not need to become an artifact-serving application. It supplies private
strategy logic and research metadata to the orchestration layer through a stable API or an explicit
handoff. The orchestration layer produces the formal public artifact, and `market-intel` consumes
only that artifact. This preserves the existing producer/consumer contract while moving repository
boundaries incrementally.

## Verification evidence

The independent `market-intel` worktree branch `feat/architecture-boundary` contains commit
`312efa2`, which adds `tests/test_research_artifact_boundary.py`. The test passes and enforces that
the consumer has no `quant_research` import and documents versioned-artifact consumption.
