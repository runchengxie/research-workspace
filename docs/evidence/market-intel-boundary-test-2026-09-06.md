# `market-intel` boundary test evidence

> verified: 2026-09-06
> repository: `market-intel`
> branch: local `main`
> commit: `063994a66a5b4661179fe1f9fb67d0cb2d97d423`

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

The boundary commit was locally merged into `market-intel/main` as
`063994a66a5b4661179fe1f9fb67d0cb2d97d423`. The local merge was validated without including the
unrelated pre-existing working-tree changes. Nothing was pushed; the remote-tracking branch remains
at `c8f24a5`.

Rollback point: preserve the unrelated working-tree changes, then return the local branch to `c8f24a5`
if the local integration needs to be abandoned. The boundary work itself is one merge commit with no
remote side effects.
