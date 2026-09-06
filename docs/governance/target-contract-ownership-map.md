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
| `watchlist_20.csv` and `selection_receipt.json` | `strategy-pipeline` + `strategy-app` | `quant-research/strategies/daily_watch20` produces the private projection; `quant-platform/publication` supplies generic bundle mechanics | `market-intel` | Strategy-specific selection and receipt remain private; only the versioned file bundle crosses the application boundary |
| Generic publication manifest and file hashing | `research_contracts` in the workspace | `quant-platform/research_contracts` | `quant-research`, `market-intel`, other approved consumers | Public mechanism only; no strategy selection, provider, credential, or real data |
| DailyWatch20 rendering and delivery | `market-intel` | `market-intel` | end users | Independent application; no import from `quant-research` |
| Version combination and compatibility smoke tests | `research-workspace` | `research-workspace` thin layer | release process | Records compatible commits and rollback pointers; does not own strategy logic |

## Consequence

`quant-research` owns the private strategy logic and strategy-specific projection. The public
platform supplies generic manifest construction, relative-path validation, hashing, and atomic
bundle mechanics; it does not decide which symbols are selected. `market-intel` consumes only the
versioned file bundle. This preserves the existing producer/consumer contract without exposing the
strategy edge through a public orchestration package.

## Verification evidence

The independent `market-intel` worktree branch `feat/architecture-boundary` contains commit
`312efa2`, which adds `tests/test_research_artifact_boundary.py`. The test passes and enforces that
the consumer has no `quant_research` import and documents versioned-artifact consumption.
