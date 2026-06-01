## Why

The workspace has already frozen the heavy China Hong Kong market research/data surface and is moving active work toward A-share data, research, and execution. Keeping the legacy HK narrative inside the active workspace without a clear public snapshot creates maintenance drag, portfolio ambiguity, and avoidable leak risk.

## What Changes

- Publish the existing HK strategy showcase only as a clean-room, synthetic-data, paused-maintenance public repository, with no copied Git history, provider data, credentials, private research outputs, broker adapters, or production performance claims.
- Keep the public HK demo outside the workspace submodule graph; the workspace may link to it as an external portfolio reference, but must not depend on it in CI, release matrix, or daily workflow.
- Reposition the superproject documentation around an active A-share direction, while retaining HK restore and compatibility surfaces only where they are needed for cold-storage reproducibility, historical provenance, or explicit compatibility.
- Add explicit public-demo review requirements: export manifest, offline smoke, safety scan, human grep for sensitive/provider/local-path terms, and small-file-only constraints.
- Clarify type-checking governance across the integrated repositories: Pyright is the delegated hard type gate for active subprojects, including `quant-execution-engine`; `quant-execution-engine` keeps mypy only as an advisory bake-period check until a release review removes it.
- Do not rename public asset keys, contract paths, CLI names, or historical artifact names as part of this change. In particular, `metadata/current_assets/a_share_current.json` remains the canonical A-share current contract.

## Capabilities

### New Capabilities

- `hk-public-demo-publication`: Requirements for exporting, reviewing, and linking a clean-room HK public demo repository.
- `a-share-primary-workspace-positioning`: Requirements for documenting A-share as the active workspace direction while preserving HK frozen compatibility and restore boundaries.
- `type-gate-status-governance`: Requirements for reporting Pyright hard gates and the temporary `quant-execution-engine` mypy advisory status without overstating type coverage.

### Modified Capabilities

- None. No existing `openspec/specs/` directory is present in this workspace at proposal time.

## Impact

- Affected superproject files: `README.md`, `docs/README.md`, `docs/hk-public-demo-export.md`, `docs/hk-legacy-surface-inventory.md`, `docs/data-transition-playbook.md`, `docs/quality-governance.md`, `docs/release-checklist.md`, and the top-level doctor/checklist tests that assert documented paths and delegated commands.
- Affected demo files: `demo/hk-public-demo-template-v1/README.md`, `demo/hk-public-demo-template-v1/docs/architecture.md`, optional `SECURITY.md` / `NOTICE.md`, allowlist, and `scripts/export_hk_public_demo.py` scanner/review evidence.
- Affected quality configuration: `scripts/submodule_checks.json` remains the source of truth for delegated hard type gates and `mypy_advisory`; no change should make mypy a hard gate again unless a rollback is explicitly chosen.
- No provider credentials, licensed market data, Parquet/cache/archive files, real broker adapters, real trading targets, or private research outputs may be added to the public demo.
