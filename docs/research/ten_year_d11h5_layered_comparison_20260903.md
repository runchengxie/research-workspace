# Ten-year D11-H5 layered comparison — 2026-09-03

## Status

Research-only. No production promotion.

The first historical file named `historical_scores_D11_20.parquet` under
`daily_watch20_historical_backfill_2015_20260902` was rejected as an input for
this comparison. Its 2026 scores matched the DailyWatch20 raw score exactly,
and its monthly rank correlation with DailyWatch20 was effectively one. It is
retained as historical evidence, but is not used below.

## Correct D11-H5 ladder

The replacement ladder is under
`ten_year_d11h5_20260903/d11_ladder_true_120d/`.

- 1,878,400 rows across 2,348 trading dates;
- 2017-01-03 through 2026-09-02;
- exactly 800 rows per date and zero duplicate `(trade_date, symbol)` keys;
- limit-aware D11-D20 incremental-return target;
- 504-date training window and strict label-end OOS rule;
- 120-session rolling refit blocks for this long diagnostic.

This is approximately 9.7 years of D11 score coverage, but the common
fundamental comparison begins on 2018-03-30 because the fundamental ladder has
fewer than 20 eligible names before that date. The 120-session refit cadence is
strictly OOS, but differs from the current 40-session production/shadow
cadence; this is therefore a historical research diagnostic, not a production
replica.

On the overlapping 2026 monthly dates, the correct D11 score had rank
correlation around 0.65–0.68 with DailyWatch20 and Top20 overlap of 3–8 names,
confirming that it is not the same signal.

## Common-condition replay

Artifact: `ten_year_d11h5_20260903/unified_monthly_replay_true_d11/`.

All arms use the same 103 monthly formation dates from 2018-03-30 through
2026-09-01, the same stock-date intersection, Top20, one-session execution
shift, incumbent buffer of 15, 25bp transaction cost, close pricing, and 5th
percentile amount liquidity floor.

| Arm | Total return | Annualized return | Sharpe | Max drawdown | Avg turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fundamental only | -15.75% | -2.09% | 0.037 | -39.99% | 0.203 |
| DailyWatch20 only | -54.55% | -9.27% | -0.152 | -74.88% | 0.514 |
| D11-H5 only | -37.83% | -5.69% | -0.017 | -60.80% | 0.487 |
| Fundamental + DailyWatch20 | -38.48% | -5.82% | -0.156 | -55.75% | 0.253 |
| Fundamental + D11-H5 | -37.53% | -5.64% | -0.125 | -50.72% | 0.246 |
| DailyWatch20 + D11-H5 | -40.69% | -6.24% | -0.051 | -66.00% | 0.455 |
| Three-way | -35.34% | -5.24% | -0.114 | -51.65% | 0.233 |

The common-period result does not support production promotion. The
fundamental arm is the least bad of these long-window arms, while D11-H5 is
meaningfully different from DailyWatch20 but does not improve the fundamental
blend enough to produce a positive result. The result is diagnostic, not proof
that either the fundamental thesis or D11-H5 is permanently invalid.

## Remaining limitations

1. The common replay has only 102 realized holding periods after the first
   formation; it is not a substitute for future live maturity.
2. The historical D11 ladder uses a 120-session refit block for tractability;
   an exact 40-session historical replay remains a separate robustness check.
3. The fundamental ladder is sparse before 2018-03-30, so the strict common
   comparison cannot claim a full 2016–2026 four-way sample.
4. Industry-neutral and size-neutral variants were not folded into this one
   common table; they remain follow-up diagnostics.

## Reproduction

The model-frame builder is
`tools/ten_year_d11h5/build_historical_model_frame.py`; the common replay
runner is `tools/ten_year_d11h5/run_unified_monthly_replay.py`. Both write
research-only artifacts and do not modify published strategy state.
