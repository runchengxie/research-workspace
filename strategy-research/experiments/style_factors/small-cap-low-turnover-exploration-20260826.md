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
- Arms: small-cap, raw low-turnover, low-turnover residualized against size and low volatility, raw 50/50 composite, residualized 50/50 composite, large-cap control, and low-volatility control.
- Robustness matrix: raw composite only, 100m CNY research capital, 100-share lot rounding, and unconstrained/5%/10%/20% prior-session traded-amount cases (not rolling ADV).
- Development window: 2015–2023. Fixed holdout: 2024–2026. No parameter was selected from the holdout.

## Full-period result

Values below are annualized return or turnover unless stated otherwise. Returns are net of the 10 bps research cost case.

| arm | net return | net Sharpe | max drawdown | annualized turnover |
| --- | ---: | ---: | ---: | ---: |
| small-cap | 1.66% | 0.20 | -74.67% | 2.97x |
| low-turnover | 5.44% | 0.33 | -51.84% | 6.79x |
| low-turnover residual | -10.11% | -0.18 | -88.44% | 19.22x |
| raw composite | 7.24% | 0.38 | -68.59% | 6.77x |
| residual composite | 4.22% | 0.29 | -75.23% | 15.42x |
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
- `candidate_target_counts.csv`
- `candidate_signal_panel.parquet`
- `small_cap_low_turnover_exploration.md`
- `exploration_meta.json`

## Remaining limitations

- The baseline simulator uses continuous portfolio weights. The sensitivity cases round target entry weights to 100-share lots using the prior close, but the daily weight-accounting engine is not a full share-ledger simulator.
- Participation caps use prior observed traded amount, constant research capital, and per-symbol static weight caps; this is not rolling ADV and does not model market impact, portfolio cash evolution, or broker fills.
- The 10 bps cost case is a sensitivity case, not a broker-specific execution model.
- The loaded reconstructed PIT contract reports that historical revision safety is not complete.
- The experiment does not yet include dynamic capacity, broker-specific fills, or a live paper-trading observation period.
- No final-OOS parameter selection, strategy registration, or E2 audit was performed.

## Recommended next step

Do not promote this composite yet. The next research step should replace the weight-level approximation with a share-ledger/backtest that models cash, lot rounding, T+1 inventory, ADV participation, and slippage. The decision criterion should be incremental net performance versus the large-cap control after those constraints, not the raw full-period return.
