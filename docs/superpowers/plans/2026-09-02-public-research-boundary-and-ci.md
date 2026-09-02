# Public Research Boundary and CI Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public/private repository policy consistent, prepare `alpha-research` and the public portion of `strategy-research` for independent GitHub Actions checks, and keep production data operations and private strategy assets out of public repositories.

**Architecture:** Keep `market-data-platform` and `strategy-pipeline` private. Make `alpha-research` public-ready by removing its mandatory private data-platform installation path from the public test surface. Keep reusable research infrastructure in `strategy-research` and move personal strategy assets into a separate private repository only after an explicit file manifest and consumer audit. Public CI must run without private credentials or real data.

**Tech Stack:** GitHub repository visibility, Git submodules, Python, `uv`, pytest, Ruff, `ty`, Markdown, GitHub Actions.

**Spec:** `docs/quality-governance.md`, each repository's `AGENTS.md`, and the file-level classification recorded during this audit.

## Global Constraints

- Public repositories default to enabled GitHub Actions.
- Private repositories default to disabled GitHub Actions.
- Private repository exceptions must document reason, scope, and resource cost.
- Public CI must not require private repository credentials, real data assets, or production paths.
- Do not move or delete the concurrent uncommitted change in `strategy-research/research/experiments/long_term_fundamental_v2/run_quarterly_research.py`.
- Do not change repository visibility until the public-readiness checks pass.

### Task 1: Align repository documentation with the CI policy

**Files:**
- Modify: root `AGENTS.md`, `README.md`, and `docs/quality-governance.md`
- Modify: each repository `AGENTS.md`, README, or quality/testing document where the policy is missing
- Test: existing documentation and policy tests in each repository

- [ ] Add the same three-rule policy to every active repository's maintainer documentation.
- [ ] Record the current visibility and current workflow status separately.
- [ ] Replace stale root statements claiming that all Actions are disabled.
- [ ] Add a repository visibility matrix with the five private repositories and their documented reason for remaining private.
- [ ] Run each repository's documentation and policy tests.
- [ ] Commit policy documentation separately from code changes.

### Task 2: Finalize the `alpha-research` public boundary

**Files:**
- Modify: `alpha-research/pyproject.toml`, dependency source configuration, and CI/test entrypoints
- Test: `alpha-research/tests` and public-install smoke test

- [ ] Identify imports that require `market-data-platform` at runtime.
- [ ] Move provider-specific functionality behind an optional extra or a narrow adapter boundary.
- [ ] Make the default public test and lint profile installable without private repositories.
- [ ] Keep fixture-based tests deterministic and offline.
- [ ] Resolve or explicitly scope the existing `ty` diagnostics before enabling public CI.
- [ ] Run locked install, Ruff, format, `ty`, pytest, and dependency audit in a clean public-style environment.

### Task 3: Freeze the `strategy-research` public/private file manifest

**Files:**
- Create: a file-level public/private manifest in the private research boundary documentation
- Review: `research/experiments/**`, `research/cases/**`, `research/evidence/**`, `research/ledgers/**`, `src/**`, `tests/**`, `tools/**`, and `docs/**`
- Test: path and import-boundary tests

- [ ] Mark reusable framework code, schemas, tests, and sanitized specifications as public.
- [ ] Mark personal strategy logic, judgments, evidence, results, and production-adjacent scripts as private candidates.
- [ ] Search public candidates for credentials, absolute local paths, real data identifiers, and private dependency pins.
- [ ] Audit consumers before moving any file.
- [ ] Create `strategy-research-private` only if the private manifest contains a stable, non-trivial asset set.
- [ ] Keep public code independent from the private repository.

### Task 4: Clean public CI and path dependencies

**Files:**
- Modify: public repository workflow files
- Modify: public-facing package dependency declarations and path defaults
- Test: CI workflow syntax, clean checkout install, and offline test suite

- [ ] Enable lightweight PR CI for public repositories only after their clean-checkout tests pass.
- [ ] Keep private repositories without workflows unless an exception is documented.
- [ ] Replace personal absolute paths with environment variables or fixture-relative defaults.
- [ ] Ensure no workflow accesses private repositories or secrets on fork pull requests.

### Task 5: Change visibility and verify remote behavior

**Files:**
- Repository settings for `alpha-research` and, if Task 3 passes, `strategy-research`
- Modify: root submodule pins and CI policy matrix

- [ ] Change visibility only after all public-readiness checks pass.
- [ ] Confirm public Actions workflows run successfully on the default branch.
- [ ] Confirm root submodule pins resolve from public repositories.
- [ ] Run the root workspace contract checks and record remaining unrelated failures.
- [ ] Update the final visibility matrix and document any deferred repository.
