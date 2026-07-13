# Framework adapter release staging

> status: active
> owner: workspace
> last_verified: 2026-07-13
> source_of_truth: `framework-adapter-release.yml`

The `framework-adapters-2026-07` train is intentionally **blocked on downstream
merge**. The manifest records reviewable feature-branch candidates; it is not a
verified version combination and none of those candidates is pinned by the
superproject.

## What this train changes

- `market-data-platform` remains the data system of record and exposes a
  read-only, optional Qlib adapter over published assets.
- `alpha-research` keeps PIT, leakage, CPCV/PBO, evidence, and promotion
  authority while Qlib is an optional dataset/training/recording backend.
- `portfolio-backtester` keeps deterministic A-share replay and compares
  framework-neutral results against Qlib and LEAN reference scenarios.
- `strategy-pipeline` delegates the tuning slice to its alpha owner and emits
  deterministic contract-v2 targets. Panel loading, fundamentals enrichment,
  evaluation, grid, and linear-sweep ownership remain explicit follow-up work
  until equivalent owner APIs exist.
- `quant-execution-engine` keeps policy, approval, idempotency, the durable
  journal, and reconciliation authority while vn.py is an optional transport.

Qlib, vn.py, and LEAN runtime objects never enter a cross-repository contract.
The native path remains available and default until owner-produced parity
evidence is accepted.

## Safe merge and pin sequence

1. Review and merge each repository stack from its oldest base PR to its final
   candidate PR.
2. Preserve every feature-branch `candidate_commit` as audit history. Record the
   actual merge commit separately in `merged_commit`, change `merge_state` to
   `merged`, and set the release status to `ready_to_validate`.
3. Only then update the five submodule gitlinks to those merged commits.
4. Run `python scripts/framework_adapter_release_gate.py --strict`.
5. Generate owner evidence and build the integration envelope:

   ```bash
   python scripts/framework_adapter_evidence.py \
     --release-manifest docs/framework-adapter-release.yml \
     --alpha <backend-comparison-replay-receipt.json> \
     --backtest <backtest-differential.json> \
     --execution <execution-recovery-matrix.json> \
     --output <integration-evidence.json>
   ```

6. Store the envelope at `integration_evidence.path`, record its lowercase
   SHA-256 in the manifest, and run the release gate again. The envelope must
   bind the same `release_id` and five actual merge commits.
7. After the envelope is accepted and the native/no-framework smoke paths pass,
   change `evidence_status` to `accepted` and the release status to `verified`.
8. Record the merged, pinned, verified combination in `version-matrix.md`.

The non-strict release gate exits successfully while reporting `blocked`; this
allows review of the integration PR without weakening merge-before-pin. Strict
mode remains red until all downstream PRs are merged and pinned.

## Rollback

Before merge, close the affected draft PR and remove its candidate from a new
release train. After merge but before verification, restore the last verified
submodule combination and keep the failed evidence. Do not delete execution
journals, reset idempotency keys, or silently reinterpret an artifact schema.
