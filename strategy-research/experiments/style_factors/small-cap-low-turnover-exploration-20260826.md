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
- Cost case: 10 bps per unit of simulated traded notional.
- Eligibility: minimum 180 listed days, non-ST, non-suspended, and present in the formation universe.
- Arms: small-cap, raw low-turnover, low-turnover residualized against size and low volatility, raw 50/50 composite, residualized 50/50 composite, large-cap control, and low-volatility control.

## Full-period result

Values below are annualized return or turnover unless stated otherwise. Returns are net of the 10 bps research cost case.

| arm | net return | net Sharpe | max drawdown | annualized turnover |
| --- | ---: | ---: | ---: | ---: |
| small-cap | 1.66% | 0.20 | -74.67% | 2.97x |
| low-turnover | 3.40% | 0.26 | -54.49% | 6.70x |
| low-turnover residual | -11.69% | -0.25 | -90.08% | 19.13x |
| raw composite | 8.77% | 0.43 | -57.28% | 5.78x |
| residual composite | 4.31% | 0.29 | -73.23% | 14.96x |
| large-cap control | 6.72% | 0.41 | -44.05% | 1.40x |
| low-volatility control | 0.27% | 0.13 | -67.81% | 16.96x |

## What the result says

1. Raw low-turnover is not useless in this test, but its standalone result is modest and turnover is still high for a supposedly slow strategy.
2. The raw composite beats the large-cap control over this window, but the difference is not enough to call it robust: drawdown is severe, the sample is regime-sensitive, and the result is affected by the 2025 run.
3. Residualizing low-turnover against size and low volatility destroys the standalone result. This is evidence that the observed low-turnover payoff is not an independent linear premium under this specification.
4. Low-turnover has a mean cross-sectional correlation of about `0.48` with the low-volatility control. After residualization, the correlation with size and low volatility is approximately zero by construction, but the residual portfolio performs poorly.
5. The result does not prove that low-turnover is “fake.” It says that a production thesis should not claim an independent low-turnover premium without additional controls, alternative definitions, and investability evidence.

## Regime check

The raw composite net returns were approximately:

| period | raw composite | large-cap control |
| --- | ---: | ---: |
| 2015–2019 | +84.1% | +45.4% |
| 2020–2023 | -7.3% | +13.9% |
| 2024–2026 | +48.1% | +23.7% |

The positive full-period result is therefore not uniform across regimes.

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
- `candidate_target_counts.csv`
- `candidate_signal_panel.parquet`
- `small_cap_low_turnover_exploration.md`
- `exploration_meta.json`

## Remaining limitations

- The simulator uses continuous portfolio weights and does not round to the A-share 100-share lot size.
- The 10 bps cost case is a sensitivity case, not a broker-specific execution model.
- The loaded reconstructed PIT contract reports that historical revision safety is not complete.
- The experiment does not yet include capacity limits, ADV participation limits, or a live paper-trading observation period.
- No final-OOS parameter selection, strategy registration, or E2 audit was performed.

## Recommended next step

Do not promote this composite yet. The next research step should be a pre-registered robustness matrix: alternative turnover windows and medians, explicit liquidity/ADV participation caps, integer-lot rounding, and a walk-forward holdout. The decision criterion should be incremental net performance versus the large-cap control after these constraints, not the raw full-period return.
