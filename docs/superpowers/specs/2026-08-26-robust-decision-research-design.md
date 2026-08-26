# Robust Decision Research Design

## Goal

Turn the workspace's existing robustness checks into an explicit decision workflow that can answer three questions:

1. Which observations or market states are credible counterexamples to a research claim?
2. How much predictive advantage survives portfolio construction, costs, capacity and execution assumptions?
3. How should portfolio construction react when the score or expected-return input is uncertain?

The design follows the existing owner boundaries. It adds governance objects at the workspace level, reusable uncertainty transforms in `portfolio-backtester`, and strategy-specific decision-evaluation receipts in `strategy-app`. It does not introduce a new generic robustness framework inside `strategy-research`.

## Principles

- Keep prediction, portfolio construction and execution as separate owners with stable handoffs.
- Treat counterexamples as first-class evidence, not prose in a report.
- Make uncertainty explicit and input-driven. Do not infer a fake uncertainty estimate from an alpha score.
- Prefer small, testable robust transforms before solver-heavy DRO/MILP implementations.
- Keep all new behavior opt-in and preserve existing outputs by default.
- Fail closed on malformed evidence, missing references and non-finite uncertainty inputs.
- Do not claim C&CG, DRO, MILP or Benders support unless the corresponding mathematical problem and solver path actually exist.

## Architecture

```text
alpha-research
  prediction / signal / optional uncertainty estimate
        |
        v
portfolio-backtester
  conservative score or expected-return transform
  existing construction / cost / capacity / exposure / execution simulation
        |
        v
strategy-app
  compare prediction metrics with downstream decision metrics
  emit decision-focused evaluation receipt
        |
        v
strategy-research / workspace governance
  counterexample.v1 records
  claims + cases link to counterexamples
  human decision / lifecycle
```

### 1. Counterexample-driven governance

Add `counterexample.v1` under `strategy-research/schemas/` and store records under `strategy-research/counterexamples/`.

A counterexample record is evidence navigation, not a computation engine. Required fields:

- `counterexample_id`
- `claim_id`
- `scenario_type`
- `summary`
- `as_of`
- `status`
- `severity`
- `stress_dimensions`
- `baseline_metrics`
- `stressed_metrics`
- `failure_conditions`
- `evidence_refs`

`scenario_type` covers `time_window`, `market_regime`, `cost`, `liquidity`, `capacity`, `exposure`, `signal_perturbation`, `correlation`, and `custom`.

The validator must check:

- IDs and dates;
- referenced claim existence;
- non-empty stress dimensions and evidence references;
- unique metric names within baseline/stressed blocks;
- status and severity enums;
- case references to counterexamples actually exist.

`research_case.v1` gains an optional `counterexamples` list. Existing cases remain valid.

### 2. Robust portfolio uncertainty primitives

Add a small public module to `portfolio-backtester` with two box-uncertainty primitives:

- `conservative_score(score, uncertainty, aversion)` computes `score - aversion * uncertainty` elementwise.
- `box_worst_case_return(weights, expected_returns, uncertainty_radius)` computes the long/short-aware worst-case linear return under independent box uncertainty:
  `w·mu - sum(abs(w_i) * radius_i)`.

A DataFrame helper applies the conservative transform without changing candidate row order and can optionally write an output column. Inputs must be finite; uncertainty radii and aversion must be non-negative. The functions do not estimate uncertainty and do not optimize weights.

This is intentionally smaller than DRO. It creates a stable owner-native interface that later optimizers can consume without locking the project into SciPy/CVXPy or a particular ambiguity set.

### 3. Decision-focused evaluation

Add a strategy-app utility that compares a candidate's prediction metrics with downstream decision metrics and emits a typed immutable receipt.

The receipt records:

- candidate identifier;
- prediction metrics;
- decision metrics;
- baseline decision metrics;
- degradation/improvement deltas;
- explicit metric directions (`higher_is_better` / `lower_is_better`);
- evaluation assumptions and evidence references.

The utility does not call alpha or portfolio internals. A strategy app supplies already-computed metrics from public owner APIs. This keeps the experiment layer thin and prevents a new cross-repository abstraction.

### 4. Recourse, MILP and DRO

This PR series establishes the seams but deliberately does not pretend to implement full recourse optimization, MILP/MIQP, DRO, C&CG or Benders.

Existing execution simulation already represents blocked orders, cash shortfall and market-rule effects. A future recourse policy can consume those results once a concrete strategy defines whether a blocked target should remain cash, substitute another asset, or trigger re-optimization.

MILP/MIQP should be introduced only when discrete constraints make the existing heuristic constructor measurably inadequate. DRO should follow empirical evidence that simple scenario and box-uncertainty robustness are insufficient. Benders belongs only after a scenario/recourse optimization problem is too large for a direct solver.

## Compatibility

- Existing claims and cases require no migration.
- Existing portfolio construction is unchanged unless callers invoke the new uncertainty helpers.
- Existing strategy apps are unchanged unless they emit a decision-focused receipt.
- No new third-party runtime dependency is required.

## Testing

Workspace:

- valid and invalid `counterexample.v1` fixtures;
- missing claim/reference failures;
- case-to-counterexample reference validation;
- CLI full scan includes counterexamples;
- schema existence tests.

Portfolio:

- zero uncertainty is identity;
- increasing uncertainty lowers conservative scores;
- negative/non-finite uncertainty is rejected;
- long/short worst-case return uses absolute exposure;
- shape mismatch rejected;
- public import smoke.

Strategy app:

- direction-aware deltas;
- missing baseline metric behavior is explicit;
- non-finite metrics rejected;
- receipt serialization is deterministic;
- public import smoke.

## Rollout

1. Merge the owner PRs first (`portfolio-backtester`, `strategy-app`).
2. Update workspace gitlinks only after owner PRs merge.
3. Merge the workspace governance PR after its own tests pass and, if owner PRs have merged, pin the new gitlinks in a follow-up commit.
4. Use the new counterexample schema on a real strategy only when an existing evidence artifact can be referenced without inventing data.
