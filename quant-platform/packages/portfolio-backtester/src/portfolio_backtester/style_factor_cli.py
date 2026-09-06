"""CLI for the staged synthetic style-factor backtest artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import pandas as pd

from .style_factors_backtest import build_quantile_portfolio_returns, get_rebalance_dates


def _rounded(value: object) -> float:
    return round(float(cast(float, value)), 12)


def build_artifact(input_path: Path, *, signal: str, n_quantiles: int) -> dict[str, object]:
    frame = pd.read_csv(input_path, parse_dates=["trade_date"])
    signal_column = f"factor_{signal}_z"
    if signal_column not in frame:
        raise ValueError(f"input is missing required column: {signal_column}")
    dates = get_rebalance_dates(pd.DatetimeIndex(frame["trade_date"].unique()))
    result = build_quantile_portfolio_returns(
        frame,
        frame,
        dates,
        {signal: signal_column},
        n_quantiles=n_quantiles,
        requested_quantiles=(1, n_quantiles),
        include_universe=False,
    )[signal]
    long_returns = cast(pd.Series, result["long"])
    short_returns = cast(pd.Series, result["short"])
    long_short = cast(pd.Series, result["long_short"])
    rows = [
        {
            "period_end": pd.Timestamp(date).date().isoformat(),
            "long_return": _rounded(long_returns.loc[date]),
            "short_return": _rounded(short_returns.loc[date]),
            "long_short_return": _rounded(value),
        }
        for date, value in long_short.items()
    ]
    return {
        "artifact_type": "portfolio_backtester.style_factor_backtest",
        "schema_version": 1,
        "signal": signal,
        "n_quantiles": n_quantiles,
        "observations": len(rows),
        "cumulative_return": _rounded((1.0 + long_short).prod() - 1.0),
        "returns": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--signal", required=True)
    parser.add_argument("--quantiles", type=int, default=5)
    args = parser.parse_args()
    try:
        artifact = build_artifact(args.input, signal=args.signal, n_quantiles=args.quantiles)
    except (KeyError, ValueError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
