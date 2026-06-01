## Context

The superproject already separates responsibilities across `market-data-platform`, `cross-sectional-trees`, and `quant-execution-engine`. Current documentation also records that HK assets have moved to cold-storage / restore workflows, while A-share work is the active baseline direction.

The remaining ambiguity is project shape: the existing HK public demo is intentionally small, but the historical HK implementation and data/research systems were much larger. Publishing old history or keeping HK as an active-looking lane would increase leak risk and maintenance cost. At the same time, deleting restore-sensitive HK compatibility code before the archived releases and consumers are fully audited would weaken reproducibility.

The type-checking question has a similar boundary issue. The delegated hard type gate has moved to Pyright across active subprojects, including `quant-execution-engine`, but `quant-execution-engine` still carries mypy as an advisory bake-period check. The implementation should describe that state precisely instead of treating "Pyright migration complete" as "mypy fully removed" or "strict typing complete".

## Goals / Non-Goals

**Goals:**

- Make the public HK repository a clean-room, paused-maintenance portfolio snapshot generated from the curated demo template.
- Make A-share data/research/execution the explicit active direction in superproject-facing documentation and release checklists.
- Preserve HK cold-storage restore and compatibility boundaries until source tags, manifests, restore drills, and downstream audits justify further removal.
- State type-checking governance accurately: Pyright is the hard gate; `quant-execution-engine` mypy is advisory during a release bake period.
- Keep the public demo independent from workspace CI, submodules, release matrix, and daily workflows.

**Non-Goals:**

- Do not publish historical HK Git history, real HK market data, provider cache, credentials, broker integrations, private research output, true performance, or real target files.
- Do not turn the HK public demo into a reusable package or a dependency of the active workspace.
- Do not remove HK restore-sensitive code in this change unless a separate audit proves it is no longer needed.
- Do not claim full strict Pyright coverage or remove `quant-execution-engine` mypy advisory before the planned release review.
- Do not rename existing public paths, commands, asset keys, or historical artifact names as part of wording cleanup.

## Decisions

1. Use clean-room export as the only publication path.

   The public repository must be produced from `scripts/export_hk_public_demo.py` and `demo/hk-public-demo-allowlist-v1.txt`, not from a filtered copy of historical Git history. This keeps publication reviewable and avoids relying on history rewriting as a safety mechanism. The rejected alternative is to make the old HK repository public after deleting obvious sensitive files; that leaves too much risk in historical commits, local paths, data artifacts, and private research traces.

2. Keep the public demo small and synthetic.

   The demo should show the engineering handoff flow: synthetic prices, ranking, summary output, and standard `targets.json`. It should not try to prove the historical HK production system by line count. The rejected alternative is to add more legacy code to look substantial; that increases maintenance and disclosure risk without improving the active A-share workspace.

3. Link the public demo as an external reference only.

   The workspace may link to the public repo from README/docs, but it must not add the repo as a submodule or include it in required checks. This preserves the intended split: active A-share workspace here, frozen HK portfolio artifact elsewhere, private/cold storage for actual reproducibility.

4. Treat HK code removal as a separate audited migration.

   HK surfaces stay classified as shared active, frozen compatibility, archived provenance, or retire-after-audit. Restore-sensitive entry points are not deleted simply because the public demo exists. The rejected alternative is a broad cleanup pass that removes HK code before checking restore releases, source tags, and consumers.

5. Keep type-gate state source-of-truth in delegated commands.

   `scripts/submodule_checks.json` remains the superproject source of truth: each active subproject `type` profile runs Pyright, while `quant-execution-engine` keeps `mypy_advisory` separate. Documentation must match this distinction and mention that current Pyright coverage is staged/basic rather than a full strict-type guarantee.

## Risks / Trade-offs

- Public demo looks too small -> Mitigation: README and architecture docs must explicitly say it is a synthetic portfolio demo extracted from a larger private research workspace, and must list what is intentionally omitted.
- Sensitive data or local paths leak into the public repo -> Mitigation: use allowlist export, safety scan, offline smoke, export manifest, small-file rules, and a human grep review before any push.
- Frozen HK surfaces continue to make the active workspace feel large -> Mitigation: classify them as compatibility/provenance, hide them from active A-share paths, and schedule separate retirement audits instead of deleting them opportunistically.
- A-share readiness is overstated -> Mitigation: keep staged baseline wording and require evidence manifests for research output, target lineage, and execution dry-run before promotion claims.
- Type migration is overstated -> Mitigation: say "Pyright hard gate migrated" and "mypy advisory remains for `quant-execution-engine`", not "mypy removed" or "full strict Pyright coverage".

## Migration Plan

1. Update the public demo template with a relationship-to-active-work section, a short security policy, synthetic-data notice/disclaimer, and any allowlist updates needed for those files.
2. Extend release/checklist documentation so publication requires export manifest, scanner pass, offline smoke, and manual grep review.
3. Update top-level workspace documentation to make A-share the active direction and HK the frozen/legacy compatibility surface.
4. Confirm quality governance documentation and delegated check profiles consistently describe Pyright hard gates and `quant-execution-engine` mypy advisory.
5. Run focused superproject tests for doctor, docs contracts, repo path references, public demo export, and delegated check manifest behavior.
6. Stage the demo to a temporary directory, inspect it manually, then let the maintainer create/push the public GitHub repository outside the workspace scripts.

Rollback is documentation-first: remove or revise the external public-demo link if publication is deferred, keep the demo template private, and leave workspace submodule pointers untouched. If a staged public tree fails scan or review, discard that staged directory and fix the template/exporter before trying again.

## Open Questions

- Should the public repository be GitHub-archived immediately after publication, or left writable as paused-maintenance until one final README/CI pass settles?
- Is MIT still the intended license for the narrow synthetic demo, or should publication wait for a license review?
- Should the `quant-execution-engine` mypy advisory removal be tracked by a later OpenSpec change tied to the next release review?
