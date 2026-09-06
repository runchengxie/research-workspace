from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from portfolio_backtester.style_factors_backtest import (
    build_quantile_portfolio_returns,
    get_rebalance_dates,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic-style-factor.csv"


def test_quantile_backtest_keeps_the_portfolio_backtester_namespace() -> None:
    frame = pd.read_csv(EXAMPLE, parse_dates=["trade_date"])
    dates = get_rebalance_dates(pd.DatetimeIndex(frame["trade_date"].unique()))

    result = build_quantile_portfolio_returns(
        frame,
        frame,
        dates,
        {"size": "factor_size_z"},
        n_quantiles=2,
        include_universe=False,
    )

    long_short = result["size"]["long_short"]
    assert long_short.index.tolist() == [pd.Timestamp("2026-02-02")]
    assert long_short.tolist() == pytest.approx([0.02])


def test_cli_writes_the_versioned_style_factor_artifact(tmp_path: Path) -> None:
    output = tmp_path / "style-factor-report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "portfolio_backtester.style_factor_cli",
            "--input",
            str(EXAMPLE),
            "--output",
            str(output),
            "--signal",
            "size",
            "--quantiles",
            "2",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {
        "artifact_type": "portfolio_backtester.style_factor_backtest",
        "schema_version": 1,
        "signal": "size",
        "n_quantiles": 2,
        "observations": 1,
        "cumulative_return": 0.02,
        "returns": [
            {
                "period_end": "2026-02-02",
                "long_return": 0.01,
                "short_return": -0.01,
                "long_short_return": 0.02,
            }
        ],
    }


def test_cli_rejects_input_without_the_requested_signal(tmp_path: Path) -> None:
    output = tmp_path / "style-factor-report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "portfolio_backtester.style_factor_cli",
            "--input",
            str(EXAMPLE),
            "--output",
            str(output),
            "--signal",
            "missing",
            "--quantiles",
            "2",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "factor_missing_z" in completed.stderr
    assert not output.exists()
