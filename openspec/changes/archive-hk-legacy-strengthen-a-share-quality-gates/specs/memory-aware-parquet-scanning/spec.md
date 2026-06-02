## ADDED Requirements

### Requirement: Scanner reads Parquet data in projected batches
The data platform SHALL provide a reusable Parquet scanner that uses explicit column projection and batch iteration. Validation workflows MUST NOT require loading an entire multi-part dataset or an entire large Parquet file into pandas memory before checks can run.

#### Scenario: Scan a large symbol file
- **WHEN** a validation workflow scans a Parquet file larger than one configured batch
- **THEN** the scanner yields projected batches incrementally and the workflow computes its result without a whole-file pandas read

#### Scenario: Read only required columns
- **WHEN** a quality check declares a subset of columns
- **THEN** the scanner requests only available required columns and reports missing requested columns separately

### Requirement: Memory policy adapts batch work to runtime pressure
The scanner SHALL sample available system memory and process RSS before and during long scans. It MUST use bounded configuration for minimum and maximum batch rows, reduce or flush pending work under soft memory pressure, and abort under hard memory pressure with a diagnostic error. When platform memory snapshots are unavailable, it SHALL continue with a bounded configured fallback batch size.

#### Scenario: Reduce batch work under soft pressure
- **WHEN** available memory falls below the configured soft limit during a scan or compaction step
- **THEN** the workflow flushes pending work or reduces subsequent batch rows, records the reason, and continues if the hard limit is not exceeded

#### Scenario: Abort under hard pressure
- **WHEN** available memory falls below the configured hard limit
- **THEN** the workflow aborts before starting additional batch work and reports available memory, RSS, configured limits, and the active file or stage

#### Scenario: Use bounded fallback without Linux memory telemetry
- **WHEN** available-memory or RSS telemetry cannot be read on the current platform
- **THEN** the scanner uses configured bounded batch rows and records that adaptive telemetry was unavailable

### Requirement: Scanner emits diagnostic telemetry
The scanner SHALL emit bounded telemetry suitable for structured reports. Telemetry MUST include files scanned, batches scanned, rows scanned, projected columns, configured and effective batch rows, available memory samples, RSS samples, estimated bytes per row when available, and flush or abort reasons.

#### Scenario: Inspect a successful scan
- **WHEN** a batch scan completes successfully
- **THEN** its report contains bounded telemetry that identifies how much work was scanned and whether memory pressure changed the batch strategy

### Requirement: Compaction avoids unbounded staging concatenation
Memory-managed compaction workflows SHALL write bounded batches through a streaming sink such as a Parquet writer. They MUST NOT concatenate every staging part for a large logical partition before writing the compacted output.

#### Scenario: Compact many staging parts for one symbol
- **WHEN** one symbol has more staging rows than the configured in-memory batch limit
- **THEN** compaction writes multiple bounded batches to the output file and records compaction telemetry without loading all symbol parts together
