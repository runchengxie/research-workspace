"""Load the matched raw/gross baseline used by constrained robustness runs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_baseline_factor_results(
    artifacts_dir: Path,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, dict[str, pd.Series]]:
    """Load raw/gross factor returns from a previously generated full run."""
    results: dict[str, dict[str, pd.Series]] = {}
    for path in sorted(artifacts_dir.glob("factor_*_daily.csv")):
        name = path.name.removeprefix("factor_").removesuffix("_daily.csv")
        frame = pd.read_csv(path, parse_dates=["trade_date"])
        if name not in frame.columns:
            continue
        series = frame.set_index("trade_date")[name].astype(float).sort_index()
        series = series.loc[(series.index >= start_date) & (series.index <= end_date)]
        if not series.empty:
            results[name] = {"long_short": series}
    if not results:
        raise ValueError(f"No factor daily CSVs found in baseline artifacts: {artifacts_dir}")
    return results
