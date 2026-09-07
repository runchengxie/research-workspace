# Cashflow Executable Portfolio Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a price-aware, 100-share-lot-rounded executable cash-flow portfolio for a RMB 500,000 reference account and redesign the Feishu research chart around executable holdings and diagnostics.

**Architecture:** Keep the existing Top 50 factor selection unchanged. Add a deterministic execution-simulation module in `strategy-app` that consumes the selection artifact and an immutable price snapshot, then add rendering/enrichment support in `market-intel` that presents the executable result without changing live eligibility or reconstructed-PIT gates.

**Tech Stack:** Python, pandas, dataclasses, pytest, Ruff, Matplotlib, existing Feishu CLI delivery.

**Spec:** `docs/superpowers/specs/2026-09-06-cashflow-executable-portfolio-design.md`

## Global Constraints

- Research/shadow only; no live trading or production eligibility change.
- Preserve `RESEARCH ONLY`, `RECONSTRUCTED PIT`, and `eligible_for_live=false` labeling.
- Use deterministic ordering and SHA-256 identities for input snapshots.
- Preserve unrelated dirty-worktree changes.
- Follow TDD: each production behavior starts with a failing test.

---

### Task 1: Add executable portfolio policy and deterministic lot-rounded construction

**Files:**
- Create: `strategy-app/src/strategy_app/cashflow/executable.py`
- Modify: `strategy-app/src/strategy_app/cashflow/__init__.py`
- Test: `strategy-app/tests/test_cashflow_executable.py`

**Interfaces:**
- Consumes a research selection `pandas.DataFrame`, a price `pandas.DataFrame`, and an execution policy.
- Produces an `ExecutablePortfolioResult` with `targets`, `skipped`, and `receipt`.
- Public functions:
  - `CashflowExecutionPolicy(...)`
  - `build_executable_cashflow_portfolio(selection, prices, policy, signal_date) -> ExecutablePortfolioResult`

- [ ] **Step 1: Write failing policy-validation tests.**

Add tests asserting that invalid capital, negative cash reserve, invalid lot size, invalid caps, and impossible minimum-position constraints raise `CashflowRunError`.

- [ ] **Step 2: Run the focused test file and verify the expected missing-module failure.**

Run:

```bash
uv run --project strategy-app pytest strategy-app/tests/test_cashflow_executable.py -q
```

Expected: collection or import failure because `strategy_app.cashflow.executable` does not exist.

- [ ] **Step 3: Implement the policy dataclass and validation.**

Implement defaults exactly from the spec: `portfolio_value=500_000`, `research_top_n=50`, `max_holdings=25`, `cash_reserve=0.03`, `max_weight=0.08`, `min_position_value=10_000`, `industry_cap=0.25`, `lot_size=100`. Validate numeric ranges and that the maximum holdings/cap combination can invest the non-cash capital.

- [ ] **Step 4: Run policy tests and verify they pass.**

Run the same focused pytest command and confirm all policy tests pass.

- [ ] **Step 5: Write failing tests for price validation and candidate diagnostics.**

Cover normalized symbols, duplicate price symbols, missing prices, non-positive prices, stale price dates, and an empty executable candidate set. Assert that affected symbols appear in deterministic skip diagnostics.

- [ ] **Step 6: Run the focused tests and verify the new tests fail for the expected missing behavior.**

Run the focused pytest command and confirm failures describe the absent builder behavior rather than test errors.

- [ ] **Step 7: Implement price validation and snapshot metadata.**

Normalize symbols, require `symbol`, `price`, and `price_date`, reject invalid duplicates, compute the price snapshot SHA-256 from canonical input rows, and record `price_date`, freshness status, and missing/invalid price reasons in the receipt.

- [ ] **Step 8: Write failing tests for deterministic target allocation and 100-share rounding.**

Use a small synthetic selection with known free-cash-flow values, prices, industries, and a RMB 500,000 account. Assert that at most 25 names are selected, actual shares are multiples of 100, actual amounts do not exceed investable capital, cash reserve is preserved, and target/actual weights and deviations are present.

- [ ] **Step 9: Implement candidate selection, constrained target weights, and lot rounding.**

Use research rank as the deterministic tie-breaker, retain at most 25 executable candidates, allocate within stock and industry caps, round down to whole lots, recalculate actual fields, and retain residual cash. Record `target_amount`, `actual_amount`, `shares`, `actual_weight`, `weight_deviation`, `industry`, and skip reasons.

- [ ] **Step 10: Run the full focused executable-portfolio suite.**

Run:

```bash
uv run --project strategy-app pytest strategy-app/tests/test_cashflow_executable.py -q
uv run --project strategy-app ruff check strategy-app/src/strategy_app/cashflow/executable.py strategy-app/tests/test_cashflow_executable.py
```

Expected: all tests pass and Ruff exits 0.

---

### Task 2: Integrate executable simulation into the cash-flow research run without changing gates

**Files:**
- Modify: `strategy-app/src/strategy_app/cashflow/contract.py`
- Modify: `strategy-app/src/strategy_app/cashflow/runner.py`
- Modify: `strategy-app/src/strategy_app/cashflow/cli.py`
- Test: `strategy-app/tests/test_cashflow_runner.py`
- Test: `strategy-app/tests/test_cashflow_executable.py`

**Interfaces:**
- Existing `build_cashflow_targets` behavior remains unchanged.
- Add an explicit execution-simulation entry point or runner option that requires a price snapshot and emits a separate executable artifact.
- Existing readiness gates still reject live/gray eligibility when reconstructed PIT or other gates fail.

- [ ] **Step 1: Write failing integration tests.**

Assert that a reconstructed-PIT selection can produce a research-only executable artifact when explicitly requested, that the original research selection remains unchanged, and that the receipt contains `eligible_for_live=false`, price identity, policy, and execution diagnostics.

- [ ] **Step 2: Run the integration tests and verify the expected failure.**

Run the focused runner tests and confirm the new executable path is not yet available.

- [ ] **Step 3: Implement the narrow integration surface.**

Add only the required runner/CLI plumbing; do not modify strict readiness decisions or publication gates. Store executable output under a distinct artifact name/path so it cannot overwrite the research selection.

- [ ] **Step 4: Run the existing cash-flow runner/calendar/rollout suites.**

Run:

```bash
uv run --project strategy-app pytest \
  strategy-app/tests/test_cashflow_runner.py \
  strategy-app/tests/test_cashflow_calendar.py \
  strategy-app/tests/test_cashflow_rollout.py -q
```

Expected: all existing tests and the new integration tests pass.

---

### Task 3: Redesign the Markdown and PNG renderer for executable portfolio reporting

**Files:**
- Modify: `market-intel/src/a_share_daily/cashflow_portfolio_render.py`
- Modify: `market-intel/src/a_share_daily/cli.py`
- Test: `market-intel/tests/test_cashflow_portfolio_render.py`

**Interfaces:**
- Existing renderer continues to accept research selection artifacts.
- Add executable-artifact rendering based on the fields from Task 1.
- Preserve company-name and industry enrichment from the existing instrument snapshot path.

- [ ] **Step 1: Write failing renderer tests.**

Assert that Markdown includes research versus executable counts, cash reserve, actual shares, actual amounts, deviations, skipped symbols, and industry allocation. Assert that PNG rendering uses a bounded Top 10 holdings panel instead of 50 dense stock bars and includes the execution status/KPI labels.

- [ ] **Step 2: Run the renderer tests and verify the expected failure.**

Run:

```bash
uv run --project market-intel pytest market-intel/tests/test_cashflow_portfolio_render.py -q
```

- [ ] **Step 3: Implement the Markdown layout.**

Render a compact summary, executable holdings table, top industry table, and skipped-symbol diagnostics while retaining the full research list in JSON/Markdown where available.

- [ ] **Step 4: Implement the PNG layout.**

Use the existing chart theme and Watch20/D11-H5 language. Add a KPI strip, Top 10 actual-weight bars, Top 8 industries plus `Other`, a compact execution table, and a research-only footer. Keep all labels readable at Feishu image size.

- [ ] **Step 5: Run renderer tests and Ruff.**

Run:

```bash
uv run --project market-intel pytest market-intel/tests/test_cashflow_portfolio_render.py -q
uv run --project market-intel ruff check market-intel/src/a_share_daily/cashflow_portfolio_render.py market-intel/tests/test_cashflow_portfolio_render.py
```

Expected: all tests pass and Ruff exits 0.

---

### Task 4: Connect executable artifacts to explicit Feishu test delivery

**Files:**
- Modify: `market-intel/src/a_share_daily/cashflow_delivery.py`
- Modify: `market-intel/src/a_share_daily/cli.py`
- Test: `market-intel/tests/test_cashflow_delivery.py`

**Interfaces:**
- Existing explicit chat ID, application-auth, idempotent delivery behavior remains in force.
- Delivery accepts the executable Markdown and PNG paths and sends them only to explicitly supplied test chats.

- [ ] **Step 1: Write failing delivery tests.**

Assert that the delivery payload identifies the executable portfolio, includes research-only status, and refuses missing/ambiguous chat IDs or a missing chart artifact.

- [ ] **Step 2: Run the delivery tests and verify the expected failure.**

Run the focused delivery tests and confirm the new executable metadata/path checks fail before implementation.

- [ ] **Step 3: Implement delivery plumbing.**

Add executable artifact paths and metadata to the existing delivery contract without changing default dry-run behavior or explicit chat authorization requirements.

- [ ] **Step 4: Run delivery tests and Ruff.**

Run the focused delivery suite and CLI lint checks; confirm all pass.

---

### Task 5: Generate and inspect the current reconstructed-PIT executable snapshot

**Files:**
- Modify: `docs/operations/cashflow-feishu-rollout.md`
- Create: `/tmp/cashflow-reconstructed-snapshot-20260906/executable-portfolio.json`
- Create: `/tmp/cashflow-reconstructed-snapshot-20260906/cashflow-executable.png`

- [ ] **Step 1: Locate or build the signal-date price snapshot.**

Use the existing Tushare-compatible local data source and create an immutable snapshot with `symbol`, `price`, and `price_date`. Do not use future prices or overwrite the research input panel.

- [ ] **Step 2: Run the executable simulation against the existing research selection.**

Use the explicit reconstructed-PIT flag and the new execution policy. Confirm the receipt retains `research_only=true`, `eligible_for_live=false`, and the price snapshot hash.

- [ ] **Step 3: Render the new Markdown and PNG artifacts.**

Inspect the PNG with the image viewer and check that the KPI strip, Top 10 holdings, industry breakdown, execution table, and warning footer are legible.

- [ ] **Step 4: Update the operations note.**

Document the new command, artifact fields, default policy, and the fact that the executable result is still research-only.

---

### Task 6: End-to-end verification and authorized Feishu send

**Files:**
- No source changes expected.

- [ ] **Step 1: Run focused and relevant regression tests.**

Run the strategy-app cash-flow suites, market-intel cash-flow suites, and Ruff checks from Tasks 1–4. Record exact pass counts and failures.

- [ ] **Step 2: Verify artifact contracts.**

Check that the research selection, executable portfolio, receipt, Markdown, and PNG all agree on signal date, price date, holdings count, capital, cash, and eligibility labels.

- [ ] **Step 3: Send the new PNG and Markdown to the explicitly authorized personal Feishu chat using application authentication.**

Use the existing explicit chat ID and idempotent delivery path. Do not send to any group or production destination.

- [ ] **Step 4: Inspect the returned Feishu message IDs and report the artifact path, test results, and research-only caveat.**
