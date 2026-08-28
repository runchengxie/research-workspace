# Plan: integrate deep-learning as an independent research satellite

## Goal

Register `deep-learning-tick-data-prediction` in `research-workspace` as an independently released Git submodule, while defining a stable artifact handoff to `alpha-research` and `portfolio-backtester`. Keep L2 data, checkpoints, experiment outputs, and repository-specific implementation outside the superproject.

## Tasks

1. Register the deep-learning repository as a Git submodule.
   - Update `.gitmodules` with the public HTTPS repository URL.
   - Pin the submodule to the already pushed upstream `main` commit.
   - Keep the superproject free of copied source code, data, checkpoints, and generated outputs.

2. Add delegated quality checks for the new submodule.
   - Add smoke, lint, test, type, release-typecheck, and full profiles to `scripts/submodule_checks.json`.
   - Extend the manifest tests and submodule-list tests so the registration cannot silently drift.

3. Document the integration boundary.
   - Describe deep-learning as the L2 event-stream audit and model-producing satellite.
   - Define the handoff as versioned prediction artifacts, with `alpha-research` owning alpha evidence and `portfolio-backtester` owning portfolio/execution semantics.
   - Record that the native event-level simulator remains the correctness oracle until differential parity is demonstrated.

4. Validate the federated setup.
   - Run root tests covering the Git submodule and delegated-check manifest.
   - Run the new submodule smoke check and workspace doctor.
   - Inspect the final diff and submodule status before reporting the result.
