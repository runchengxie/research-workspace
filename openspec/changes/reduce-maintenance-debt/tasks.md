## 1. Static Quality Baseline

- [x] 1.1 Extend `market-data-platform/scripts/dev/quality_debt.py` with `--json` output for Ruff and Pyright coverage metrics.
- [x] 1.2 Add a checked-in quality baseline file containing current Ruff/Pyright coverage counts and configured source excludes.
- [x] 1.3 Add baseline enforcement that fails when checked-line coverage decreases, excluded-line coverage increases, or source excludes expand without a baseline update.
- [x] 1.4 Add tests for coverage calculation, JSON output shape, and exclude-regression failure behavior.
- [x] 1.5 Document the static quality commands and the baseline update workflow in project developer docs.

## 2. Debt Reports and Maintainability Metrics

- [x] 2.1 Add a non-blocking Ruff debt scan mode for full-source diagnostics using the configured base rules.
- [x] 2.2 Add a non-blocking complexity scan mode covering `C90`, `PLR0911`, `PLR0912`, `PLR0913`, and `PLR0915`.
- [x] 2.3 Add a maintainability metrics report for file length, function length, argument count, and public facade export counts.
- [x] 2.4 Add a maintainability baseline file for current outliers and enforce regression checks for new severe outliers.
- [x] 2.5 Add tests for maintainability metric extraction and baseline comparison.

## 3. Compatibility Lifecycle

- [x] 3.1 Convert the compatibility inventory into a script-checkable format or add a parser for the existing `docs/compatibility.md` table.
- [x] 3.2 Add a compatibility governance check that verifies documented entries for console script aliases, `hk_data_platform.*`, provider re-export modules, migration commands, and release presets.
- [x] 3.3 Add repo-local audit output for each compatibility item, distinguishing source usage, test usage, and documentation-only usage.
- [x] 3.4 Add or update deprecation guidance for items whose cleanup condition is already satisfied locally but still needs downstream confirmation.
- [x] 3.5 Add tests that fail when a new compatibility alias, migration command, or re-export module is introduced without lifecycle metadata.

## 4. Architecture and API Boundaries

- [x] 4.1 Add architecture checks that prevent core contract/path/registry/manifest modules from importing HK-specific pipelines, CLI modules, provider runtimes, or release workflow code.
- [x] 4.2 Add checks or tests that keep public facade exports limited to documented stable symbols or documented compatibility exceptions.
- [x] 4.3 Update tests that rely on private helpers so they import helpers from their owning module rather than through public facades.
- [x] 4.4 Identify the first low-risk modules to admit into Ruff or Pyright coverage and record the staged admission plan.

## 5. First Incremental Cleanup Pass

- [x] 5.1 Remove at least one low-risk module or narrow file group from Ruff excludes after fixing or documenting its diagnostics.
- [x] 5.2 Refactor one selected long workflow function by extracting a cohesive plan/config, fetch, transform, validate, persist, manifest, or report step.
- [x] 5.3 Add focused tests proving the refactored workflow preserves existing behavior.
- [x] 5.4 Run the standard test, Ruff, Pyright, and governance checks and update baselines only for intentional improvements or accepted debt.
