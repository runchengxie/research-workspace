# Cashflow Feishu Shadow Rollout

## Current operating mode

`cashflow_quality_top50_v1` remains `research_shadow`. The orchestration entry
point is fail-closed: a failed readiness decision, PIT audit, trading-calendar
check, scheduler, publication check, or delivery check stops the run before the
next stage.

The default mode is a Feishu dry-run. A real send requires explicit chat IDs
and the separate `--send` flag; no production-group target is configured by
default.

## Operational status notifications

The target-list delivery path remains fail-closed: it cannot send a selection
unless readiness, PIT, scheduler, and publication checks pass. To observe the
strategy before those economic/research gates are ready, configure a separate
status chat with `--status-chat-id` (or `CASHFLOW_STATUS_CHAT_IDS` in the
deployment bridge). A blocked run then sends, by default as a dry-run, a
status-only message containing the stage and reason. The status payload is
explicitly forbidden from containing symbols, weights, or target selections and
has its own receipt (`--status-receipt`).

For an explicit test-group send, use the same confirmation gate:

```bash
... scripts/run_cashflow_shadow.py \
  ... \
  --status-chat-id oc_test_status_group \
  --status-receipt /path/to/cashflow-status-receipt.json \
  --send --send-confirmation I_UNDERSTAND_TEST_GROUP_ONLY
```

The standalone adapter is also available for replaying a status input:

```bash
uv run --project /home/richard/code/market-intel \
  a-share-daily cashflow-status-notify \
  --status-json /path/to/status.json \
  --receipt /path/to/status-receipt.json \
  --chat-id oc_test_status_group
```

The `--features` input must be a separately materialized and attested
`cashflow_pit_features.v2` artifact. Raw or normalized fundamentals and the
existing 980092 research panel are not valid substitutes: the feature contract
requires the frozen derived fields
`selection_score`, `free_cash_flow`, `eligible`, `quality_pass`, and
`value_trap_pass`, plus an `available_date` no later than the source date. The
feature receipt must prove the same source date and PIT input identity.

The contract does not infer or impute these fields. A research panel with
reconstructed history, missing disclosure timing, or a neutral missing-feature
policy remains blocked until an upstream builder emits an attested feature
artifact.

The frozen `cashflow_quality_feature_builder.v1` policy separates the raw
`cfo_to_operating_profit_ratio` eligibility floor (`>= 0.30`) from the
cross-sectional `cfo_quality_percentile` used in the quality score and the
value-trap floor (`>= 0.60`). It also requires non-negative
`revenue_growth_persistence`; these are recorded in the feature receipt.

The builder entry point is:

```bash
PYTHONPATH=src uv run --project . \
  python -m style_factors.cashflow_quality_feature_builder \
  --input-panel /path/to/pit-visible-panel.parquet \
  --pit-audit /path/to/cashflow_pit_input_audit.json \
  --source-date YYYYMMDD \
  --output /path/to/cashflow-features.parquet
```

It returns `20` and writes `features.blocked.receipt.json` when disclosure
timing, feature inputs, or PIT attestation is unsafe.

## Reconstructed-PIT research snapshot

When the goal is to inspect the actual portfolio shape before historical
revision safety is complete, the builder and scheduler support an explicit
research-only override:

```bash
... cashflow_quality_feature_builder \
  ... \
  --allow-reconstructed-pit

... strategy_app.cashflow.scheduler \
  ... \
  --allow-reconstructed-pit
```

This mode uses the immutable snapshot plus Tushare-style availability dates,
but records `pit_quality=reconstructed` and keeps
`eligible_for_live=false`. The normal readiness and production paths remain
strict. The resulting selection can be rendered with:

```bash
uv run --project /home/richard/code/market-intel \
  a-share-daily cashflow-portfolio-render \
  --selection /path/to/selection.json \
  --chart-out /path/to/cashflow-portfolio.png
```

The PNG and Markdown are a research snapshot, not a deployable signal.

## Executable RMB 500,000 research view

The research selection can be converted into a separate executable simulation
without modifying the Top 50 selection artifact. The default execution policy
uses a RMB 500,000 reference account, at most 25 holdings, a 3% cash reserve,
an 8% single-stock cap, a RMB 10,000 minimum position, a 25% industry cap, and
100-share purchase lots.

The price snapshot must contain `symbol`, `price`, and `price_date`; its latest
date must not be later than the signal date. The executable receipt records the
price snapshot hash, actual shares, actual amounts, cash, weight deviations,
and skipped-symbol reasons. It remains `research_only=true` and
`eligible_for_live=false`.

The strategy-app CLI can publish both artifacts in one run:

```bash
PYTHONPATH=src uv run --project strategy-app \
  python -m strategy_app.cashflow \
  --input /path/to/cashflow-features.parquet \
  --readiness /path/to/readiness.json \
  --output-root /path/to/cashflow-runs \
  --trade-calendar /path/to/trade-calendar.parquet \
  --source-date YYYYMMDD \
  --signal-date YYYYMMDD \
  --execution-prices /path/to/price-snapshot.parquet \
  --execution-output-root /path/to/cashflow-runs
```

Render the executable artifact for Feishu with:

```bash
uv run --project /home/richard/code/market-intel \
  a-share-daily cashflow-portfolio-render \
  --selection /path/to/executable/selection.json \
  --instruments /path/to/instruments.parquet \
  --chart-out /path/to/cashflow-executable.png
```

The chart shows the Top 10 executable holdings, Top 8 industries plus Other,
cash/investment KPIs, and the 100-share execution table. The full research
Top 50 and skip diagnostics remain in the JSON/Markdown artifact.

## One-run command

From the repository root, provide the dated evidence and runtime inputs:

```bash
PYTHONPATH=src uv run --project . --group dev \
  python scripts/run_cashflow_shadow.py \
  --evidence-bundle strategy-research/research/evidence/cashflow_quality_top50_v1.json \
  --readiness /path/to/readiness.json \
  --trade-calendar /path/to/trade_calendar.parquet \
  --features /path/to/features.parquet \
  --features-receipt /path/to/features.receipt.json \
  --pit-audit strategy-research/research/evidence/cashflow_pit_input_audit_YYYYMMDD.json \
  --output-root /path/to/cashflow-runs \
  --publication-root /path/to/cashflow-publications \
  --rollout-ledger /path/to/cashflow-shadow-rollout.json \
  --delivery-receipt /path/to/cashflow-delivery.json \
  --chat-id oc_test_group \
  --as-of-date YYYYMMDD
```

The command returns exit code `20` for any blocked stage. A successful default
run returns `dry_run`; `--send` changes the terminal state to `sent` only after
the explicit delivery adapter succeeds and
`--send-confirmation I_UNDERSTAND_TEST_GROUP_ONLY` is supplied. The Python
orchestrator enforces this confirmation independently of the deployment shell.

For recurring shadow observation, the deployment bridge is
`market-intel/scripts/run_cashflow_shadow.sh`, with the optional
`cashflow-feishu-shadow.timer` scheduled for 06:15 Asia/Shanghai weekdays.
Install it only after supplying explicit feature/calendar/output paths and a
test chat ID in the external `cashflow-shadow.env`; the deployment setup keeps
this timer disabled unless `CASHFLOW_SHADOW_ENABLE=1` is explicitly provided.
The default remains dry-run.

## Promotion checklist

Before considering a real test-group send, retain immutable receipts for the
run, publication, and delivery stages, and inspect the rollout ledger. The
ledger must contain at least 20 passed trading sessions, have no unresolved
blocked-session alert, and still pass the current PIT, common out-of-sample,
cost, capacity, and evidence-integrity gates. Production-group promotion is a
separate manual decision and is not authorized by this script.
