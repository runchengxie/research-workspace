# Documentation supersession matrix

> status: active
> owner: workspace
> last_verified: 2026-09-06

The combined target repositories currently have 627 Markdown files and 49,674
physical Markdown lines. The checked-out workspace has 772 Markdown files and
70,652 lines. The difference is an ownership and migration gap, not a reason
to duplicate every page in both targets.

| Documentation category | Owner | Action | Status |
| --- | --- | --- | --- |
| Public data, alpha, backtest, orchestration, execution, and microstructure implementation | `quant-platform` | Move active implementation guidance to the owning package and retain one index entry | `DOCUMENTATION_RELOCATE` |
| Strategy identity, lifecycle, experiments, model choices, evidence, and private research | `quant-research` | Move active private research guidance and preserve evidence provenance | `DOCUMENTATION_RELOCATE` |
| Version matrix, submodule composition, cross-repository contracts, doctor, release governance | `research-workspace` | Retain as the thin integration layer | `RETAIN_IN_WORKSPACE` |
| ADRs and dated evidence | Original owner or workspace archive | Preserve historical context; do not rewrite as current guidance | `HISTORICAL_ARCHIVE` |
| Current cashflow research and readiness documents | `quant-research` unless they describe cross-repo release or market-intel delivery | Verify against current source and target revisions | `REVIEW_REQUIRED` |
| Public/private boundary and migration manifests | Workspace plus target migration directories | Keep machine-readable ownership and parity evidence synchronized | `REVIEW_REQUIRED` |

Moved active pages must leave a short compatibility pointer with
`status: superseded` and `superseded_by`. Historical evidence, ADRs, and
archived research records remain in their original historical form.
