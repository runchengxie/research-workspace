## ADDED Requirements

### Requirement: Compatibility inventory
The system SHALL maintain an inventory for compatibility surfaces, migration-only commands, and legacy aliases. Each inventory entry MUST record purpose, risk, preferred replacement, cleanup condition, current status, and audit evidence.

#### Scenario: Existing compatibility surface is reviewed
- **WHEN** a developer reviews `hkdata`, `hk_data_platform.*`, provider re-export modules, migration commands, legacy console scripts, or historical release presets
- **THEN** the inventory identifies why the surface exists and what condition allows removal or archival

#### Scenario: Compatibility inventory is incomplete
- **WHEN** a compatibility surface exists in project scripts, packages, or CLI definitions without an inventory entry
- **THEN** the governance check fails and names the undocumented surface

### Requirement: New compatibility requires lifecycle metadata
The system MUST reject new compatibility aliases, migration commands, or re-export modules unless they are documented in the compatibility inventory before merge.

#### Scenario: New legacy alias is added
- **WHEN** a change adds a new console script alias, import re-export, or migration helper
- **THEN** the governance check requires a matching inventory entry with cleanup criteria

### Requirement: Deprecation and removal workflow
The system SHALL require repo-local usage audit before deprecating or removing a compatibility surface. Removal MUST include documented migration guidance and MUST preserve rollback by keeping the last known replacement path clear.

#### Scenario: Compatibility item has no repo-local users
- **WHEN** repo-local audit finds no usage of a compatibility item outside tests and documentation
- **THEN** the item can move to deprecated status with replacement guidance
- **AND** removal can be scheduled only after downstream usage is checked or explicitly waived

#### Scenario: Downstream usage remains unknown
- **WHEN** downstream usage for a compatibility item has not been audited
- **THEN** the item MUST remain available or guarded by a deprecation warning rather than removed

### Requirement: Migration commands do not accumulate new business behavior
Migration-only commands SHALL remain limited to transition support and historical import/sync workflows. New platform behavior MUST be implemented in native platform commands or internal tools rather than expanding migration commands.

#### Scenario: New HK asset production behavior is requested
- **WHEN** a developer adds a new HK asset production or release behavior
- **THEN** the behavior is implemented under the native platform workflow rather than `marketdata migration`

#### Scenario: One-time migration is complete
- **WHEN** a migration command has met its cleanup condition and downstream usage has been audited
- **THEN** the command is archived, deprecated, or removed according to the compatibility inventory
