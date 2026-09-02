from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _load_minute_audit():
    research_dir = (
        Path(__file__).resolve().parents[1]
        / "strategy-research"
        / "research"
        / "experiments"
        / "next_open_to_high"
    )
    path = research_dir / "a_share_next_open_to_high_minute_audit.py"
    spec = importlib.util.spec_from_file_location("next_open_to_high_nav_test_module", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(research_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(research_dir))
    return module


def test_relative_cumulative_uses_nav_ratio_not_compounded_daily_difference() -> None:
    audit = _load_minute_audit()
    daily = pd.DataFrame(
        {
            "benchmark_return": [0.0, 0.1],
            "benchmark_exposure_matched_return": [0.0, 0.1],
            "broad_active_return": [0.1, -0.1],
            "benchmark_limit_band_matched_return": [0.0, 0.1],
            "within_band_active_return": [0.1, -0.1],
        }
    )

    result = audit._benchmark_summary(daily, pd.Series([0.1, 0.0]))

    assert result["relative_nav_vs_limit_band_matched_benchmark"] == pytest.approx(0.0)
    assert np.prod(1.0 + daily["within_band_active_return"]) - 1.0 == pytest.approx(-0.01)
