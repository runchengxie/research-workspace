## Why

`research-workspace` and `cross-sectional-trees` both contain useful documentation, but too many process records and historical research notes still look like current entry points. This change reduces maintenance ambiguity by making active docs, reference docs, archived records, and superseded research provenance explicit.

## What Changes

- Add a shared documentation lifecycle rule for status metadata, source-of-truth ownership, and archive routing.
- Keep `research-workspace` focused on cross-repo workflow, contracts, current version combinations, release gates, and the A-share / Hong Kong market transition playbook.
- Consolidate top-level Hong Kong market archive, public demo, private archive, and legacy-surface guidance into a single human-readable archive entry backed by structured manifests.
- Move one-time handoffs, release notes, freeze notes, and restore records out of primary reading paths under archive records.
- Reclassify `cross-sectional-trees` Hong Kong market historical research notes as archive material and keep only short active entry points or summaries in active docs.
- Merge or shrink overlapping `cross-sectional-trees` playbooks and concept pages where they describe the same legacy Hong Kong market data boundary or model-selection guidance.
- Update docs indexes and documentation tests so renamed or archived files remain discoverable without preserving stale active-entry semantics.

## Capabilities

### New Capabilities

- `docs-lifecycle-governance`: Defines how cross-repo documentation is classified, indexed, archived, and verified so maintainers can identify the current source of truth quickly.

### Modified Capabilities

- None.

## Impact

- Affected systems: top-level `docs/`, `openspec/`, `cross-sectional-trees/docs/`, and documentation contract tests in both repositories.
- Affected workflows: onboarding, A-share migration readiness review, Hong Kong market archive restore review, public-demo export review, and research-note handoff.
- No runtime API, provider API, asset key, broker integration, or data contract changes are intended.
- Existing public paths may be moved only with index updates, compatibility links, or explicit archive entries; canonical current contract naming remains `metadata/current_assets/a_share_current.json`.
