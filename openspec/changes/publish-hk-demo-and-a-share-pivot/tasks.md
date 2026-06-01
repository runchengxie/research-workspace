## 1. Public Demo Package

- [x] 1.1 Update `demo/hk-public-demo-template-v1/README.md` so the first screen states paused maintenance, synthetic-only scope, relationship to the active A-share workspace, and intentionally omitted real data/research/execution content.
- [x] 1.2 Add short public-demo `SECURITY.md` and `NOTICE.md` or equivalent README sections covering no real credentials, no live-trading support, synthetic data only, and no investment advice.
- [x] 1.3 Update `demo/hk-public-demo-allowlist-v1.txt` and export config if new public-demo files are added.
- [x] 1.4 Confirm `scripts/export_hk_public_demo.py` blocks forbidden paths, archive/data suffixes, oversized files, credential-like assignments, and local absolute paths for the updated template.
- [x] 1.5 Stage a fresh demo export to `/tmp`, verify `export-manifest.json` records `scan=passed` and `offline_smoke=passed`, and run `--scan-only` against the staged tree.

## 2. Workspace Positioning

- [x] 2.1 Update `README.md` and `docs/README.md` to present A-share data/research/execution as the active workspace direction and the HK public demo as an external paused-maintenance portfolio reference.
- [x] 2.2 Update `docs/hk-public-demo-export.md` with the publication review checklist, manual grep terms, and explicit "not a submodule / not required CI" boundary.
- [x] 2.3 Update `docs/data-transition-playbook.md` and `docs/hk-legacy-surface-inventory.md` only where needed to keep HK restore-sensitive surfaces classified as frozen compatibility, archived provenance, shared active, or retire-after-audit.
- [x] 2.4 Update `docs/release-checklist.md` so public-demo publication requires export manifest, scanner pass, offline smoke, human sensitive-term review, and maintainer-controlled GitHub push.
- [x] 2.5 Ensure all touched documentation uses `metadata/current_assets/a_share_current.json` as the canonical A-share current contract and treats `cn_current.json` only as a historical alias when mentioned.

## 3. Type Gate Governance

- [x] 3.1 Verify `scripts/submodule_checks.json` keeps Pyright as the `type` hard gate for `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine`.
- [x] 3.2 Verify `quant-execution-engine` keeps `mypy_advisory` separate from `full` and that no docs describe mypy as fully removed.
- [x] 3.3 Update `docs/quality-governance.md`, `docs/workspace-maintenance.md`, and `quant-execution-engine/docs/testing.md` only if their wording drifts from "Pyright hard gate complete; qexec mypy advisory remains for bake period".
- [x] 3.4 Add or update focused tests that assert delegated `type` profiles use Pyright and `quant-execution-engine` `full` does not include `mypy_advisory`.

## 4. Validation

- [x] 4.1 Run focused superproject tests for docs contracts, repo path references, public demo export behavior, delegated submodule checks, and workspace doctor.
- [x] 4.2 Run a final manual grep over the staged public demo for `token`, `secret`, `password`, `api_key`, `access_key`, `rqdata`, `tushare`, `longport`, `ibkr`, `alpaca`, `/home/`, `Users/`, `parquet`, `pickle`, `zst`, `tar`, and `zip`.
- [x] 4.3 Inspect `git status --short` and confirm no submodule gitlink, provider cache, market data, research output, trading audit, `.env*`, `artifacts/`, `outputs/`, or generated public-demo staging directory is tracked.
- [x] 4.4 Record final implementation evidence in the handoff summary in data platform -> strategy research -> trading execution -> top-level docs/doctor -> remaining limitations order.
