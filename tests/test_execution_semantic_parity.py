from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "execution_parity_cases.json"


def test_execution_parity_cases_match_across_runtime_boundaries() -> None:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert cases
    for case in cases:
        assert case["case_id"]
        assert case["semantics"]
        assert case["portfolio"] == case["execution"]


def test_execution_parity_cases_have_conservation_fields() -> None:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    for case in cases:
        values = case["portfolio"]
        if "filled_qty" in values and "unfilled_qty" in values:
            assert values["filled_qty"] + values["unfilled_qty"] == values["target_qty"]
