## ADDED Requirements

### Requirement: A-share is the active workspace direction
The superproject SHALL describe A-share data, research, and execution as the active direction while describing HK strategy work as frozen, legacy, or explicitly compatibility/restoration scoped.

#### Scenario: Reader opens workspace entry documentation
- **WHEN** a reader opens the top-level README or documentation index
- **THEN** the active workflow is described as data platform to strategy research to execution for A-share work, with HK public demo and HK restore paths called out as separate legacy references

#### Scenario: Documentation mentions HK surfaces
- **WHEN** documentation mentions retained HK code, data, or research surfaces
- **THEN** it classifies them as shared active, frozen compatibility, archived provenance, or retire-after-audit rather than presenting them as the default active research lane

### Requirement: Canonical contracts and market wording are preserved
The superproject SHALL preserve existing public contract names and use clear market wording in documentation and user-facing text.

#### Scenario: A-share current contract is documented
- **WHEN** documentation names the canonical A-share current contract
- **THEN** it uses `metadata/current_assets/a_share_current.json` as the authoritative path and treats `cn_current.json` only as a historical compatibility alias when mentioned

#### Scenario: Market names appear in prose
- **WHEN** documentation describes market scope in prose
- **THEN** it uses wording such as `中国香港市场`, `港股`, `港股通`, `中国大陆市场`, and `A 股`, while keeping commands, paths, config keys, and historical filenames unchanged

### Requirement: HK restore-sensitive code is not removed prematurely
The workspace SHALL keep HK restore-critical and compatibility code until restore evidence, source tags, archive manifests, and downstream consumer audits prove the code can be retired safely.

#### Scenario: Implementation proposes deleting HK code
- **WHEN** an implementation task proposes deleting or moving HK restore, release, research, or execution compatibility code
- **THEN** it must reference current restore drill evidence, consumer audit results, rollback evidence, and a separate retirement decision before deletion proceeds

#### Scenario: Restore evidence is unavailable locally
- **WHEN** cold-storage snapshots or remote release assets are not available in the current environment
- **THEN** HK restore-sensitive code remains retained and documented as compatibility/provenance rather than removed

### Requirement: A-share readiness is not overstated
The superproject SHALL distinguish staged A-share baseline readiness from complete PIT research data, production strategy evidence, and broker trading enablement.

#### Scenario: A-share readiness is summarized
- **WHEN** documentation or scripts summarize A-share readiness
- **THEN** they identify the current evidence tier and do not claim complete PIT research data, production alpha readiness, or broker trading enablement without the required evidence manifests

#### Scenario: Execution handoff is described
- **WHEN** the workspace describes `targets.json` handoff to `quant-execution-engine`
- **THEN** it states that dry-run evidence and broker-specific execution gates remain separate from research export success
