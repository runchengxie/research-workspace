# Freshness Ownership Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `alpha-research` the single canonical owner of the existing volume-based freshness score transform, remove the duplicate implementation from `portfolio-backtester` without adding a reverse dependency, and add regression coverage that keeps the boundary from drifting back.

**Architecture:** The score transform remains an alpha-domain operation. `alpha-research` exposes and tests the canonical API. `portfolio-backtester` accepts already-transformed scores and must not import `alpha-research`. If the portfolio duplicate has no source consumers, it is removed directly; if a source consumer exists, that caller is migrated upstream before deletion. No compatibility facade is retained in portfolio if it would require copied algorithm code or a `portfolio-backtester -> alpha-research` runtime dependency.

**Tech Stack:** Python 3.12, pandas, pytest, Ruff, ty, GitHub feature branches/PRs.

**Spec:** `docs/superpowers/specs/2026-08-30-cross-repo-boundary-cleanup-design.md`, especially sections 4-6 and 12-15.

## Global Constraints

- Preserve the numerical behavior of the current transform.
- Do not add `alpha-research` to `portfolio-backtester` dependencies.
- Do not place this algorithm in `research-contracts`; that package remains algorithm-free.
- Characterization tests may pass immediately because they pin existing behavior. Any new public API or boundary change follows RED -> GREEN.
- The current ChatGPT connector environment does not provide a complete checkout and repository Actions are disabled. PRs created here must distinguish scratch/structural verification from the authoritative full repository gates.
- Do not merge an implementation PR on the basis of scratch verification alone. Run the listed repository commands in a managed checkout before declaring the implementation fully verified.

---

## Task 1: Harden the canonical alpha owner API

**Repository:** `runchengxie/alpha-research`

**Files:**
- Modify: `tests/test_freshness_overlay.py`
- Modify: `src/alpha_research/__init__.py`
- Keep behavior unchanged unless a characterization test exposes an inconsistency: `src/alpha_research/freshness_overlay.py`

- [ ] **Step 1: Add characterization coverage for current score semantics**

Append focused tests that pin exact ranking, metadata, disabled behavior, output preservation, empty frames, and invalid lambda:

```python
def test_freshness_overlay_preserves_exact_rank_blend_and_metadata() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-05"] * 3),
            "signal": [3.0, 2.0, 1.0],
            "volume_sma5_ratio": [1.0, 3.0, 2.0],
            "volume_sma20_ratio": [1.0, 3.0, 2.0],
            "volume_sma60_ratio": [1.0, 3.0, 2.0],
        }
    )

    overlaid, meta = apply_freshness_overlay(
        frame,
        score_col="signal",
        cfg={"enabled": True, "name": "volume-only", "lambda": 0.05},
    )

    assert overlaid["signal_base"].tolist() == [3.0, 2.0, 1.0]
    assert overlaid["signal"].tolist() == pytest.approx(
        [
            0.95 * 1.0 + 0.05 * (1 / 3),
            0.95 * (2 / 3) + 0.05 * 1.0,
            0.95 * (1 / 3) + 0.05 * (2 / 3),
        ]
    )
    assert meta == {
        "enabled": True,
        "name": "volume-only",
        "lambda": 0.05,
        "base_score_col": "signal",
        "output_col": "signal",
        "volume_rank_cols": [
            "volume_sma5_ratio",
            "volume_sma20_ratio",
            "volume_sma60_ratio",
        ],
        "rows": 3,
        "dates": 1,
    }


def test_freshness_overlay_disabled_is_noop() -> None:
    frame = pd.DataFrame({"trade_date": pd.to_datetime(["2024-01-05"]), "signal": [1.0]})
    overlaid, meta = apply_freshness_overlay(frame, score_col="signal", cfg=None)
    pd.testing.assert_frame_equal(overlaid, frame)
    assert meta == {"enabled": False}


def test_freshness_overlay_empty_frame_reports_empty() -> None:
    frame = pd.DataFrame(columns=["trade_date", "signal"])
    overlaid, meta = apply_freshness_overlay(
        frame,
        score_col="signal",
        cfg={"enabled": True},
    )
    assert overlaid.empty
    assert meta == {"enabled": True, "status": "empty"}


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_freshness_overlay_rejects_lambda_outside_unit_interval(value: float) -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-05"]),
            "signal": [1.0],
            "volume_sma5_ratio": [1.0],
            "volume_sma20_ratio": [1.0],
            "volume_sma60_ratio": [1.0],
        }
    )
    with pytest.raises(ValueError, match="lambda must be between 0 and 1"):
        apply_freshness_overlay(
            frame,
            score_col="signal",
            cfg={"enabled": True, "lambda": value},
        )
```

These are characterization tests. They are expected to pass against current production code; their purpose is to freeze behavior before the duplicate is deleted elsewhere.

- [ ] **Step 2: Add a RED test for the stable top-level owner API**

Add:

```python
def test_freshness_overlay_is_exported_from_alpha_package() -> None:
    from alpha_research import apply_freshness_overlay as public_apply

    assert public_apply is apply_freshness_overlay
```

Run:

```bash
uv run --extra dev pytest tests/test_freshness_overlay.py -q
```

Expected RED: import fails because `alpha_research.__init__` does not currently expose `apply_freshness_overlay`.

- [ ] **Step 3: Expose the existing implementation from `alpha_research.__init__`**

Add:

```python
from .freshness_overlay import apply_freshness_overlay
```

and add `"apply_freshness_overlay"` to `__all__`.

Do not duplicate or move the implementation.

- [ ] **Step 4: Verify GREEN and package compatibility**

Run:

```bash
uv run --extra dev pytest tests/test_freshness_overlay.py tests/test_package_smoke.py -q
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit and open alpha PR A1**

Commit message:

```text
refactor: establish freshness score owner API
```

PR body must state that behavior is unchanged and this is the provider-side prerequisite for removing the portfolio duplicate.

---

## Task 2: Audit portfolio use of the duplicate before deletion

**Repository:** `runchengxie/portfolio-backtester`

**Files:**
- Inspect: `src/**/*.py`
- Inspect: `tests/**/*.py`
- Inspect: `docs/**/*.md`
- Candidate delete: `src/portfolio_backtester/freshness_overlay.py`
- Candidate replace: `tests/test_freshness_overlay.py`
- Add: `tests/test_alpha_score_ownership.py`

- [ ] **Step 1: Search the complete checkout, not GitHub's incomplete code index**

Run:

```bash
rg -n "freshness_overlay|apply_freshness_overlay|volume_rank_cols|volume_only_lambda" src tests docs
```

Classify every result as one of:

1. duplicate module definition;
2. duplicate-module test;
3. active source consumer;
4. documentation/config reference.

Do not delete the module if category 3 exists until that consumer has been migrated.

- [ ] **Step 2A: If no active source consumer exists, write the RED boundary test**

Create `tests/test_alpha_score_ownership.py`:

```python
from pathlib import Path


def test_portfolio_package_does_not_own_freshness_score_transform() -> None:
    duplicate = Path("src/portfolio_backtester/freshness_overlay.py")
    assert not duplicate.exists(), (
        "freshness score transformation is alpha-owned; portfolio-backtester "
        "must consume an already-transformed score"
    )
```

Run:

```bash
uv run --extra dev pytest tests/test_alpha_score_ownership.py -q
```

Expected RED: the duplicate file still exists.

- [ ] **Step 2B: If active source consumers exist, migrate them before writing the deletion guard**

For each active source consumer:

- identify the upstream caller that already owns/produces the score;
- move the transformation into `alpha-research`, `strategy-app`, or a research caller as appropriate;
- pass the transformed score column into the portfolio API;
- add a parity test with the old expected numeric output;
- do not add `alpha-research` to `portfolio-backtester` dependencies.

Only continue to deletion after `rg` reports no active source consumer.

- [ ] **Step 3: Delete the duplicate implementation and its duplicate behavior test**

Delete:

```text
src/portfolio_backtester/freshness_overlay.py
```

Remove `tests/test_freshness_overlay.py` once equivalent semantics are pinned in `alpha-research` and no portfolio-owned behavior remains there.

- [ ] **Step 4: Verify GREEN and dependency direction**

Run:

```bash
uv run --extra dev pytest tests/test_alpha_score_ownership.py tests/test_package_smoke.py -q
rg -n "alpha[-_]research" pyproject.toml uv.lock src tests
```

Expected:

- boundary test passes;
- package smoke passes;
- no new runtime dependency/import from `portfolio-backtester` to `alpha-research` is introduced.

Then run:

```bash
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh all
scripts/dev/run_tests.sh maintainability
```

Expected: all required repository gates exit 0, or any pre-existing baseline failure is explicitly separated from failures introduced by this PR.

- [ ] **Step 5: Commit and open portfolio PR A2**

Commit message:

```text
refactor: remove duplicate freshness score transform
```

PR body must include the exact `rg` audit result and explicitly state that no `portfolio-backtester -> alpha-research` dependency was added.

---

## Task 3: Cross-repository parity evidence

**Repositories:** `alpha-research`, `portfolio-backtester`

- [ ] **Step 1: Preserve the portfolio fixture as alpha characterization evidence**

Ensure the exact portfolio fixture from the former `tests/test_freshness_overlay.py` is represented in `alpha-research/tests/test_freshness_overlay.py`, including the explicit expected values:

```python
[
    0.95 * 1.0 + 0.05 * (1 / 3),
    0.95 * (2 / 3) + 0.05 * 1.0,
    0.95 * (1 / 3) + 0.05 * (2 / 3),
]
```

This makes the deletion auditable even after the old test file disappears.

- [ ] **Step 2: Compare provider and consumer PRs against their bases**

Run:

```bash
git diff --check
```

for each repository and inspect:

```bash
git diff <base>...HEAD -- src tests pyproject.toml
```

Expected:

- alpha PR changes only owner API exposure/tests unless a discovered defect requires a separately documented behavior change;
- portfolio PR deletes the duplicate and adds the boundary guard, plus only the consumer migrations proven necessary by the source audit.

- [ ] **Step 3: Record verification limitations honestly**

If executing through an environment without complete checkout, PR remains Draft and the body must use wording equivalent to:

```text
Targeted behavior/static checks were performed in a scratch environment. The authoritative full repository gates listed below were not executed in this connector environment and are required before Ready/Merge.
```

No claim of a passing full suite is allowed without fresh command output.

---

## Completion Criteria

- [ ] `alpha-research` has one tested public canonical `apply_freshness_overlay` entry point.
- [ ] The alpha characterization suite pins the exact legacy portfolio numerical fixture and metadata behavior.
- [ ] `portfolio-backtester` contains no second implementation of the alpha freshness score transform.
- [ ] No active portfolio source consumer imports the removed module.
- [ ] `portfolio-backtester` does not gain an `alpha-research` dependency.
- [ ] A portfolio boundary test fails if the duplicate file is reintroduced.
- [ ] Both PR descriptions contain exact verification evidence and clearly identify any unexecuted full gates.
