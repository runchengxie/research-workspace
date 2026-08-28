# Context Data Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a revision-aware `cn_context` data domain, PIT context assets, and the first TuShare macro pack without changing the existing A-share contract semantics.

**Architecture:** `market-data-platform` owns immutable raw captures, normalized context observations, release metadata, PIT selection, validation, and publication. `cn_context_current.json` uses `market=cn_context` and `provider=composite`; raw provider identity remains in manifest lineage. Research code consumes only ordinary tables and published asset references.

**Tech Stack:** Python 3, pandas, PyArrow/Parquet, YAML/JSON manifests, existing TuShare client/CLI infrastructure, pytest, Ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-28-contextual-alpha-platform-design.md`

## Global Constraints

- Preserve `a_share_current.json` with `market=a_share` and `provider=tushare`.
- Add `market=cn_context`, `provider=composite`, and `metadata/current_assets/cn_context_current.json`.
- First stable asset keys are `context_catalog`, `context_observations`, `context_pit`, `context_release_calendar`.
- `available_at` is the authoritative research-visibility timestamp.
- Historical values without release-time or observed-vintage evidence are marked reconstructed and cannot be promotion eligible.
- Immutable raw snapshots retain retrieval timestamp, source hash, parser version, and request metadata.
- New production code follows TDD: failing behavior test first, verified red, minimal implementation, verified green.

---

### Task 1: Add the `cn_context` contract domain

**Files:**
- Modify: `src/market_data_platform/paths.py`
- Modify: `src/market_data_platform/published_assets.py`
- Test: `tests/test_paths.py`
- Test: `tests/test_published_assets.py`
- Modify: `docs/contracts.md`

**Interfaces:**
- Produces: `normalize_market("cn_context") -> "cn_context"`
- Produces: `normalize_provider("composite", market="cn_context") -> "composite"`
- Produces: `current_contract_path(root, market="cn_context") -> root/metadata/current_assets/cn_context_current.json`
- Existing A-share behavior must remain byte-for-byte compatible at the API level.

- [ ] **Step 1: Write failing path-domain tests**

```python
def test_cn_context_contract_path(tmp_path):
    assert normalize_market("cn_context") == "cn_context"
    assert normalize_provider("composite", market="cn_context") == "composite"
    assert current_contract_path(tmp_path, market="cn_context") == (
        tmp_path / "metadata/current_assets/cn_context_current.json"
    )


def test_cn_context_rejects_tushare_as_contract_provider():
    with pytest.raises(ValueError, match="Unsupported provider"):
        normalize_provider("tushare", market="cn_context")
```

- [ ] **Step 2: Run the targeted tests and verify RED**

Run: `uv run --extra dev python -m pytest tests/test_paths.py -k cn_context -q`

Expected: failure because `cn_context` is not in `SUPPORTED_MARKETS`.

- [ ] **Step 3: Add the domain without changing A-share defaults**

Implement in `paths.py`:

```python
SUPPORTED_MARKETS = {"a_share", "cn_context"}
SUPPORTED_PROVIDERS_BY_MARKET = {
    "a_share": {"tushare"},
    "cn_context": {"composite"},
}
```

Keep `normalize_market(None)` and `normalize_provider(None, market="a_share")` resolving to the current A-share defaults. For `cn_context`, require explicit `provider="composite"` when provider normalization is invoked by contract-building code.

- [ ] **Step 4: Add published-contract round-trip coverage**

Create a test fixture contract with:

```json
{
  "contract": {
    "name": "cn_context_current",
    "market": "cn_context",
    "provider": "composite",
    "version": 1,
    "artifacts_root": "<tmp>",
    "target_date": "20260828"
  },
  "assets": {}
}
```

Assert `PublishedAssetContract.load(...).market == "cn_context"` and `.provider == "composite"`.

- [ ] **Step 5: Run the path and published-asset tests**

Run: `uv run --extra dev python -m pytest tests/test_paths.py tests/test_published_assets.py -q`

Expected: PASS.

- [ ] **Step 6: Document the new contract domain**

Add a `cn_context_current.json` subsection to `docs/contracts.md` that explicitly states it is a composite standardized domain and does not change A-share provider semantics.

- [ ] **Step 7: Commit**

```bash
git add src/market_data_platform/paths.py src/market_data_platform/published_assets.py tests/test_paths.py tests/test_published_assets.py docs/contracts.md
git commit -m "feat: add cn context contract domain"
```

### Task 2: Define context catalog and normalized observation contracts

**Files:**
- Create: `src/market_data_platform/context/__init__.py`
- Create: `src/market_data_platform/context/models.py`
- Create: `src/market_data_platform/context/validation.py`
- Test: `tests/test_context_models.py`

**Interfaces:**
- Produces: `ContextSeriesSpec`
- Produces: `normalize_context_catalog(frame: pd.DataFrame) -> pd.DataFrame`
- Produces: `validate_context_observations(frame: pd.DataFrame) -> ContextValidationReport`

- [ ] **Step 1: Write failing schema tests**

Test that a valid catalog row requires `series_id`, `source_id`, `provider`, `source_series_key`, `name`, `family`, `frequency`, `unit`, `value_semantics`, `revision_policy`, `availability_policy`, `expected_release_lag`, `max_staleness`, and `status`.

Test that normalized observations require:

```text
series_id, period_start, period_end, value, unit,
published_at, observed_at, ingested_at, source_retrieved_at,
available_at, vintage_id, revision_number, source_hash,
revision_covered, reconstructed
```

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_context_models.py -q`

Expected: import failure for `market_data_platform.context.models`.

- [ ] **Step 3: Implement immutable specs and validation errors**

Use frozen dataclasses for specs and a small frozen report type. Parse timestamps with `pd.to_datetime(..., utc=True, errors="raise")`. Reject duplicate `(series_id, period_end, vintage_id)` rows, `period_start > period_end`, `available_at < published_at` when `published_at` exists, `source_retrieved_at < observed_at`, empty hashes, and negative `revision_number`.

- [ ] **Step 4: Add reconstructed-history semantics**

Require `revision_covered=False` whenever `reconstructed=True`. A row with `reconstructed=False` must have non-null `source_retrieved_at` and `available_at`.

- [ ] **Step 5: Verify GREEN**

Run: `uv run --extra dev python -m pytest tests/test_context_models.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/market_data_platform/context tests/test_context_models.py
git commit -m "feat: define context observation contracts"
```

### Task 3: Implement revision-aware PIT selection

**Files:**
- Create: `src/market_data_platform/context/pit.py`
- Test: `tests/test_context_pit.py`

**Interfaces:**
- Produces: `ContextPITPanel(frame: pd.DataFrame, audit: Mapping[str, object])`
- Produces: `select_context_as_of(observations, *, as_of, series_ids=None, require_revision_covered=True, max_staleness_days=None) -> ContextPITPanel`

- [ ] **Step 1: Write a future-publication leakage test**

Create two periods where the second has `available_at=2026-02-02`. Assert an `as_of=2026-01-31` selection cannot contain the second row.

- [ ] **Step 2: Write a revision-selection test**

For one `series_id + period_end`, create vintage 1 available January 10 and vintage 2 available January 20. Assert January 15 returns vintage 1 and January 25 returns vintage 2.

- [ ] **Step 3: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_context_pit.py -q`

Expected: import failure for `select_context_as_of`.

- [ ] **Step 4: Implement selection**

Filter `available_at <= as_of`, then stable-sort by `series_id`, `period_end`, `available_at`, `revision_number`, `source_retrieved_at`, and keep the last visible row per `(series_id, period_end)`. Reject requested series that have no eligible observation when strict mode is active.

- [ ] **Step 5: Add audit and staleness behavior**

Audit keys must include `revision_covered`, `freshness_verified`, `series_missing`, `series_stale`, `selected_vintages`, `max_observation_age`, and `reconstructed_series`. Staleness is measured from the selected row's `available_at` to `as_of`; when a per-series catalog limit is supplied, use that limit instead of one global limit.

- [ ] **Step 6: Verify GREEN**

Run: `uv run --extra dev python -m pytest tests/test_context_pit.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/market_data_platform/context/pit.py tests/test_context_pit.py
git commit -m "feat: add revision aware context pit loader"
```

### Task 4: Add immutable raw snapshot and publication helpers

**Files:**
- Create: `src/market_data_platform/context/snapshots.py`
- Create: `src/market_data_platform/context/publish.py`
- Test: `tests/test_context_snapshots.py`
- Test: `tests/test_context_publish.py`

**Interfaces:**
- Produces: `seal_context_snapshot(...) -> Path`
- Produces: `publish_context_assets(...) -> Path`

- [ ] **Step 1: Write failing snapshot tests**

Assert a sealed snapshot writes `raw.bin`, `receipt.json`, and `manifest.seal.json` containing SHA-256, byte count, retrieval timestamp, provider, dataset, source locator, parser version, and request metadata. Assert an existing sealed target is never overwritten.

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_context_snapshots.py -q`

Expected: module import failure.

- [ ] **Step 3: Implement atomic sealing**

Write to a sibling temporary directory, fsync/close files, compute hashes, then rename into the final `vintage=<UTC timestamp>` directory. Existing completed directories raise `FileExistsError`.

- [ ] **Step 4: Write publication tests**

Create tiny Parquet fixtures for catalog, observations, PIT, and release calendar. Assert publication creates manifests, latest aliases, and a `cn_context_current.json` with exactly the four stable asset keys and `provider=composite`.

- [ ] **Step 5: Implement publication with existing manifest conventions**

Reuse the repository's manifest helpers where possible. Do not create a second dataset-registry format. Composite asset manifest lineage must list every raw snapshot receipt used to produce the asset.

- [ ] **Step 6: Verify GREEN**

Run: `uv run --extra dev python -m pytest tests/test_context_snapshots.py tests/test_context_publish.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/market_data_platform/context tests/test_context_snapshots.py tests/test_context_publish.py
git commit -m "feat: seal and publish context assets"
```

### Task 5: Add the TuShare macro adapter pack

**Files:**
- Create: `src/market_data_platform/providers/tushare_context.py`
- Test: `tests/test_tushare_context.py`
- Modify: `docs/operations/a-share-tushare.md`

**Interfaces:**
- Produces: `TUSHARE_CONTEXT_ENDPOINTS`
- Produces: `fetch_tushare_context_endpoint(client, endpoint, *, start_date=None, end_date=None) -> pd.DataFrame`
- Produces: `normalize_tushare_context(endpoint, raw, *, retrieved_at) -> tuple[pd.DataFrame, pd.DataFrame]` where the tuple is observations and release-calendar rows.

- [ ] **Step 1: Write endpoint contract tests**

Freeze the first endpoint set to `shibor`, `shibor_lpr`, `cn_m`, `sf_month`, `cn_pmi`, `cn_cpi`, `cn_ppi`, `cn_gdp`, `cn_schedule`. Use fake client responses, not network calls.

- [ ] **Step 2: Write release-date fallback tests**

Assert an observation with an explicit source release date gets `available_at` from that date using the conservative next-A-share-session rule. If no source release evidence or matching `cn_schedule` record exists, assert `reconstructed=True` and `revision_covered=False`.

- [ ] **Step 3: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_tushare_context.py -q`

Expected: module import failure.

- [ ] **Step 4: Implement thin endpoint fetching**

Reuse the existing TuShare API/client mechanism and its retry/limit behavior. Adapter code must not read credentials directly and must not write files.

- [ ] **Step 5: Implement endpoint-specific normalization maps**

Map provider columns to stable `series_id` values. Preserve provider source keys in lineage fields. Do not dynamically publish arbitrary new columns: unknown fields are ignored unless explicitly catalogued; required expected fields missing from a response raise a schema error.

- [ ] **Step 6: Verify GREEN**

Run: `uv run --extra dev python -m pytest tests/test_tushare_context.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/market_data_platform/providers/tushare_context.py tests/test_tushare_context.py docs/operations/a-share-tushare.md
git commit -m "feat: add tushare context macro pack"
```

### Task 6: Add `marketdata context` CLI and end-to-end publication test

**Files:**
- Create: `src/market_data_platform/cli_context.py`
- Modify: `src/market_data_platform/cli.py`
- Test: `tests/test_cli_context.py`
- Modify: `docs/operations.md`
- Modify: `README.md`

**Interfaces:**
- Produces commands:
  - `marketdata context fetch --provider tushare --dataset <endpoint>`
  - `marketdata context build --as-of YYYYMMDD`
  - `marketdata context publish --as-of YYYYMMDD`
  - `marketdata context inspect --as-of YYYYMMDD`

- [ ] **Step 1: Write CLI parser tests**

Assert all four subcommands parse to a callable handler and `fetch` only accepts provider `tushare` in PR 1.

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_cli_context.py -q`

Expected: `marketdata context` is unknown.

- [ ] **Step 3: Implement command registration**

Add `add_context_parser(subparsers)` in `cli.py`. Keep provider credentials and network construction in existing provider helpers. `build` and `publish` consume sealed raw snapshots; they do not refetch.

- [ ] **Step 4: Add an offline end-to-end fixture test**

Use a fake TuShare response fixture, seal it, normalize it, build PIT, publish four assets, load `PublishedAssetContract.load_current(tmp_path, market="cn_context")`, and assert a PIT query before release cannot see the observation while a query after release can.

- [ ] **Step 5: Run the full relevant test set**

Run:

```bash
uv run --extra dev python -m pytest \
  tests/test_paths.py \
  tests/test_published_assets.py \
  tests/test_context_models.py \
  tests/test_context_pit.py \
  tests/test_context_snapshots.py \
  tests/test_context_publish.py \
  tests/test_tushare_context.py \
  tests/test_cli_context.py -q
```

Expected: PASS.

- [ ] **Step 6: Run repository quality gates**

Run:

```bash
uv run --extra dev python scripts/dev/run_pytest_isolated.py -- -q
uv run --extra dev python -m ruff check .
uv run --extra dev python -m ruff format --check .
uv run --extra dev ty check --error-on-warning
uv run --extra dev python scripts/dev/quality_debt.py
uv run --extra dev python scripts/dev/maintainability_metrics.py
uv run --extra dev python scripts/dev/compatibility_governance.py --check
uv run --extra dev python scripts/dev/architecture_governance.py --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/market_data_platform/cli.py src/market_data_platform/cli_context.py tests/test_cli_context.py docs/operations.md README.md
git commit -m "feat: publish contextual macro assets"
```
