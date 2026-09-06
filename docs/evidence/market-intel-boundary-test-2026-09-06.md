# `market-intel` boundary test evidence

> verified: 2026-09-06
> repository: `market-intel`
> branch: `feat/architecture-boundary`
> commit: `312efa2`

## Check

```bash
uv run pytest tests/test_research_artifact_boundary.py -q
```

Result: `2 passed`.

The broader consumer gate also passed:

```bash
uv run pytest -k "contract or freshness or recovery"
```

Result: `112 passed, 646 deselected`.

The test verifies that:

- Python source under `market-intel/src` does not import `quant_research`;
- the boundary documentation requires versioned file artifacts and prohibits direct business-code
  imports across the research boundary.

The commit is isolated in a `market-intel` worktree and has not been merged or pushed. The current
`market-intel` main branch remains unchanged.
