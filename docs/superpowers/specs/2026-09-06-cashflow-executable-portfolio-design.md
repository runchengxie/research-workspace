# Cashflow Executable Portfolio and Feishu Chart Design

**Date:** 2026-09-06
**Status:** Proposed for implementation
**Scope:** Research/shadow only; no live trading or production eligibility change

## Goal

Extend the cash-flow strategy from a research-only Top 50 ranking into a price-aware, lot-rounded executable portfolio for a RMB 500,000 reference account, and publish a concise Feishu chart that makes the distinction between research weights and executable trades explicit.

## Non-goals

- This change does not make the strategy production eligible.
- This change does not remove the reconstructed-PIT warning or relax existing publication gates.
- This change does not place orders or connect to a brokerage account.
- This change does not replace the Top 50 research ranking or change its factor definition.

## Design

The system will produce two related artifacts:

```text
Top 50 research ranking
        ↓
price-aware executable portfolio
        ↓
Feishu Markdown + PNG chart
```

The research selection remains the source of factor evidence. A separate execution layer converts the research selection into a portfolio that respects reference capital, 100-share purchase lots, cash reserve, stock caps, and industry caps. Both artifacts remain research-only.

### Execution policy

The initial default policy is:

- Reference portfolio value: RMB 500,000.
- Research candidate universe: Top 50.
- Maximum executable holdings: 25.
- Cash reserve: 3% of portfolio value.
- Maximum single-stock target weight: 8%.
- Minimum target position value: RMB 10,000.
- Maximum industry weight: 25%.
- Purchase lot size: 100 shares.

The policy must be configurable and included in the output receipt. The implementation must reject invalid policy combinations rather than silently adjusting them.

### Price input

The execution layer consumes a price snapshot with at least:

```text
symbol, price, price_date
```

The price snapshot is immutable for a run, its SHA-256 is recorded, and the artifact records whether `price_date` equals the signal date or is the most recent available trading date. Missing, non-positive, duplicated, or stale prices are execution blockers for the affected symbols and are recorded explicitly.

### Portfolio construction

The layer will:

1. Start from the research-ranked candidates.
2. Join prices by normalized symbol.
3. Remove candidates that fail price, eligibility, minimum-position, or required metadata checks, recording reasons.
4. Select at most the configured maximum number of executable holdings while preserving research rank order as the deterministic tie-breaker.
5. Allocate the investable capital subject to the single-stock and industry caps.
6. Convert target amounts to whole 100-share purchase lots.
7. Recalculate actual amounts, actual weights, weight deviations, invested capital, and residual cash.
8. Emit a deterministic receipt containing policy, price snapshot identity, selected/skipped symbols, and execution diagnostics.

The result is a research execution simulation, not an order instruction. The output must retain both target and actual fields so rounding effects are auditable.

### Feishu chart and message

The chart will be redesigned for daily reading rather than displaying 50 equally sized bars. It will contain:

- A clear `RESEARCH ONLY / RECONSTRUCTED PIT` status badge.
- Signal date, price date, and reference capital.
- KPI row: executable holdings, invested percentage, cash percentage, largest position, and largest industry.
- Top 10 executable holdings ranked by actual amount or actual weight.
- Top 8 industry allocations plus `Other`.
- A compact execution table with company, code, target amount, actual amount, shares, actual weight, and deviation.
- A footer explaining that the artifact is reconstructed-PIT research output and not a live instruction.

The full research Top 50 and all skipped-symbol reasons remain available in the Markdown/JSON artifact, while the PNG stays legible in Feishu at normal viewing size.

## Interfaces and ownership

- `strategy-app` owns deterministic execution simulation and its receipt because it already owns cash-flow selection and policy contracts.
- `market-intel` owns company-name/industry enrichment, static chart rendering, and Feishu delivery because it already owns the existing cash-flow renderer and delivery path.
- Existing reconstructed-PIT and live-eligibility gates remain unchanged.

## Failure behavior

The execution layer fails closed for missing or invalid portfolio value, invalid policy, missing price snapshot, duplicate symbols, non-positive prices, or an empty executable set. Individual symbol failures are retained as skip diagnostics when a valid executable portfolio can still be built.

The renderer must not imply that a rounded portfolio is live-tradable. It must show research-only status even when all lot calculations succeed.

## Testing and verification

Tests will cover:

- 100-share lot rounding.
- Cash reserve preservation.
- Single-stock and industry caps.
- Maximum executable holdings and deterministic ranking.
- Missing, duplicate, stale, and invalid prices.
- Target-versus-actual amount and weight calculations.
- Skipped-symbol diagnostics.
- Chart KPI and execution-table content.
- Continued reconstructed-PIT and `eligible_for_live=false` labeling.

Validation will run the focused unit suites, relevant existing cash-flow suites, lint checks, and one end-to-end rendering run against the current reconstructed-PIT snapshot. Feishu delivery will remain explicitly authorized test-chat delivery only.
