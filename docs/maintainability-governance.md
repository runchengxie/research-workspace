# Maintainability Governance

This page collects the active governance surfaces for maintainability debt. It
does not replace submodule-specific rules; each submodule still owns its code,
docs, tests, and runtime behavior.

## Registers

| Area | Source of truth |
| --- | --- |
| Deprecated compatibility entrypoints | [deprecations.md](deprecations.md), [deprecations.yml](deprecations.yml) |
| Script lifecycle and safety | [script-lifecycle.yml](script-lifecycle.yml) |
| Quality coverage and excludes | [quality-coverage-governance.yml](quality-coverage-governance.yml) |
| Large-file and refactor roadmap | [maintainability-refactor-roadmap.yml](maintainability-refactor-roadmap.yml) |
| Generated maintainability baseline | [evidence/maintainability/baseline-20260602.json](evidence/maintainability/baseline-20260602.json) |
| HK archive routing | [archive/hk/README.md](archive/hk/README.md) |
| HK public split boundary | [hk-public-split-manifest.yml](hk-public-split-manifest.yml) |
| HK private legacy archive gate | [hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) |

## Baseline Command

```bash
python scripts/maintainability_baseline.py --out docs/evidence/maintainability/baseline-20260602.json
```

The report uses stdlib AST parsing and records Python LOC, HK-related file
counts, large files, long functions, approximate complexity hotspots, quality
configuration, and script inventory.

## Policy

- New deprecated surfaces need an owner, replacement, removal condition, rollback
  path, and focused tests.
- New non-trivial scripts need lifecycle metadata before they are used by release
  or migration workflows.
- New broad Ruff/Pyright/mypy excludes need owner, reason, review milestone, and
  next include target.
- Large files and long functions should enter the roadmap before broad rewrites.
- Actual deletion of restore-sensitive HK compatibility code requires a follow-up
  change and evidence from the owning repository.
