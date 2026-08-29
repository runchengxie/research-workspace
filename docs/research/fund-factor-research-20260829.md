# Public-fund ownership factor research record

Date: 2026-08-29  
Status: exploratory only  
Decision: do not promote to production

## Research question

Does gradual public-fund accumulation predict subsequent stock returns, especially
when current fund ownership is still low and the position is not highly concentrated
among the top ten funds?

## Tested signals

| Model | Definition |
| --- | --- |
| M0 | Top quintile of change in the number of funds holding the stock |
| M1 | Change in fund ownership ratio |
| M2 | Low current fund ownership/crowding |
| M3 | M0 and ownership-ratio change both in the top quintile |
| M4 | Low crowding plus accumulation with a top-ten concentration constraint |

The portfolio shadow used the latest disclosed state, an equal-weight top-quintile
portfolio, strict `available_date <= trade_date` filtering, a matched equal-weight
A-share benchmark, and 30 bps turnover cost.

## Main evidence

In the original 2025–2026 shadow, M0 and M3 both lost to the matched benchmark in
2026. M0 had approximately `-7.5%` active return after cost and M3 approximately
`-6.0%`. M3 also had higher mean daily turnover (about 9.0% versus 7.5% in 2026).

The frozen 2026 final-OOS block bootstrap gave:

| Model | Net annualized return | Active return after cost | Positive active-mean probability |
| --- | ---: | ---: | ---: |
| M0 | -34.6% | -7.5% | 0.7% |
| M3 | -32.4% | -6.0% | 3.0% |

As a window-stability check, the existing derived asset was evaluated from
2022-01-01 onward, excluding the oldest suspect periods from the evaluation window.
This was not a newly rebuilt raw asset, so it is sensitivity evidence rather than a
fully clean PIT result. M0 still underperformed after cost in every year from 2022
through 2026, with active returns of approximately `-27.5%`, `-11.4%`, `-4.9%`,
`-2.5%`, and `-7.9%`. M3 showed the same pattern.

Industry/size-neutral event scans and Shibor-conditioned scans did not establish a
stable independent effect. A CPCV-style fixed-model selection diagnostic produced
positive test active returns on only 40% of paths; this is not formal CPCV/PBO
certification, but it is a stability warning.

## Data-quality and PIT findings

The derived feature asset passes the publication-date PIT checks:

- 0 missing PIT dates;
- 0 invalid `disclosure_date` → `available_date` → `trade_date` orderings;
- 0 duplicate stock/trade-date feature rows;
- 0 rows whose available date was not the next available trading date.

The raw TuShare holdings asset contains 197 duplicate logical rows. Of these, 34
are exact duplicates and 163 contain conflicting holding values. The conflicts are
concentrated in report periods from 2017-06 through 2021-06 and affect approximately
35 funds and 116 stocks. Several examples have market value and share count close
to a 2x relationship while percentage fields differ. The available schema does not
contain enough page or revision evidence to select a correct row.

The upstream loader now removes exact duplicates and fails closed on conflicting
keys. New pulls record retrieval/vintage metadata, but the existing historical asset
does not contain a complete vintage ladder. Consequently the feature is classified
as `publication_date_pit`, not fully `revision_safe`.

## Interpretation

The research does not support the claim that public-fund accumulation is a standalone
stock-selection Alpha. The current result is more consistent with a time-varying
market/style or implementation exposure, with possible contamination from historical
source-quality issues.

This does not make the feature useless. It may still be worth testing as an
auxiliary variable inside a stronger model, for example:

```text
PIT fundamental quality
+ industry/earnings context
+ fund-holder-count change
+ price/volume confirmation
```

It should not be used as the primary ranking signal until a clean historical asset
and a new out-of-sample result justify that use.

## Decision and next steps

1. Keep the audit, duplicate guard, and provenance changes.
2. Re-fetch or quarantine the conflicted historical periods rather than inventing a
   deterministic correction.
3. Rebuild from the first clean quarter with a clean warm-up period.
4. Re-run the full PIT, final-OOS, cost, capacity, and robustness protocol.
5. If revisited, test the fund features as conditional or auxiliary features, not
   as a standalone production strategy.

Relevant implementation: [context shadow experiment](../../strategy-research/experiments/macro_context_shadow/README.md).  
Upstream data-quality fix: [market-data-platform PR #65](https://github.com/runchengxie/market-data-platform/pull/65).  
Research integration: [research-workspace PR #251](https://github.com/runchengxie/research-workspace/pull/251).
