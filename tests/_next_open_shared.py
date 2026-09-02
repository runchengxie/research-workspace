"""Shared helpers for next_open_to_high research tests.

Extracted from ``test_next_open_to_high_research.py`` to keep individual test
modules under the maintainability large-file budget (M1). Both
``test_next_open_to_high_research.py`` and its part2 split import from here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "strategy-research" / "research" / "experiments" / "next_open_to_high"


def _load_research_module(filename: str, module_name: str):
    module_path = RESEARCH_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(RESEARCH_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(RESEARCH_DIR))
    return module


BACKTEST = _load_research_module(
    "a_share_next_open_to_high_backtest.py",
    "a_share_next_open_to_high_backtest_for_tests",
)
MINUTE_AUDIT = _load_research_module(
    "a_share_next_open_to_high_minute_audit.py",
    "a_share_next_open_to_high_minute_audit_for_tests",
)


def _session_times(date: str) -> pd.DatetimeIndex:
    day = pd.Timestamp(date)
    morning = pd.date_range(day + pd.Timedelta(hours=9, minutes=30), periods=121, freq="min")
    afternoon = pd.date_range(day + pd.Timedelta(hours=13, minutes=1), periods=120, freq="min")
    return pd.DatetimeIndex(morning.append(afternoon))


def _flat_session_bars(date: str = "2026-01-06") -> pd.DataFrame:
    times = _session_times(date)
    return pd.DataFrame(
        {
            "trade_time": times,
            "open": [10.0] * len(times),
            "high": [10.1] * len(times),
            "low": [9.9] * len(times),
            "close": [10.0] * len(times),
            "amount": [100.0] * len(times),
        }
    )


def _minute_candidate(**overrides: object) -> pd.Series:
    values: dict[str, Any] = {
        "signal_date": pd.Timestamp("2026-01-05"),
        "entry_date": pd.Timestamp("2026-01-06"),
        "symbol": "000001.SZ",
        "execution_eligible": True,
        "exec_next_up_limit": 11.0,
        "exec_next_down_limit": 9.0,
    }
    values.update(overrides)
    return pd.Series(values)
