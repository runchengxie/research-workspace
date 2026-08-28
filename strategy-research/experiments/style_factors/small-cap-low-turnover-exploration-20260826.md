# Small-cap × low-turnover exploration — 2026-08-26

## Question

Does a small-cap plus low-turnover signal provide useful incremental evidence for an actual long-only strategy, or is the low-turnover effect mainly a proxy for size, low volatility, or another exposure?

This remains an exploration. It is not a strategy-catalog entry and does not trigger E2.

## Pre-declared design

- Data window: 2015-01-05 to 2026-07-31.
- Formation: monthly, using the point-in-time formation universe.
- Turnover: mean `turnover_rate` over the prior 60 trading sessions, excluding the formation session.
- Ranking: sector-neutral cross-sectional scores.
- Portfolio: long-only, equal weight, 40-name target, 60-name holding buffer.
- Execution: target changes on the next trading session; shared suspension, price-limit, delisting, and transaction-cost mechanics.
- Sensitivity execution inputs: prior-session close for lot sizing and prior observed traded amount for participation caps.
- Cost case: 10 bps per unit of simulated traded notional.
- Eligibility: minimum 180 listed days, non-ST, non-suspended, and present in the formation universe.
- Arms: small-cap, raw low-turnover, low-turnover residualized against size and low volatility, low-turnover residualized against size, low volatility, and one-hot industry dummies, raw 50/50 composite, residualized 50/50 composite, industry-residualized 50/50 composite, large-cap control, and low-volatility control.
- Robustness matrix: raw composite only, 100m CNY research capital, 100-share lot rounding, and unconstrained/5%/10%/20% prior-session traded-amount cases (not rolling ADV).
- Rebalance-frequency matrix: raw composite only, weekly/biweekly/monthly/quarterly formation, monthly as the baseline cadence, with the same sector-neutral controls and cost mechanics.
- Share-ledger check: raw composite re-run through the portfolio-backtester cash-ledger execution model (lot rounding, T+1 inventory, participation caps, daily NAV) for the monthly and biweekly cadences, using 5% participation and the same 10 bps cost case.
- Execution adapter check: the runner now normalizes buffered targets into the owner's `positions_by_rebalance` contract and runs a parallel native period replay for comparison. Owner ledger replay remains an explicit opt-in because running two full ledgers doubles the experiment cost; it is covered separately by adapter tests.
- Impact sensitivity: `--impact-bps` enables the owner's participation-based slippage model on the share-ledger matrix. The model uses traded amount in the source data's thousand-CNY unit and records model costs in `temporary_impact`; the default remains `0` for historical comparability.
- Ledger reconciliation: identical targets run through a weight-level reference, a frictionless ideal NAV with share semantics, and the fully constrained ledger, plus a one-constraint-at-a-time relaxation ladder (participation, T+1, lot, cost) on the monthly composite; composite and large-cap control are both reconciled so the incremental criterion can be read under each engine.
- Capital ladder: the monthly raw composite under the fully constrained ledger at 10m, 100m, and 500m CNY research capital, holding participation at 5% so per-name capacity tightens mechanically with size.
- Joint matrix: four turnover lookback definitions crossed with weekly/biweekly/monthly/quarterly cadences on the raw composite with the weight-level screening engine; this fills the definition × cadence grid that the robustness and rebalance matrices cover only one axis of.
- Development window: 2015–2023. Fixed holdout: 2024–2026. No parameter was selected from the holdout.

## Full-period result

Values below are annualized return or turnover unless stated otherwise. Returns are net of the 10 bps research cost case.

| arm | net return | net Sharpe | max drawdown | annualized turnover |
| --- | ---: | ---: | ---: | ---: |
| small-cap | 1.66% | 0.20 | -74.67% | 2.97x |
| low-turnover | 5.44% | 0.33 | -51.84% | 6.79x |
| low-turnover residual | -10.11% | -0.18 | -88.44% | 19.22x |
| low-turnover residual (industry) | -7.73% | -0.09 | -84.65% | 19.95x |
| raw composite | 7.24% | 0.38 | -68.59% | 6.77x |
| residual composite | 4.22% | 0.29 | -75.23% | 15.42x |
| residual composite (industry) | 1.37% | 0.20 | -81.88% | 13.02x |
| large-cap control | 6.72% | 0.41 | -44.05% | 1.40x |
| low-volatility control | 0.27% | 0.13 | -67.81% | 16.96x |

## What the result says

1. Raw low-turnover is not useless in this test, but its standalone result is modest and turnover is still high for a supposedly slow strategy.
2. The raw composite beats the large-cap control over this window, but the difference is not enough to call it robust: drawdown is severe, the sample is regime-sensitive, and the result is affected by the 2025 run.
3. Residualizing low-turnover against size and low volatility destroys the standalone result. This is evidence that the observed low-turnover payoff is not an independent linear premium under this specification.
4. Low-turnover has a mean cross-sectional correlation of about `0.48` with the low-volatility control. After residualization, the correlation with size and low volatility is approximately zero by construction, but the residual portfolio performs poorly.
5. Adding one-hot industry dummies to the residualization changes the standalone arm modestly (-10.11% to -7.73%) and weakens the residual composite further (4.22% to 1.37%). The industry-residual signal is about `0.9995` correlated with the plain residual, because the raw signals are already sector-neutral z-scored. Industry neutralization therefore does not rescue the deconfounded low-turnover arm.
6. The result does not prove that low-turnover is “fake.” It says that a production thesis should not claim an independent low-turnover premium without additional controls, alternative definitions, and investability evidence.

## Regime check

The raw composite net returns were approximately:

| period | raw composite | large-cap control |
| --- | ---: | ---: |
| 2015–2019 | +109.2% | +45.4% |
| 2020–2023 | -33.1% | +13.9% |
| 2024–2026 | +54.4% | +23.7% |

The positive full-period result is therefore not uniform across regimes.

## Robustness matrix

The table below shows the unconstrained and 5% prior-session traded-amount cases. The 10% and 20% cases are in `candidate_robustness_matrix.csv`.

| turnover definition | unconstrained net | 5% prior-amount net | unconstrained holdout | 5% prior-amount holdout | turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| mean 20-day | +7.46% | +11.73% | +25.22% | +27.23% | 8.61x |
| mean 60-day | +7.28% | +10.23% | +19.16% | +19.40% | 6.78x |
| median 60-day | +7.45% | +10.14% | +20.14% | +20.87% | 6.64x |
| mean 120-day | +13.70% | +15.33% | +25.12% | +26.74% | 5.59x |

The prior-session traded-amount caps did not monotonically reduce returns. In this simulator they change the order-fill path: delayed entries and exits can avoid some losing trades. That is an execution-path sensitivity, not evidence that greater constraints create investable alpha.

## Rebalance-frequency check

The raw composite was run at four formation cadences with the same sector-neutral controls, buffer, cost, and eligibility mechanics.

| frequency | formation dates | net annual | net Sharpe | max drawdown | annualized turnover | development annualized | holdout annualized |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| weekly | 592 | 9.20% | 0.44 | -61.68% | 5.17x | 5.98% | 21.07% |
| biweekly | 296 | 18.87% | 0.70 | -59.68% | 3.25x | 17.69% | 23.04% |
| monthly | 139 | 7.24% | 0.38 | -68.59% | 6.77x | 4.01% | 19.16% |
| quarterly | 47 | 8.11% | 0.41 | -64.99% | 4.24x | 2.93% | 27.87% |

Biweekly formation is the standout in this test: it roughly doubles the monthly net return while cutting annualized turnover in half, and it is the best in both the development and the holdout windows. Weekly is weaker than monthly on full-period net return, and quarterly is similar to monthly on the full period but stronger in the holdout. The biweekly advantage may come from more frequent refreshes reducing stale positioning under the buffer, but it remains a single-simulator result with a deep drawdown and the same execution-path caveats. No cadence was selected from the holdout.

## Share-ledger execution check

The raw composite was re-run through the portfolio-backtester cash-ledger execution model for the monthly and biweekly cadences, with 100m CNY capital, 5% participation on prior traded amount, 100-share lots, T+1 inventory, and the same 10 bps cost case.

| frequency | share-ledger net annual | share-ledger Sharpe | share-ledger max drawdown | fill ratio | avg cash weight | cumulative turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| monthly | 16.01% | 0.70 | -51.10% | 44.98% | 11.62% | 147.9x |
| biweekly | 14.14% | 0.63 | -59.34% | 75.40% | 21.14% | 69.5x |

The share-ledger result differs materially from the weight-level engine; the reconciliation section below decomposes that gap and supersedes the interpretation of this table on its own.

## Ledger reconciliation

Identical formation targets were run through three engines: the weight-level simulator, a frictionless ideal NAV with share semantics, and the fully constrained cash ledger, plus a one-constraint-at-a-time relaxation ladder on the monthly composite.

Monthly raw composite:

| engine arm | net annual | net Sharpe | max drawdown | avg cash weight |
| --- | ---: | ---: | ---: | ---: |
| weight_level | 7.24% | 0.38 | -68.59% | fully invested by assumption |
| ideal_nav (share semantics, zero friction) | 11.95% | 0.57 | -51.86% | ~0% |
| ledger_full | 16.01% | 0.70 | -51.10% | 11.62% |

Relaxation ladder on the monthly composite: removing the participation cap lowers the result to 14.56%, disabling T+1 changes nothing, disabling lot rounding adds about 0.01pp, and zero cost adds about 0.56pp versus the constrained ledger.

What the decomposition says:

1. Accounting semantics dominate the old numbers. Moving from daily-renormalized constant weights to held shares lifts the monthly composite by about 4.7pp annualized before any friction change, so the previously reported weight-level results structurally understated this strategy family.
2. Execution constraints raise the simulated composite result by another 4.1pp, and the sign is diagnostic: relaxing participation lowers it to 14.56%. Delayed, partial fills into illiquid small caps dodge losers in this simulator. The large-cap control behaves normally instead: its three engines sit within about 0.3pp (6.72% / 6.63% / 6.41%) with monotone decay, so the composite's constraint gain is specific to the illiquid tail where participation binds (45% fill versus 80% for the control) and must be treated as an execution-path artifact, not alpha.
3. T+1 and lot rounding are second order here; costs are worth about 0.56pp annualized at 10bps.
4. The biweekly-versus-monthly ranking reversal resolves: under share semantics the monthly ledger (16.01%) beats the biweekly ledger (14.14%), so the biweekly advantage was an artifact of the weight-level engine's daily renormalization interacting with cadence.
5. The decision criterion flips with the engine. Incremental composite minus large-cap control is about +0.5pp under the weight-level engine but +5.3pp under ideal NAV and +9.6pp under the constrained ledger. The earlier reading that the composite barely beats the control was engine-specific.

Engine trust going forward: share-semantics engines (ideal or constrained ledger) are the decision basis for costs, capacity, and cadence; the weight-level engine remains useful only for cheap screening. The constrained ledger now has an opt-in participation-based slippage sensitivity, but the impact case has not yet been propagated through the reconciliation and capital-ladder matrices, so those results remain an optimistic upper bound until that comparison is complete.

## Capital ladder (ledger)

The monthly raw composite was scaled across research capital on the fully constrained ledger engine.

| capital | net annual | net Sharpe | max drawdown | fill ratio | avg cash weight | cumulative turnover |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10m CNY | 15.85% | 0.67 | -51.48% | 33.17% | 0.58% | 138.5x |
| 100m CNY | 16.01% | 0.70 | -51.10% | 44.98% | 11.62% | 147.9x |
| 500m CNY | 13.40% | 0.68 | -49.86% | 30.96% | 36.85% | 87.0x |

Capacity degrades by under-deployment rather than collapse: at 500m CNY the book averages 37% cash because per-name participation caps bind harder, and net return eases to about 13.4%. Sharpe is remarkably stable across the ladder. The non-monotonic step from 10m to 100m is fill-path noise, not a scaling law. This ladder holds the strategy fixed and varies capital in the static-capacity approximation, so it bounds capacity rather than pricing it.

## Turnover-definition × cadence matrix

The joint grid ran on the weight-level screening engine; after the reconciliation finding that this engine distorts cadence rankings, cell rankings here are screening observations that require ledger-engine confirmation before any selection.

| definition | cadence | net annual | Sharpe | turnover | dev annualized | holdout annualized |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| mean_120 | biweekly | 21.25% | 0.75 | 3.11x | 20.82% | 22.77% |
| mean_60 | biweekly | 18.87% | 0.70 | 3.25x | 17.69% | 23.04% |
| median_60 | biweekly | 18.53% | 0.69 | 3.24x | 17.29% | 22.93% |
| mean_20 | biweekly | 16.99% | 0.65 | 3.67x | 16.43% | 18.95% |
| mean_120 | monthly | 13.59% | 0.57 | 5.57x | 10.45% | 25.13% |
| mean_120 | weekly | 13.10% | 0.55 | 4.71x | 10.04% | 24.31% |
| mean_120 | quarterly | 10.46% | 0.48 | 4.21x | 6.07% | 26.85% |

Two patterns are consistent across the whole grid rather than isolated-cell luck: mean-120 dominates every cadence it appears in, and within any definition the biweekly cadence leads the full period and the development window (the best cell also leads its development window at 20.82%, so a development-only selection rule would pick it). The holdout column has been inspected repeatedly across these matrices and is degraded as clean final out-of-sample; treat it as descriptive only.

## Evidence files

The runner is:

`python experiments/style_factors/small_cap_low_turnover_exploration_20260826.py`

It writes the following outputs when given `--data-root` and `--outdir`:

- `candidate_summary.csv`
- `candidate_daily.csv`
- `candidate_yearly_returns.csv`
- `candidate_regime_returns.csv`
- `candidate_signal_correlations.csv`
- `candidate_net_correlations.csv`
- `candidate_robustness_matrix.csv`
- `candidate_rebalance_matrix.csv`
- `candidate_share_ledger_matrix.csv`
- `candidate_reconciliation_matrix.csv`
- `candidate_capacity_ladder.csv`
- `candidate_joint_matrix.csv`
- `candidate_size_turnover_double_sort.csv`
- `candidate_delayed_fill_attribution.csv`
- `candidate_target_counts.csv`
- `candidate_signal_panel.parquet`
- `small_cap_low_turnover_exploration.md`
- `exploration_meta.json`

## Remaining limitations

- The baseline simulator uses continuous portfolio weights; the reconciliation shows its semantics understate this strategy family, so weight-level rows are screening references only.
- Participation caps use prior observed traded amount, constant research capital, and per-symbol static weight caps; this is not rolling ADV or a broker fill model. The optional participation-based slippage sensitivity prices the requested fill amount against that same source liquidity measure, but is not a full impact calibration.
- The reconciliation attributes the composite's constraint-induced gain to delayed fills in the illiquid tail. The impact sensitivity now propagates through the share-ledger, reconciliation, and capital-ladder outputs, but it remains a parameterized sensitivity rather than a broker-calibrated impact curve.
- Delayed-fill attribution reports execution-path evidence: positive `delay_opportunity_cost` means the requested side moved against the unfilled quantity before its first fill; negative means the delay helped. Neither should be counted as signal alpha.
- The owner native backend now supports the same slippage model in ledger mode and emits a capability receipt, but it remains comparison-only until dates, exits, cash, fills, and costs reconcile with the constrained ledger.
- The 10 bps cost case is a sensitivity case, not a broker-specific execution model.
- The loaded reconstructed PIT contract reports that historical revision safety is not complete.
- The experiment does not yet include dynamic capacity, broker-specific fills, or a live paper-trading observation period.
- The 2024–2026 holdout has now been inspected by several sensitivity matrices in this exploration; it is degraded as a clean final out-of-sample window, and future parameter decisions should be made on the 2015–2023 development window only.
- No final-OOS parameter selection, strategy registration, or E2 audit was performed.

## Recommended next step

Do not promote this composite yet. The next decision basis is the constrained ledger with impact enabled: inspect the delay attribution, compare incremental net performance versus both controls, and use the double-sort to test whether low turnover is conditional on small size. Any cadence or definition choice must be justified on the 2015–2023 development window only. Promote the owner backend only after it reproduces these same comparisons and accounting semantics.
