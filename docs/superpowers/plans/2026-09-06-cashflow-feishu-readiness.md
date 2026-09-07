# Cashflow Feishu Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现金流主因子策略推进到具备飞书测试群幂等推送资格的灰度候选状态，并在研究门禁未通过时保持 research/shadow。

**Architecture:** `strategy-research` 保留策略身份、研究证据和准入决策；`strategy-app` 承担冻结后的现金流计算、组合合同和解释产物；`strategy-pipeline` 承担运行编排、目标导出和回执；独立的 Feishu adapter 只消费已通过校验的不可变发布产物。所有生产路径 fail-closed，研究脚本不得直接触发推送。

**Tech Stack:** Python、pandas、现有 research contracts、JSON/Parquet artifact、交易日历、`strategy-app` CLI、`strategy-pipeline` target contract、Feishu bot webhook/card API。

**Spec:** `strategy-research/research/experiments/cashflow_indices/current_status_980092.md`、`strategy-research/research/experiments/cashflow_indices/decisions/980092_final_decision_20260905.md`、`strategy-app/docs/daily-watch20-publication-orchestration.md`。

## Global Constraints

- 现金流策略在严格 PIT、统一样本外、成本和容量门禁通过前，必须保持 `research`/`shadow`，不得发布为正式生产策略。
- 生产产物必须包含 strategy/policy/data/code identity、source/signal/effective dates、输入哈希和不可变 run receipt。
- 缺少核心数据、交易日历或准入证据时必须拒绝发布，不得用默认值补齐。
- Feishu 推送只消费已通过发布合同的 artifact，并使用 `strategy_id + policy_id + signal_date` 做幂等键。
- 凭证、真实 provider 配置、私有数据和生产 webhook 不进入 Git。

---

### Task 1: Freeze the research and production-candidate contract

**Files:**
- Create: `docs/evidence/cashflow-production-readiness-baseline-2026-09-06.md`
- Modify: `strategy-research/catalog.json`
- Modify: `strategy-research/research/experiments/cashflow_indices/current_status_980092.md`
- Test: `tests/test_strategy_catalog_document.py`

**Interfaces:**
- Consumes: current cashflow decision records and existing strategy catalog schema.
- Produces: a named cashflow candidate identity, lifecycle state, explicit failed/unverified gates, and a machine-readable decision that downstream runtime code can enforce.

- [x] **Step 1: Record the baseline evidence and candidate identity**

  Freeze the initial candidate as a research-only identity (not production eligible): `cashflow_quality_top50_v1`, with quality filter, value-trap filter, FCF weighting, 10% single-name cap, and quarterly rebalance. Record that strict PIT and common OOS gates are unverified.

- [x] **Step 2: Add the catalog entry and regression test**

  Add the candidate to `strategy-research/catalog.json` with `lifecycle: "research_shadow"`, `production_eligible: false`, the cashflow status document as `human_spec`, and a future runtime entry placeholder that points only to the eventual `strategy cashflow` owner.

- [x] **Step 3: Verify the catalog and documentation contracts**

  Run:

  ```bash
  pytest -q tests/test_strategy_catalog_document.py tests/test_strategy_evidence_gate.py
  ```

  Expected: existing catalog/evidence checks pass and the new candidate remains explicitly ineligible.

### Task 2: Build strict production-candidate evidence gates

**Files:**
- Create: `src/research_contracts/cashflow_readiness.py`
- Create: `tests/test_cashflow_readiness.py`
- Modify: `src/research_contracts/__init__.py`
- Modify: `docs/research-decision-governance.md`

**Interfaces:**
- Consumes: a mapping containing PIT coverage, aligned OOS metrics, cost grid, capacity evidence, and exposure diagnostics.
- Produces: `CashflowReadinessDecision` with `decision`, `production_eligible`, `failed_gates`, and `evidence_refs`.

- [x] **Step 1: Write failing tests for missing and passing gates**
- [x] **Step 2: Implement a pure fail-closed evaluator**
- [x] **Step 3: Add explicit thresholds and schema validation**
- [x] **Step 4: Run the focused contract tests**

  ```bash
  pytest -q tests/test_cashflow_readiness.py
  ```

  The initial real evidence fixture must evaluate to `continue_shadow`, not pass production.

### Task 3: Create the strategy-app cashflow production runner

**Files:**
- Create: `strategy-app/src/strategy_app/cashflow/contract.py`
- Create: `strategy-app/src/strategy_app/cashflow/runner.py`
- Create: `strategy-app/src/strategy_app/cashflow/__init__.py`
- Create: `strategy-app/tests/test_cashflow_runner.py`
- Modify: `strategy-app/pyproject.toml`

**Interfaces:**
- Consumes: validated daily PIT feature frame, trading calendar, frozen policy config, and prior holdings.
- Produces: `CashflowRunResult` containing holdings, target weights, trade changes, explanations, and a fail-closed receipt.

- [x] **Step 1: Define the input/output schema and failure cases in tests**
- [x] **Step 2: Implement policy validation and date semantics**
- [x] **Step 3: Implement deterministic selection and capped weighting**
- [x] **Step 4: Implement immutable run artifact writing**
- [x] **Step 5: Add a CLI entry point and run focused tests**

  ```bash
  cd strategy-app
  pytest -q tests/test_cashflow_runner.py
  ```

- [x] **Step 6: Add the research-to-runtime feature boundary**

  Add `cashflow_pit_features.v2` validation so the runner cannot consume a raw
  or reconstructed research panel as if it were a strategy feature frame.
  Require `available_date`, all strategy-derived fields, and an immutable,
  revision-safe PIT manifest attestation; do not infer missing formulas.

- [x] **Step 7: Freeze quality/no-trap feature formulas**

  Implement `cashflow_quality_feature_builder.v1` with an explicit policy
  receipt. Keep raw CFO/profit eligibility separate from the cross-sectional
  quality percentile used by the no-trap variant; reject missing announcement
  timing instead of treating the research panel formation date as disclosure.

- [x] **Step 8: Add an operational feature-builder CLI**

  Write the v2 parquet and receipt on success; write a blocked receipt and
  return exit code 20 for missing disclosure timing, missing fields, or unsafe
  PIT input.

- [x] **Step 9: Preserve announcement provenance in the research panel**

  Carry the latest disclosure date across the income, cashflow, balance-sheet,
  and indicator inputs used by each panel row as `available_date`. Do not use
  the formation date as a disclosure-date substitute.

### Task 4: Integrate publication and target export

**Files:**
- Create: `strategy-app/docs/cashflow-publication.md`
- Modify: `strategy-pipeline/src/strategy_pipeline/cli.py`
- Create: `strategy-pipeline/src/strategy_pipeline/cashflow_publication.py`
- Create: `strategy-pipeline/tests/test_cashflow_publication.py`
- Modify: `docs/platform-workflow.md`

**Interfaces:**
- Consumes: a passed cashflow run directory and readiness decision.
- Produces: an immutable publication directory, `targets.json`, lineage, and publication receipt; rejects research-only or failed artifacts.

- [x] **Step 1: Write tests for rejection, duplicate identity, and atomic publication**
- [x] **Step 2: Implement publication contract and latest pointer**
- [x] **Step 3: Reuse the existing selection/target payload contract**
- [x] **Step 4: Run cross-repository publication tests**

Implementation note: the publication boundary currently lives in
`strategy-pipeline/src/strategy_pipeline/cashflow_publication.py` and is
exposed as `strategy-pipeline cashflow-publish-shadow`. It intentionally
publishes only the Feishu shadow tier; it does not authorize live delivery.

### Task 5: Add Feishu test-group delivery with idempotency

**Files:**
- Create: `market-intel/src/market_intel/delivery/feishu_cashflow.py`
- Create: `market-intel/tests/test_feishu_cashflow.py`
- Create: `market-intel/docs/operations/feishu-cashflow-shadow.md`
- Modify: `market-intel` deployment configuration outside Git for secrets only

**Interfaces:**
- Consumes: passed publication receipt and compact cashflow signal artifact.
- Produces: one Feishu message/card per idempotency key, delivery receipt, retry outcome, and alertable failure status.

- [x] **Step 1: Write tests with a fake subprocess transport**
- [x] **Step 2: Implement payload rendering and explicit target lookup**
- [x] **Step 3: Implement duplicate suppression and atomic delivery receipts**
- [x] **Step 4: Run delivery tests without real credentials**

Implementation note: the current adapter is
`market-intel/src/a_share_daily/cashflow_delivery.py`; it requires explicit
chat IDs and supports dry-run only until a test-group credential is supplied.

### Task 6: Operate a shadow-to-gray rollout

**Files:**
- Create: `docs/operations/cashflow-feishu-rollout.md`
- Create: `scripts/run_cashflow_shadow.py`
- Create: `tests/test_cashflow_shadow_schedule.py`
- Modify: `docs/strategy-catalog.md`

**Interfaces:**
- Consumes: trading calendar, data freshness checks, runner, publication receipt, and Feishu test-group adapter.
- Produces: scheduled shadow runs, operational health checks, manual approval records, and a documented promotion decision.

- [x] **Step 1: Add trading-calendar scheduling, PIT audit and fail-closed input checks**
- [x] **Step 2: Add daily run audit and alert conditions**
- [ ] **Step 3: Run 20–30 trading days of dual-run observation**
- [ ] **Step 4: Re-evaluate all gates before any production-group promotion**
