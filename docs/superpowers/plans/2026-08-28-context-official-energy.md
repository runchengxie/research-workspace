# Official Context Energy Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add failure-closed National Bureau of Statistics and National Energy Administration adapters that feed observed/reconstructed activity and energy vintages into the existing `cn_context` core.

**Architecture:** Provider adapters only fetch and parse official public responses into provider-neutral rows; the context core from the preceding plan owns snapshot sealing, observation validation, PIT construction, and publication. Parser fixtures pin source structure and publication metadata so structural drift fails loudly.

**Tech Stack:** Python 3 standard HTTP/client abstractions already used by `market-data-platform`, pandas, HTML/JSON parsing already available in the repository, pytest fixtures, existing context snapshot/PIT APIs.

**Spec:** `docs/superpowers/specs/2026-08-28-contextual-alpha-platform-design.md`

## Global Constraints

- Official adapters must never depend on AKShare objects or schemas across module boundaries.
- Raw response bytes or page HTML must be sealable before parsing.
- If historical publication availability cannot be proven, observations are `reconstructed=True` and `revision_covered=False`.
- Parser structure drift raises an explicit error; it never silently returns a partial table.
- Catalog additions are explicit and reviewed; parsers do not auto-publish unknown columns.
- New production code follows TDD with verified red and green runs.

---

### Task 1: Add an official-source parsing boundary

**Files:**
- Create: `src/market_data_platform/context/source_payload.py`
- Test: `tests/test_context_source_payload.py`

**Interfaces:**
- Produces: `SourcePayload(provider: str, dataset: str, source_locator: str, retrieved_at: datetime, content_type: str, body: bytes, metadata: Mapping[str, object])`
- Produces: `sha256` property used by raw snapshot lineage.

- [ ] **Step 1: Write failing immutability/hash tests**

Create a payload from fixed bytes and assert its SHA-256 is deterministic, its body is bytes, and mutation is rejected by the frozen dataclass.

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_context_source_payload.py -q`

Expected: module import failure.

- [ ] **Step 3: Implement the minimal provider-neutral payload type**

Do not put parser-specific methods on it. Provide only immutable source evidence plus `sha256` and `byte_count`.

- [ ] **Step 4: Verify GREEN and commit**

Run: `uv run --extra dev python -m pytest tests/test_context_source_payload.py -q`

```bash
git add src/market_data_platform/context/source_payload.py tests/test_context_source_payload.py
git commit -m "feat: add official source payload boundary"
```

### Task 2: Add National Bureau of Statistics activity/energy parsing

**Files:**
- Create: `src/market_data_platform/providers/nbs_context.py`
- Create: `tests/fixtures/context/nbs_activity_response.json`
- Create: `tests/fixtures/context/nbs_release_page.html`
- Test: `tests/test_nbs_context.py`

**Interfaces:**
- Produces: `NBS_CONTEXT_SERIES`
- Produces: `parse_nbs_activity(payload: SourcePayload) -> pd.DataFrame`
- Produces: `parse_nbs_release_metadata(payload: SourcePayload) -> pd.DataFrame`
- Produces: `fetch_nbs_payload(client, *, dataset, period) -> SourcePayload`

- [ ] **Step 1: Write fixture-based schema tests**

Freeze catalogued series for industrial value-added YoY, total generation, thermal, hydro, nuclear, wind, solar generation, coal output, crude-oil output, and natural-gas output where the official fixture exposes the field.

Assert output columns are exactly the provider-neutral staging columns expected by the context normalizer: `source_series_key`, `period_start`, `period_end`, `value`, `unit`, `published_at`, `source_locator`.

- [ ] **Step 2: Write structural-drift tests**

Delete the response dimension key or rename the value field in a fixture copy and assert `NBSContextSchemaError` instead of an empty/partial frame.

- [ ] **Step 3: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_nbs_context.py -q`

Expected: module import failure.

- [ ] **Step 4: Implement fetch and parser separation**

`fetch_nbs_payload` returns raw evidence only. `parse_nbs_activity` never performs network I/O. Parse numeric values conservatively; source placeholders such as empty strings or `--` become missing values and remain missing through normalization.

- [ ] **Step 5: Implement publication-time evidence**

Use official release-page timestamp/date where available. When only a date exists, keep that date and let the shared context availability policy map it to the next eligible A-share trading session. If no release evidence is found, leave `published_at` null so normalization marks the row reconstructed.

- [ ] **Step 6: Verify GREEN and commit**

Run: `uv run --extra dev python -m pytest tests/test_nbs_context.py -q`

```bash
git add src/market_data_platform/providers/nbs_context.py tests/test_nbs_context.py tests/fixtures/context/nbs_activity_response.json tests/fixtures/context/nbs_release_page.html
git commit -m "feat: add nbs activity context adapter"
```

### Task 3: Add National Energy Administration electricity parsing

**Files:**
- Create: `src/market_data_platform/providers/nea_context.py`
- Create: `tests/fixtures/context/nea_electricity_release.html`
- Test: `tests/test_nea_context.py`

**Interfaces:**
- Produces: `NEA_CONTEXT_SERIES`
- Produces: `parse_nea_electricity_release(payload: SourcePayload) -> pd.DataFrame`
- Produces: `fetch_nea_payload(client, *, source_locator) -> SourcePayload`

- [ ] **Step 1: Write known-layout parsing tests**

Fixture must yield total electricity consumption plus primary, secondary, tertiary, and residential consumption when present, with YoY measures catalogued separately from levels.

- [ ] **Step 2: Write unit and title-drift tests**

Change the fixture unit from the expected unit or remove the release title/date element. Assert `NEAContextSchemaError`; no guessed conversion is allowed in the parser.

- [ ] **Step 3: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_nea_context.py -q`

Expected: module import failure.

- [ ] **Step 4: Implement deterministic HTML extraction**

Locate the published date and the explicit statistic/value phrases required by the frozen series map. Normalize Chinese punctuation and whitespace only. Do not infer unmentioned industry breakdowns.

- [ ] **Step 5: Verify GREEN and commit**

Run: `uv run --extra dev python -m pytest tests/test_nea_context.py -q`

```bash
git add src/market_data_platform/providers/nea_context.py tests/test_nea_context.py tests/fixtures/context/nea_electricity_release.html
git commit -m "feat: add nea electricity context adapter"
```

### Task 4: Wire official providers into `marketdata context fetch/build`

**Files:**
- Modify: `src/market_data_platform/cli_context.py`
- Modify: `src/market_data_platform/context/catalog.py`
- Test: `tests/test_cli_context.py`
- Create: `tests/test_context_official_integration.py`
- Modify: `docs/operations.md`

**Interfaces:**
- Extends `marketdata context fetch --provider` to `tushare|nbs|nea`.
- Existing `build/publish/inspect` commands remain provider-neutral.

- [ ] **Step 1: Write failing CLI acceptance tests**

Assert `nbs` and `nea` are accepted by `fetch`, while unsupported provider names fail parsing. Assert `build` can consume sealed snapshots from all three provider names in one run.

- [ ] **Step 2: Verify RED**

Run: `uv run --extra dev python -m pytest tests/test_cli_context.py tests/test_context_official_integration.py -q`

Expected: providers are currently unsupported.

- [ ] **Step 3: Register adapters without changing current-contract provider**

Fetcher registry maps provider names to raw fetch functions. Normalizer registry maps provider/dataset to parser and series map. Publication still emits `provider=composite` in `cn_context_current.json`.

- [ ] **Step 4: Add observed vs reconstructed integration coverage**

Build a tiny NBS release with published-date evidence and an older fixture with no release evidence. Assert the first can become `revision_covered=True` once its raw vintage is observed, while the second remains reconstructed and makes promotion audit false.

- [ ] **Step 5: Run relevant and full gates**

Run:

```bash
uv run --extra dev python -m pytest \
  tests/test_context_source_payload.py \
  tests/test_nbs_context.py \
  tests/test_nea_context.py \
  tests/test_context_official_integration.py \
  tests/test_cli_context.py -q
uv run --extra dev python scripts/dev/run_pytest_isolated.py -- -q
uv run --extra dev python -m ruff check .
uv run --extra dev python -m ruff format --check .
uv run --extra dev ty check --error-on-warning
uv run --extra dev python scripts/dev/architecture_governance.py --check
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add src/market_data_platform/cli_context.py src/market_data_platform/context/catalog.py tests/test_cli_context.py tests/test_context_official_integration.py docs/operations.md
git commit -m "feat: publish official activity context sources"
```
