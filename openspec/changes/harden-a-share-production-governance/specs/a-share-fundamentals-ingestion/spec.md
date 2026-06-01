## ADDED Requirements

### Requirement: TuShare 基本面 datasets are declared by spec
The data platform SHALL define TuShare A 股基本面 dataset specs before implementing download logic for those datasets.

#### Scenario: Supported dataset is downloaded
- **WHEN** a dataset such as `income`, `balancesheet`, `cashflow`, `forecast`, `express`, `dividend`, `fina_indicator`, `fina_audit`, `fina_mainbz`, or `disclosure_date` is downloaded
- **THEN** its spec declares API name, VIP API name if any, date fields, report-period fields, primary keys, dedupe keys, required columns, refresh mode, and entitlement requirements

#### Scenario: Dataset has special fetch semantics
- **WHEN** a dataset requires per-day, per-quarter, or per-symbol querying
- **THEN** its spec declares that fetch granularity and the downloader records it in the run metadata

### Requirement: Raw downloader is stateful and restartable
The TuShare 基本面 raw downloader SHALL persist state, failures, query windows, and contiguous progress so interrupted runs can be resumed without silent gaps.

#### Scenario: Download fails for one period
- **WHEN** a period, date, or symbol download fails after retries
- **THEN** the downloader records a machine-readable failure report and does not advance the contiguous watermark past the failed unit

#### Scenario: Download is restarted
- **WHEN** a maintainer reruns the same dataset after a partial failure
- **THEN** the downloader uses persisted state to skip completed units and retry failed or stale units

### Requirement: Entitlement and VIP behavior is explicit
The downloader SHALL distinguish VIP batch APIs, non-VIP APIs, skipped datasets, and unsupported fallbacks in output metadata.

#### Scenario: VIP API is unavailable
- **WHEN** the configured token or entitlement does not support a required VIP batch API
- **THEN** the run fails or records the dataset as skipped according to policy, and the current contract is not updated as if the dataset were complete

#### Scenario: Non-VIP fallback exists
- **WHEN** a safe per-symbol or per-date fallback is implemented
- **THEN** the dataset spec declares the fallback and the run metadata records that the fallback path was used

### Requirement: API pagination is guarded
The raw downloader SHALL guard paginated TuShare API calls against truncation, duplicate pages, empty-page ambiguity, and field drift.

#### Scenario: Page repeats
- **WHEN** two consecutive API pages have the same signature for a dataset/query
- **THEN** the downloader stops or fails that query with a duplicate-page warning rather than appending repeated rows silently

#### Scenario: Response lacks required columns
- **WHEN** TuShare returns a frame missing required columns from the dataset spec
- **THEN** the query fails validation and is recorded in the failure report

### Requirement: Raw assets preserve provenance
Raw 基本面 assets SHALL preserve retrieval metadata and source semantics without prematurely applying research-specific PIT decisions.

#### Scenario: Raw rows are written
- **WHEN** raw dataset rows are persisted
- **THEN** the asset manifest records dataset, API endpoint, query parameters, retrieved timestamp, row count, symbols or periods covered, schema hash, and source entitlement mode

#### Scenario: Multiple report types exist
- **WHEN** TuShare returns rows for multiple report types or statement scopes
- **THEN** raw storage preserves the report-type field or records a deliberate filter policy instead of deduping it away silently

### Requirement: Normalized assets separate raw schema from research schema
The platform SHALL build normalized A 股基本面 assets from raw downloads before PIT conversion.

#### Scenario: Normalized frame is built
- **WHEN** a raw dataset is normalized
- **THEN** the output uses canonical symbol/date columns, validates required fields, resolves duplicate policy, and writes a manifest linked to the raw inputs

#### Scenario: Normalization drops rows
- **WHEN** invalid symbols, invalid dates, duplicate keys, or unsupported report types are removed
- **THEN** the manifest records dropped row counts and reasons

### Requirement: PIT fundamentals prevent look-ahead bias
PIT 基本面 outputs SHALL use report period, disclosure date, availability date, availability delay, and selected field mappings before they are allowed into research configs as financial-statement features.

#### Scenario: Disclosure date follows report period
- **WHEN** a report period is disclosed after the period end
- **THEN** research rows before the availability date cannot see that report's fields

#### Scenario: Disclosure date is missing
- **WHEN** a raw row lacks a usable disclosure or announcement date
- **THEN** the PIT builder rejects the row or applies an explicitly configured conservative delay policy recorded in the manifest

### Requirement: Current contract publication is gated by validation
A 股基本面 assets SHALL be added to `a_share_current.json` and `dataset_registry.csv` only after validation and manifest checks pass.

#### Scenario: PIT validation passes
- **WHEN** PIT fundamentals validation confirms required columns, date semantics, symbol coverage, duplicate policy, and availability-delay semantics
- **THEN** the current contract may include the corresponding `pit_fundamentals` asset key

#### Scenario: Validation fails
- **WHEN** raw, normalized, or PIT validation fails
- **THEN** the platform retains the generated report for debugging but does not repoint latest aliases or current-contract keys
