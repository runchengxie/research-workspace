"""Summary helpers for the margin-qualification short-leg sensitivity."""

from __future__ import annotations

import pandas as pd

from .factor_backtest import compute_summary


def margin_comparison_frame(
    net_results: dict[str, dict[str, pd.Series]],
    margin_results: dict[str, dict[str, pd.Series]],
) -> pd.DataFrame:
    """Compare ordinary and margin-qualified theoretical shorts on common dates."""
    profiles: dict[str, dict[str, dict[str, pd.Series]]] = {
        "constrained_net_matched_2015plus": {},
        "margin_qualification_upper_bound_net": {},
    }
    for factor, margin_result in margin_results.items():
        if factor not in net_results:
            continue
        regular = net_results[factor]["long_short"]
        qualified = margin_result["long_short"]
        common = regular.index.intersection(qualified.index)
        if common.empty:
            continue
        profiles["constrained_net_matched_2015plus"][factor] = {"long_short": regular.loc[common]}
        profiles["margin_qualification_upper_bound_net"][factor] = {
            "long_short": qualified.loc[common]
        }
    rows = []
    for profile, results in profiles.items():
        summary = compute_summary(results)
        summary.insert(1, "profile", profile)
        rows.append(summary)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
