# Thin integration-layer check evidence

> status: staging-only
> verified: 2026-09-06

The workspace now has an executable guard for its target role as an integration
layer. `scripts/doctor_integration_checks.py`, invoked by
`scripts/workspace_doctor.py`, verifies that:

- the target architecture, naming, boundary, ownership, and version-manifest
  documents exist;
- the target manifest contains `quant-platform` and `quant-research` staging
  targets;
- root `src/` contains only the shared `research_contracts` package and no
  strategy, portfolio, provider, or runtime owner package.

The architecture model also records `target_repository` mappings for every
legacy component, including:

- `research-contracts` → `quant-platform/contracts`
- `alpha-research` → `quant-platform/alpha`
- `strategy-research` → `quant-research/registry`
- `strategy-app` → `quant-research/strategies`
- `strategy-pipeline` → `quant-platform/orchestration`

Verification:

```bash
PYTHONPATH=scripts:src uv run pytest -q tests/test_workspace_doctor.py
# 23 passed
uv run pytest -q tests/test_workspace_architecture.py
# 7 passed
PYTHONPATH=scripts:src uv run python scripts/workspace_doctor.py
# errors=0 warnings=5
PYTHONPATH=scripts:src uv run python scripts/workspace_architecture.py --check
# errors=0 warnings=11
```

The warnings are existing submodule freshness, local-hook, CLI, and standalone
pin differences; they do not represent root business-code ownership.
