# Publication contract field crosswalk

> status: staging-only
> verified: 2026-09-06

The architecture uses two deliberately separate metadata layers. The generic
`research.platform-publication.v1` manifest is a transport and disclosure
contract; the semantic provenance of each projection remains in its domain
artifact contract or paired receipt.

| Requirement | Authoritative location | Purpose |
| --- | --- | --- |
| `artifact_type`, `schema_version` | projection schema and `PlatformPublicationArtifact.schema_version` | Identify the semantic file type and its version |
| `producer_commit` | `PlatformPublicationManifest.producer_commit` | Pin the producing repository revision |
| `strategy_id` | strategy registry and paired strategy receipt | Identify the strategy without exposing implementation paths |
| `as_of` | domain projection/receipt | Identify the data or research clock |
| `created_at` | publication manifest `generated_at` and domain receipt `generated_at` | Identify creation time at transport and domain layers |
| `quality_status` | domain receipt contract | Fail closed before rendering or delivery |
| `source_manifest` | domain receipt `inputs`/`artifacts` lineage | Describe approved source artifacts without local filesystem paths |
| SHA-256 and audience | `PlatformPublicationArtifact` | Verify content identity and disclosure boundary |

For DailyWatch20, `selection_receipt.json` is the semantic companion to
`watchlist_20.csv`; its contract requires quality, timing, model, feature,
lineage, and source information. The generic publication manifest wraps both
files and adds producer identity, consumer targeting, relative paths, and
content hashes. This preserves the existing rule that the public transport
contract must not contain strategy logic, provider credentials, or local source
paths.

This crosswalk is the compatibility rule for the migration. A future artifact
may use a single self-describing envelope, but it must not silently move
semantic provenance into the generic transport manifest or weaken the paired
receipt gate.
