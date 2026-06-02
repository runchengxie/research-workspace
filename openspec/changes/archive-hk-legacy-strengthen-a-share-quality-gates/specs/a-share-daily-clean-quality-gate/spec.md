## ADDED Requirements

### Requirement: Daily clean validation emits a structured quality report
The A 股 `daily_clean` validator SHALL emit a versioned JSON report with `status`, `quality_verdict`, `checks`, `metrics`, `samples`, `lineage`, and scanner telemetry. Each check MUST have a stable identifier and severity. Samples MUST be bounded.

#### Scenario: Write a successful report
- **WHEN** a maintainer validates a conforming A 股 `daily_clean` asset with `--out report.json`
- **THEN** the validator writes a versioned report whose verdict passes and whose metrics can be audited without rescanning the full asset

#### Scenario: Report invalid rows
- **WHEN** a row-level rule finds invalid data
- **THEN** the report includes the stable check identifier, affected-row count, bounded sample rows, and resulting severity

### Requirement: Baseline profile checks structural and price invariants
The baseline validation profile MUST verify required columns, file readability, manifest presence, manifest-to-file totals, symbol format, trade-date format, unique `symbol` plus `trade_date`, numeric price fields, non-negative volume and amount, positive non-suspended prices, and OHLC bounds.

#### Scenario: Reject invalid OHLC bounds
- **WHEN** a non-suspended row has `high < max(open, close, low)` or `low > min(open, close, high)`
- **THEN** the baseline quality verdict fails and reports the offending row count and bounded samples

#### Scenario: Reject manifest drift
- **WHEN** actual rows, symbols, files, or date range do not match the `daily_clean` manifest
- **THEN** the baseline quality verdict fails with manifest reconciliation diagnostics

### Requirement: Research profile checks A 股 market overlays
The research validation profile MUST include the baseline checks and require valuation columns, limit-status columns, a trading-calendar input, suspension flags, limit flags, board classification, listed-days values, and ST provenance. It MUST check trading-calendar coverage, limit-price ordering, limit-flag consistency, suspension consistency, non-negative listed days, and board classification derived from the symbol.

#### Scenario: Reject inconsistent limit flags
- **WHEN** `is_limit_up` or `is_limit_down` disagrees with `close`, `up_limit`, or `down_limit`
- **THEN** the research quality verdict fails and reports the inconsistent rows

#### Scenario: Reject missing trading dates
- **WHEN** the trading calendar declares an open date in the requested asset range but the `daily_clean` asset has no rows for that date
- **THEN** the research quality verdict fails with the missing-date list or a bounded sample

#### Scenario: Record non-PIT ST provenance
- **WHEN** `is_st` is derived only from the latest instruments snapshot
- **THEN** the report records the static provenance limitation and MUST NOT describe the field as PIT-safe

### Requirement: Warning thresholds are explicit and configurable
The validator SHALL support configurable severity thresholds and row-error-rate limits. Price-change consistency and other heuristic checks MAY emit warnings within the configured tolerance, while structural corruption MUST remain hard failures regardless of the tolerated warning rate.

#### Scenario: Warn on price-change mismatch
- **WHEN** `pct_chg` differs from the value implied by `close` and `pre_close` beyond the configured tolerance
- **THEN** the validator emits a warning check with affected-row count and bounded samples

#### Scenario: Keep structural corruption blocking
- **WHEN** a structural check fails and the tolerated warning rate is non-zero
- **THEN** the report still fails because structural failures cannot be downgraded by the warning threshold

### Requirement: Validation uses memory-aware streaming
The A 股 `daily_clean` validator SHALL use the reusable memory-aware Parquet scanner and MUST aggregate checks incrementally with bounded state.

#### Scenario: Validate without whole-file pandas reads
- **WHEN** the validator scans a symbol-partitioned `daily_clean` asset
- **THEN** it uses projected Parquet batches, records scanner telemetry, and avoids reading each symbol file as one pandas frame

### Requirement: Publication requires an accepted quality report
The A 股 current refresh and publication workflow MUST require an accepted baseline report before updating aliases or rebuilding canonical `metadata/current_assets/a_share_current.json`. Research readiness claims MUST additionally require an accepted research-profile report. `daily_basic` valuation overlays MUST NOT be described as PIT fundamentals.

#### Scenario: Block alias update after failed validation
- **WHEN** the baseline quality report fails
- **THEN** the current refresh workflow does not update aliases or rebuild the canonical A 股 current contract

#### Scenario: Keep PIT claims separate
- **WHEN** only `daily_clean` and `daily_basic` overlays have passed validation
- **THEN** the readiness output may report a reproducible price-only baseline but MUST NOT report complete PIT research data
