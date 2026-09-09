# Daily Feishu 10-Stock Rollout Backtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate the gray-tested daily Feishu 10-stock rollout using immutable selection and delivery artifacts, first as a realized forward replay and then, where PIT history permits, as an out-of-sample historical replay.

**Architecture:** Keep the existing research-only selection and delivery contracts unchanged. Add a read-only analysis layer that loads historical selection/delivery receipts, joins them to authoritative daily OHLC/adjusted-return data, applies explicit T+1 execution and cost rules, and emits machine-readable evidence plus a concise report. Historical signal reconstruction is a separate optional stage and must not be presented as equivalent to the actual gray rollout.

**Tech Stack:** Python, pandas, existing `strategy_app.cashflow` / DailyWatch20 contracts, parquet/JSON artifacts, pytest, Markdown/JSON/CSV research outputs.

**Spec:** User request in the conversation: backtest the currently gray-tested daily Feishu 10-stock rollout while preserving research-only status.

## Global Constraints

- Do not modify production delivery, live eligibility, Feishu recipients, or execution behavior.
- Use the exact selection artifact and delivery receipt as the source of truth for the gray-period replay.
- Signal timing is T-session close to the next open; same-session returns are excluded from the primary result.
- Separate actual gray-period replay from reconstructed historical signal replay in all artifacts and conclusions.
- Include benchmark, transaction cost, turnover, missing-price, suspension, limit-up/down, and coverage diagnostics.
- Preserve unrelated changes and use separate provider/consumer worktrees for code changes in child repositories.

---

### Task 1: Inventory and freeze the gray-period input contract

**Files:**
- Create: `docs/evidence/daily-feishu10-backtest-input-inventory.md`
- Inspect: `market-intel/src/a_share_daily/cashflow_delivery.py`
- Inspect: `quant-research/src/strategy_app/cashflow/contract.py`
- Inspect: `quant-research/src/strategy_app/cashflow/executable.py`
- Inspect: `quant-research/src/strategy_app/daily_watch20/daily_watch20_market_shadow_publish.py`

**Interfaces:**
- Consumes: JSON selection artifacts, publication receipts, delivery receipts, and their referenced price/source files.
- Produces: an inventory recording artifact paths, schemas, date coverage, policy identity, hashes, and missing inputs; no performance conclusion is allowed before this inventory passes.

- [ ] **Step 1: Enumerate available artifact roots outside Git**

  Run:

  ```bash
  find /home/richard/code/production /home/richard/code/research-workspace/market-intel/state /home/richard/code/research-workspace/market-intel/out -type f 2>/dev/null | rg -i '(cashflow|selection|delivery|publication|receipt|feishu|watch20)'
  ```

  Record whether the gray-period artifacts are present, their earliest/latest signal dates, and whether each selection has an immutable source receipt.

- [ ] **Step 2: Validate the artifact schema and identity fields**

  Confirm `schema_version`, `strategy_id`, `policy_id`, `source_date`, `signal_date`, `content_sha256`, `research_only`, and `eligible_for_live` for each candidate artifact. Reject artifacts that do not pass the existing loader contracts.

- [ ] **Step 3: Write the inventory document**

  Include the exact artifact root, row grain, date coverage, number of signal days, number of valid 10-stock lists, delivery success coverage, and explicit missing-data blockers. Mark the result `ready_for_gray_replay` only when every selected day has a validated list and a usable signal/effective-date pair.

- [ ] **Step 4: Verify the inventory document**

  Run:

  ```bash
  git diff --check
  rg -n 'ready_for_gray_replay|signal_date|eligible_for_live|missing' docs/evidence/daily-feishu10-backtest-input-inventory.md
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add docs/evidence/daily-feishu10-backtest-input-inventory.md
  git commit -m "docs: inventory daily Feishu 10 backtest inputs"
  ```

### Task 2: Build the actual gray-period forward-replay analyzer

**Files:**
- Create in `quant-research`: `research/experiments/daily_feishu10/daily_feishu10_gray_replay.py`
- Create in `quant-research`: `tests/test_daily_feishu10_gray_replay.py`
- Modify only if needed: `quant-research/src/strategy_app/cashflow/historical_construction.py`

**Interfaces:**
- Consumes: validated daily selection rows with `signal_date`, `effective_date`, `symbol`, `target_weight`; daily OHLC/return data; benchmark daily returns; cost parameters.
- Produces: `analyze_gray_replay(...) -> tuple[pd.DataFrame, dict[str, object]]` with per-stock observations, per-signal-day portfolio observations, aggregate metrics, and coverage diagnostics.

- [ ] **Step 1: Write failing tests for timing and weighting**

  Cover: T-day signal excludes T-day return, T+1 open is the first eligible execution, duplicate symbols are rejected, missing prices are reported rather than silently filled, and weighted portfolio return equals the weighted sum of valid constituent returns.

- [ ] **Step 2: Run the focused tests and verify failure**

  ```bash
  uv run pytest tests/test_daily_feishu10_gray_replay.py -q
  ```

  Expected: collection or assertion failure because the analyzer does not yet exist.

- [ ] **Step 3: Implement the smallest pure analyzer**

  Use explicit dataclass/config fields for `entry_price_field`, `exit_price_field`, `horizons=(1,3,5,10)`, `cost_bps`, and `benchmark_column`. Preserve `NaN`/unavailable observations in diagnostics and compute the primary return only from executable constituents.

- [ ] **Step 4: Add benchmark and cost calculations**

  Report equal-weight and artifact-weighted results, gross/net returns, excess returns, hit rate, median constituent return, turnover proxy, cost drag, coverage, and blocked/suspended/limit diagnostics.

- [ ] **Step 5: Run tests and quality checks**

  ```bash
  uv run pytest tests/test_daily_feishu10_gray_replay.py -q
  uv run ruff check research/experiments/daily_feishu10 tests/test_daily_feishu10_gray_replay.py
  ```

- [ ] **Step 6: Commit the provider change**

  Commit and push the `quant-research` provider worktree before adding any consumer report integration.

### Task 3: Run the gray replay and validate the result

**Files:**
- Create outside Git or under ignored research output: `daily_feishu10_gray_replay.json`
- Create outside Git or under ignored research output: `daily_feishu10_gray_replay.csv`
- Create: `docs/evidence/daily-feishu10-gray-replay-report.md`

**Interfaces:**
- Consumes: Task 1 inventory, Task 2 analyzer, authoritative daily prices, and benchmark returns.
- Produces: a first decision-ready gray-period report with an explicit confidence level and data gaps.

- [ ] **Step 1: Pin the run inputs and code identity**

  Record source artifact hashes, price/benchmark manifests, signal date range, execution timing, cost assumptions, and analyzer commit SHA.

- [ ] **Step 2: Run the analyzer**

  Produce per-stock, per-day, and aggregate outputs without writing into production directories.

- [ ] **Step 3: Reconcile counts and identities**

  Verify that every included signal day maps to exactly one selection artifact, all symbols are unique per day, weights sum to one or are explicitly normalized, and every excluded observation has a reason.

- [ ] **Step 4: Write the report**

  Separate observed gray results from interpretation. Include sample size, cumulative and annualized figures only when the sample supports them, benchmark comparison, cost sensitivity, worst days, coverage, and the recommendation to continue/stop/extend observation.

- [ ] **Step 5: Validate before claiming completion**

  Run the focused tests, report schema checks, and a clean diff check. Do not call the result a long-term strategy backtest if the sample is only the gray window.

### Task 4: Assess and, if possible, run the historical PIT replay

**Files:**
- Create in `quant-research`: `research/experiments/daily_feishu10/daily_feishu10_historical_replay.py`
- Create in `quant-research`: `tests/test_daily_feishu10_historical_replay.py`
- Create: `docs/evidence/daily-feishu10-historical-replay-report.md`

**Interfaces:**
- Consumes: PIT feature snapshots and historical prices with a documented availability date, plus the frozen daily-10 policy.
- Produces: walk-forward/out-of-sample daily-10 selections and replay metrics, or a fail-closed evidence note explaining why historical reconstruction is not valid.

- [ ] **Step 1: Check PIT completeness before reconstruction**

  Require signal-available timestamps, candidate-universe membership, no future revisions, and sufficient daily OHLC/limit/suspension data. If any requirement fails, produce a blocked evidence note rather than substituting partial data.

- [ ] **Step 2: Write failing tests for no-lookahead behavior**

  Verify that a feature published after T is unavailable at T, the generated selection is frozen before return calculation, and walk-forward splits do not reuse future observations.

- [ ] **Step 3: Implement historical reconstruction only behind explicit inputs**

  Reuse the frozen production policy or a versioned research policy; do not copy a second ranking algorithm into the report layer. Label reconstructed signals separately from observed Feishu signals.

- [ ] **Step 4: Run subperiod and sensitivity checks**

  Compare next-day/3-day/5-day/10-day horizons, cost assumptions, benchmark choices, equal-weight versus artifact-weighted portfolios, and rolling subperiod stability. Include industry, size, value, liquidity, and concentration exposures where available.

- [ ] **Step 5: Publish the historical conclusion**

  State whether historical evidence supports the gray result, contradicts it, or is insufficient. Keep `research_only=true` and `eligible_for_live=false` in all generated artifacts.

### Task 5: Cross-repository consumer/report handoff

**Files:**
- Modify in `market-intel` only after the `quant-research` provider is merged: `src/a_share_daily/...` report/consumer adapter selected from the existing owner boundary.
- Create in `market-intel`: focused contract tests for consuming the versioned evidence artifact.
- Modify only if needed: workspace evidence navigation.

**Interfaces:**
- Consumes: versioned research evidence artifact and receipt from `quant-research`.
- Produces: optional Feishu-readable research summary, never a live target or a new selection algorithm.

- [ ] **Step 1: Define the versioned evidence contract**

  Pin schema, producer commit, input hashes, report date range, and `research_only` / `eligible_for_live` flags.

- [ ] **Step 2: Add fail-closed consumer validation**

  Reject stale, mismatched, incomplete, or live-eligible artifacts; preserve the existing explicit test-chat boundary.

- [ ] **Step 3: Add the Feishu research summary only if requested by the operator**

  Include the result period, sample size, net/excess metrics, coverage warnings, and a clear statement that the output is research evidence rather than an investment instruction.

- [ ] **Step 4: Run consumer tests and document the handoff**

  Run the relevant `market-intel` checks and record the exact producer/provider revision consumed.

## Completion Criteria

- The gray-period replay has an inventory, pinned inputs, reproducible outputs, and a report.
- The primary timing is T close to T+1 open; no same-session lookahead is present.
- Net returns, benchmark excess, costs, turnover, coverage, and execution blockers are reported.
- Historical reconstruction is either completed with PIT/OOS evidence or explicitly blocked with the reason.
- No production delivery behavior or live eligibility changes.
