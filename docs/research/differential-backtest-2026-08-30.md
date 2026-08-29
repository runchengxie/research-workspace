# Differential backtest smoke check

## Scope

This is a small CPU-only contract check for the connection between `alpha-research` and
`portfolio-backtester`. It is not a production performance result and does not use model training.

## Test

The same synthetic four-date, three-symbol score and close-price frame was run in two ways:

1. Directly through `portfolio_backtester.engine.backtest_topk`.
2. Through `alpha_research.walk_forward._evaluate_injected_walk_forward_backtest`, with the
   same `backtest_topk` function supplied through the research service hook.

The configuration used top-1 selection, same-day execution, 10 bps cost, and 52 periods per year.

## Result

The two paths matched exactly:

- net returns: `0.099, 0.000, 0.018408163265306143`
- gross returns: `0.100, 0.000, 0.020408163265306145`
- turnover: `1.0, 0.0, 1.0`

The result was recorded in `/tmp/differential-backtest-20260830.json`.

## Interpretation

`alpha-research` currently does not contain a second independent portfolio backtester. It produces
research signals and injects the portfolio backtester as a service. Therefore this check validates
the integration contract and parameter forwarding. A future comparison of two independent engines
would require implementing a deliberately separate reference calculator, which is not necessary
for the current architecture.

## Next step

Add one more fixture with delayed execution, fees, and missing prices before using the adapter for
larger research runs.
