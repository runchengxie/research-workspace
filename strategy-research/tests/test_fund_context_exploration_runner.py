from __future__ import annotations

import pandas as pd

from experiments.macro_context_shadow.run_fund_context_exploration import summarize_rows


def test_summarize_rows_is_json_safe() -> None:
    result = summarize_rows(pd.DataFrame([{"sample": "2026", "n": 3, "avg_fwd20": 0.0123}]))
    assert result["groups"][0]["n"] == 3
    assert result["groups"][0]["avg_fwd20"] == 0.0123
