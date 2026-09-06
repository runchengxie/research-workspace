from __future__ import annotations

import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).parents[1] / "scripts" / "compare_runtime_shadow.py"
_SPEC = importlib.util.spec_from_file_location("compare_runtime_shadow", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
compare_artifacts = _MODULE.compare_artifacts


def _payload(weight: float = 0.5) -> dict:
    return {
        "schema_version": "strategy_app.cashflow.selection.v1",
        "strategy_id": "cashflow_quality_top50_v1",
        "policy_id": "cashflow_quality_top50_v1.quarterly_fcf_cap10.v1",
        "policy": {"top_n": 50, "max_weight": 0.1},
        "source_date": "20260820",
        "signal_date": "20260821",
        "research_only": True,
        "eligible_for_live": False,
        "targets": [{"symbol": "000001.SZ", "target_weight": weight}],
    }


def test_runtime_comparison_normalizes_target_order() -> None:
    old = _payload()
    new = _payload()
    old["targets"] = [
        {"symbol": "000002.SZ", "target_weight": 0.5},
        {"symbol": "000001.SZ", "target_weight": 0.5},
    ]
    new["targets"] = list(reversed(old["targets"]))
    assert compare_artifacts(old, new)["status"] == "match"


def test_runtime_comparison_rejects_symbol_or_weight_drift() -> None:
    report = compare_artifacts(_payload(), _payload(0.6))
    assert report["status"] == "mismatch"
    assert "weights" in report["differences"]
