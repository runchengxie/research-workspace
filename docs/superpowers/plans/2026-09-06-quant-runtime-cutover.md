# Quant Runtime Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the DailyWatch20 and cashflow shadow runtime from the old `research-workspace` checkout to the migrated `quant-research` and `quant-platform` repositories with deterministic verification and rollback, without granting cashflow live eligibility.

**Architecture:** `quant-research` owns strategy code and the shadow scheduler. `quant-platform` owns reusable contracts and cashflow publication. `market-intel` consumes path-free published artifacts and performs explicitly opt-in delivery. The existing `research-workspace` release remains the rollback source until the cutover gates pass.

**Tech Stack:** Python 3.12+, uv, pytest, Ruff, typed JSON artifacts, shell/systemd runners, Git worktrees.

**Spec:** `docs/superpowers/specs/2026-09-06-quant-runtime-cutover-design.md`

## Global Constraints

- Cashflow artifacts must remain `research_only=true` and `eligible_for_live=false`.
- No production pointer changes occur before all cutover gates pass.
- `market-intel` must not import `quant-research` Python modules.
- New runtime code must not read strategy source files from `research-workspace`.
- FMP and other external-network tests must be opt-in and never part of the offline full suite.
- Existing production releases and rollback manifests must remain intact.

### Task 0: Import the existing cashflow delivery slice into the migration branch

**Files:**
- Source: `/home/richard/code/market-intel/src/a_share_daily/cashflow_delivery.py`
- Source: `/home/richard/code/market-intel/src/a_share_daily/cashflow_portfolio_render.py`
- Source: `/home/richard/code/market-intel/src/a_share_daily/cashflow_status_notify.py`
- Source: `/home/richard/code/market-intel/scripts/run_cashflow_shadow.sh`
- Source: `/home/richard/code/market-intel/scripts/systemd/cashflow-feishu-shadow.service`
- Source: `/home/richard/code/market-intel/scripts/systemd/cashflow-feishu-shadow.timer`
- Source: `/home/richard/code/market-intel/docs/cashflow-feishu-shadow.md`
- Source: `/home/richard/code/market-intel/tests/test_cashflow_delivery.py`
- Source: `/home/richard/code/market-intel/tests/test_cashflow_portfolio_render.py`
- Source: `/home/richard/code/market-intel/tests/test_cashflow_shadow_script.py`
- Source: `/home/richard/code/market-intel/tests/test_cashflow_status_notify.py`
- Modify: `src/a_share_daily/cli.py` in market-intel
- Modify: `scripts/setup_cron.sh` in market-intel
- Modify: `tests/test_a_share_daily_cli.py` in market-intel

**Interfaces:**
- Consumes: the user's existing uncommitted cashflow slice from the market-intel main checkout.
- Produces: the same cashflow delivery behavior on the isolated `origin/main` branch, with no source files removed from the user's main checkout.

- [ ] **Step 1: Reapply the tracked CLI and scheduler diffs with `apply_patch` and add the listed new files**

Use the existing main-checkout diff as the source of truth. Preserve all cashflow validation, explicit test-chat confirmation, dry-run defaults, and systemd unit contents exactly while applying the files to the isolated worktree.

- [ ] **Step 2: Run the imported cashflow tests**

Run: `uv run pytest tests/test_cashflow_delivery.py tests/test_cashflow_portfolio_render.py tests/test_cashflow_shadow_script.py tests/test_cashflow_status_notify.py tests/test_a_share_daily_cli.py -q`

Expected: PASS without network access.

- [ ] **Step 3: Commit the imported slice**

```bash
git add src/a_share_daily/cli.py src/a_share_daily/cashflow_delivery.py src/a_share_daily/cashflow_portfolio_render.py src/a_share_daily/cashflow_status_notify.py scripts/run_cashflow_shadow.sh scripts/setup_cron.sh scripts/systemd/cashflow-feishu-shadow.service scripts/systemd/cashflow-feishu-shadow.timer docs/cashflow-feishu-shadow.md tests/test_a_share_daily_cli.py tests/test_cashflow_delivery.py tests/test_cashflow_portfolio_render.py tests/test_cashflow_shadow_script.py tests/test_cashflow_status_notify.py
git commit -m "feat: preserve cashflow shadow delivery slice"
```

### Task 1: Establish isolated repository worktrees and migration manifest

**Files:**
- Create: `/home/richard/code/.worktrees/quant-research-cutover` from `.private-staging/quant-research` `origin/main`
- Create: `/home/richard/code/.worktrees/quant-platform-cutover` from `.public-staging/quant-platform` `origin/main`
- Create: `/home/richard/code/.worktrees/market-intel-cutover` from `market-intel` `origin/main`
- Create: `migration/runtime-cutover-manifest.json` in quant-research
- Test: `tests/test_runtime_cutover_manifest.py` in quant-research

**Interfaces:**
- Consumes: current repository commits, package versions, and the existing cashflow schema constants.
- Produces: a manifest containing `schema_version`, `producer_repository`, `producer_commit`, `platform_repository`, `platform_commit`, `consumer_repository`, `cashflow_schemas`, and `live_eligibility=false`.

- [ ] **Step 1: Write the failing manifest test**

```python
def test_runtime_cutover_manifest_pins_repositories_and_blocks_live() -> None:
    payload = json.loads(Path("migration/runtime-cutover-manifest.json").read_text())
    assert payload["schema_version"] == "quant.runtime_cutover.v1"
    assert payload["producer_repository"] == "runchengxie/quant-research"
    assert payload["platform_repository"] == "runchengxie/quant-platform"
    assert payload["consumer_repository"] == "runchengxie/market-intel"
    assert payload["live_eligibility"] is False
    assert payload["cashflow_schemas"] == [
        "strategy_app.cashflow.selection.v1",
        "strategy_app.cashflow.executable.v1",
        "strategy_pipeline.cashflow.publication.v1",
    ]
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run --locked --extra dev python -m pytest tests/test_runtime_cutover_manifest.py -q`

Expected: FAIL because the manifest does not exist.

- [ ] **Step 3: Add the manifest with the exact current commit pins**

Write the JSON from `git rev-parse HEAD` in each isolated repository and set `live_eligibility` to `false`; do not use a branch name as a pin.

- [ ] **Step 4: Run the focused test and repository lint**

Run: `uv run --locked --extra dev python -m pytest tests/test_runtime_cutover_manifest.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add migration/runtime-cutover-manifest.json tests/test_runtime_cutover_manifest.py
git commit -m "chore: pin quant runtime cutover manifest"
```

### Task 2: Add the quant-research shadow entrypoint

**Files:**
- Create: `scripts/run_runtime_shadow.py` in quant-research
- Create: `tests/test_runtime_shadow_entrypoint.py` in quant-research
- Modify: `docs/strategy-app/cashflow-runner.md` in quant-research

**Interfaces:**
- Consumes: `strategy_app.cashflow.scheduler`, `strategy_app.cashflow.readiness`, and the installed public `strategy_pipeline` publication CLI.
- Produces: a JSON result with `status`, `strategy_repository`, `platform_repository`, `selection`, `publication`, and `live_eligibility`; it must fail closed when the source root is the old workspace.

- [ ] **Step 1: Write tests for command construction and old-root rejection**

```python
def test_shadow_entrypoint_uses_quant_research_and_public_platform(tmp_path):
    result = run_shadow(config=_fixture_config(tmp_path), run_command=fake_runner)
    assert result["status"] == "passed"
    assert result["strategy_repository"] == "runchengxie/quant-research"
    assert result["platform_repository"] == "runchengxie/quant-platform"
    assert result["live_eligibility"] is False

def test_shadow_entrypoint_rejects_research_workspace_source(tmp_path):
    with pytest.raises(RuntimeError, match="old research-workspace source"):
        run_shadow(config=_fixture_config(tmp_path, source_root=Path("/research-workspace")), run_command=fake_runner)
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `uv run --locked --extra dev python -m pytest tests/test_runtime_shadow_entrypoint.py -q`

Expected: FAIL because `run_shadow` is not defined.

- [ ] **Step 3: Implement the minimal entrypoint**

The entrypoint must invoke the readiness module, invoke the cashflow scheduler, invoke `python -m strategy_pipeline.cli cashflow-publish-shadow`, pass explicit output roots, and emit `live_eligibility=false`. It must use `Path(__file__).resolve().parents[1]` as the strategy root and reject any configured source path whose resolved name is `research-workspace`.

- [ ] **Step 4: Run tests and the quant-research cashflow suite**

Run: `uv run --locked --extra dev python -m pytest tests/test_runtime_shadow_entrypoint.py tests/strategy_app/test_cashflow_*.py -q`

Expected: PASS for the new entrypoint and all migrated cashflow tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_runtime_shadow.py tests/test_runtime_shadow_entrypoint.py docs/strategy-app/cashflow-runner.md
git commit -m "feat: run cashflow shadow from quant research"
```

### Task 3: Harden public publication and artifact provenance

**Files:**
- Modify: `packages/orchestration/src/strategy_pipeline/cashflow_publication.py` in quant-platform
- Modify: `packages/orchestration/src/strategy_pipeline/cli.py` in quant-platform
- Create: `tests/orchestration/test_cashflow_cutover_provenance.py` in quant-platform
- Modify: `docs/orchestration/cashflow-publication.md` in quant-platform

**Interfaces:**
- Consumes: `strategy_app.cashflow.selection.v1` and readiness JSON from quant-research.
- Produces: `strategy_pipeline.cashflow.publication.v1` containing producer/platform commit provenance and immutable target/receipt hashes.

- [ ] **Step 1: Add failing provenance assertions**

```python
def test_cashflow_publication_records_private_and_public_commit_provenance(tmp_path):
    publication = publish_cashflow_shadow(selection, readiness_path=readiness, output_root=tmp_path)
    receipt = json.loads(publication.receipt_path.read_text())
    assert receipt["producer_repository"] == "runchengxie/quant-research"
    assert receipt["platform_repository"] == "runchengxie/quant-platform"
    assert receipt["research_only"] is True
    assert receipt["eligible_for_live"] is False
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `uv run --locked --extra dev python -m pytest tests/orchestration/test_cashflow_cutover_provenance.py -q`

Expected: FAIL because the receipt lacks the new provenance fields.

- [ ] **Step 3: Add provenance from the cutover manifest**

Load and validate `migration/runtime-cutover-manifest.json` before publication, copy only its repository identities and commit pins into the receipt, and reject a manifest with `live_eligibility=true` or a schema mismatch.

- [ ] **Step 4: Run public orchestration tests**

Run: `uv run --locked --extra dev python -m pytest tests/orchestration/test_cashflow_publication.py tests/orchestration/test_cashflow_cutover_provenance.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/orchestration/src/strategy_pipeline/cashflow_publication.py packages/orchestration/src/strategy_pipeline/cli.py tests/orchestration/test_cashflow_cutover_provenance.py docs/orchestration/cashflow-publication.md
git commit -m "feat: attest cashflow publication provenance"
```

### Task 4: Switch market-intel to consume the migrated artifact path

**Files:**
- Modify: `scripts/run_cashflow_shadow.sh` in market-intel
- Create: `scripts/run_quant_runtime_shadow.sh` in market-intel
- Create: `tests/test_quant_runtime_shadow_script.py` in market-intel
- Modify: `scripts/setup_cron.sh` in market-intel

**Interfaces:**
- Consumes: `QUANT_RESEARCH_ROOT`, `QUANT_PLATFORM_ROOT`, and the path-free publication output.
- Produces: market-intel delivery input and receipt; the script must never set `PYTHONPATH` to quant-research and must never import its modules.

- [ ] **Step 1: Write the failing shell contract tests**

```python
def test_quant_runtime_script_points_to_quant_research_and_platform():
    source = SCRIPT.read_text()
    assert 'QUANT_RESEARCH_ROOT="${QUANT_RESEARCH_ROOT:?QUANT_RESEARCH_ROOT is required}"' in source
    assert 'QUANT_PLATFORM_ROOT="${QUANT_PLATFORM_ROOT:?QUANT_PLATFORM_ROOT is required}"' in source
    assert "research-workspace" not in source
    assert "PYTHONPATH=\"$QUANT_RESEARCH_ROOT/src\"" not in source
```

- [ ] **Step 2: Run the focused test and verify failure**

Run: `uv run --locked --extra dev python -m pytest tests/test_quant_runtime_shadow_script.py -q`

Expected: FAIL because the new script does not exist.

- [ ] **Step 3: Implement the shell bridge**

Require explicit test chat IDs, default `CASHFLOW_SEND=0`, pass the artifact and receipt paths to the existing delivery validator, and execute the quant-research entrypoint with the pinned quant-platform environment.

- [ ] **Step 4: Run offline delivery and script tests**

Run: `uv run --locked --extra dev python -m pytest tests/test_quant_runtime_shadow_script.py tests/test_cashflow_delivery.py tests/test_cashflow_shadow_script.py -q`

Expected: PASS without network access.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_quant_runtime_shadow.sh scripts/run_cashflow_shadow.sh scripts/setup_cron.sh tests/test_quant_runtime_shadow_script.py
git commit -m "feat: consume quant runtime shadow artifacts"
```

### Task 5: Quarantine external FMP tests and prove import boundaries

**Files:**
- Modify: `tests/test_etl_ai_feeds.py` in market-intel
- Modify: `pyproject.toml` in market-intel
- Create: `tests/test_network_policy.py` in market-intel
- Create: `tests/test_migrated_runtime_boundaries.py` in quant-research

**Interfaces:**
- Consumes: pytest markers and the migrated package roots.
- Produces: an offline full suite that cannot call FMP, plus an explicit `network` test marker for opt-in integration tests.

- [ ] **Step 1: Write the failing no-network test**

```python
def test_ai_source_suite_does_not_enable_network_by_default(monkeypatch):
    monkeypatch.delenv("MARKET_INTEL_ENABLE_NETWORK", raising=False)
    assert network_enabled() is False
```

- [ ] **Step 2: Run the focused test and reproduce the current leak**

Run: `uv run --locked --extra dev python -m pytest tests/test_etl_ai_feeds.py::test_run_includes_ai_sources -q`

Expected before the fix: the test may reach an external fetch when a local API-key source is present; the command must be bounded by a short timeout during diagnosis.

- [ ] **Step 3: Mark and gate FMP/network paths**

Add `pytest.ini_options.markers = ["network: tests requiring external network"]`, mark only the real network tests, and make the default code path use fixtures or explicit monkeypatches. The test must not read ambient API credentials unless `MARKET_INTEL_ENABLE_NETWORK=1` is set.

- [ ] **Step 4: Add AST/import boundary checks**

Scan quant-research runtime files for `research_workspace`, absolute `/home/richard/code/research-workspace`, and imports from old `strategy_pipeline` source paths. Scan market-intel runtime files for imports beginning with `strategy_app` or `quant_research`.

- [ ] **Step 5: Run offline full suites**

Run:

```bash
uv run --locked --extra dev python -m pytest -m 'not network' -q
uv run --locked --extra dev ruff check .
```

Expected: PASS without contacting FMP.

- [ ] **Step 6: Commit**

```bash
git add tests/test_etl_ai_feeds.py tests/test_network_policy.py pyproject.toml tests/test_migrated_runtime_boundaries.py
git commit -m "test: isolate external market-intel network checks"
```

### Task 6: Run shadow comparison and prepare, but do not execute, production cutover

**Files:**
- Create: `scripts/compare_runtime_shadow.py` in the top-level worktree
- Create: `tests/test_runtime_shadow_comparison.py` in the top-level worktree
- Create: `docs/evidence/quant-runtime-shadow-YYYYMMDD.json` after a real run
- Modify: `docs/production-update.md` in the top-level worktree

**Interfaces:**
- Consumes: old and migrated selection/publication artifacts for the same source and signal dates.
- Produces: a comparison report covering policy identity, dates, symbols, weights, artifact hashes, publication receipt, and delivery payload; a non-zero exit code on any mismatch.

- [ ] **Step 1: Write failing comparison tests**

```python
def test_runtime_comparison_rejects_symbol_or_weight_drift():
    report = compare_artifacts(old_payload, new_payload)
    assert report["status"] == "mismatch"
    assert "weights" in report["differences"]
```

- [ ] **Step 2: Implement deterministic comparison and evidence writing**

Normalize symbol ordering, compare decimal weights at `1e-12`, compare policy/date/schema fields exactly, and record both commit pins without copying local source paths into the published artifact.

- [ ] **Step 3: Run the old and migrated shadow flows with `CASHFLOW_SEND=0`**

Run both flows against the same frozen fixtures and separate output roots. Do not modify `/home/richard/code/production/*/current`.

- [ ] **Step 4: Run the comparison and record evidence**

Run: `uv run --locked --extra dev python scripts/compare_runtime_shadow.py --old /tmp/quant-runtime-shadow-old/publication/latest --new /tmp/quant-runtime-shadow-new/publication/latest --output docs/evidence/quant-runtime-shadow-20260906.json`

Expected: PASS only if the artifacts match or every intentional difference is explicitly recorded and approved.

- [ ] **Step 5: Run workspace and delegated gates**

Run the new-repository focused suites, the market-intel offline suite, and the top-level contract/import checks. Record the exact results in the evidence document.

- [ ] **Step 6: Commit evidence and cutover readiness only**

```bash
git add scripts/compare_runtime_shadow.py tests/test_runtime_shadow_comparison.py docs/evidence/quant-runtime-shadow-20260906.json docs/production-update.md
git commit -m "docs: record quant runtime shadow comparison"
```

The production pointer remains unchanged. A separate, explicitly approved release operation is required after the evidence and observation window pass.
