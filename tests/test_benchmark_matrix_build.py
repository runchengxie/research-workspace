from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "benchmark_matrix_build.py"
GATE_SCRIPT = ROOT / "scripts" / "strategy_evidence_gate.py"

build_spec = importlib.util.spec_from_file_location("benchmark_matrix_build", BUILD_SCRIPT)
assert build_spec is not None and build_spec.loader is not None
build = importlib.util.module_from_spec(build_spec)
sys.modules[build_spec.name] = build
build_spec.loader.exec_module(build)

gate_spec = importlib.util.spec_from_file_location("strategy_evidence_gate", GATE_SCRIPT)
assert gate_spec is not None and gate_spec.loader is not None
gate = importlib.util.module_from_spec(gate_spec)
sys.modules[gate_spec.name] = gate
gate_spec.loader.exec_module(gate)


def _rows(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "rows.json"
    path.write_text(
        json.dumps({"schema_version": "benchmark_rows.v1", "rows": rows}),
        encoding="utf-8",
    )
    return path


def _two_axis_rows() -> list[dict[str, object]]:
    return [
        {"universe": "csi300", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 0.7},
        {"universe": "csi500", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 1.1},
        {"universe": "csi500", "horizon": "h20", "regime": "bear", "cost_bps": 50, "sharpe": -0.2},
    ]


def test_build_creates_gate_compatible_matrix(tmp_path: Path) -> None:
    path = _rows(tmp_path, _two_axis_rows())
    assert build.main(["--input", str(path)]) == 0

    built = build._matrix_from_rows(
        {"schema_version": "benchmark_rows.v1", "rows": _two_axis_rows()},
        "sharpe",
    )
    assert built["schema_version"] == "benchmark_matrix.v1"
    assert built["axes"] == ["universe", "horizon", "regime", "cost_bps"]
    assert len(built["cells"]) == 3
    assert gate._validate_benchmark_cells(built) == (True, "")


def test_check_rejects_single_point_and_single_axis(tmp_path: Path) -> None:
    single_point = _two_axis_rows()[:1]
    path = _rows(tmp_path, single_point)
    assert build.main(["--input", str(path), "--check"]) == 1

    one_axis = _two_axis_rows()[:2]
    path = _rows(tmp_path, one_axis)
    assert build.main(["--input", str(path), "--check"]) == 1

    full = _rows(tmp_path, _two_axis_rows())
    assert build.main(["--input", str(full), "--check"]) == 0


def test_missing_axis_or_metric_is_rejected(tmp_path: Path) -> None:
    rows = _two_axis_rows()
    del rows[0]["horizon"]
    assert build.main(["--input", str(_rows(tmp_path, rows))]) == 1

    rows = _two_axis_rows()
    del rows[0]["sharpe"]
    assert build.main(["--input", str(_rows(tmp_path, rows))]) == 1


def test_duplicate_and_empty_rows_are_rejected(tmp_path: Path) -> None:
    duplicate = [_two_axis_rows()[0], _two_axis_rows()[0]]
    assert build.main(["--input", str(_rows(tmp_path, duplicate))]) == 1

    assert build.main(["--input", str(_rows(tmp_path, []))]) == 1


def test_wrong_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "rows.json"
    path.write_text(
        json.dumps({"schema_version": "old.v1", "rows": _two_axis_rows()}),
        encoding="utf-8",
    )
    assert build.main(["--input", str(path)]) == 1


def test_output_writes_matrix_and_custom_metric(tmp_path: Path) -> None:
    rows = [
        {"universe": "csi300", "horizon": "h5", "regime": "bull", "cost_bps": 20, "ic": 0.02},
        {"universe": "csi500", "horizon": "h5", "regime": "bull", "cost_bps": 20, "ic": 0.05},
        {"universe": "csi500", "horizon": "h20", "regime": "bear", "cost_bps": 50, "ic": -0.01},
    ]
    path = _rows(tmp_path, rows)
    output = tmp_path / "matrix.json"
    assert build.main(["--input", str(path), "--output", str(output), "--metric", "ic"]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["metric"] == "ic"
    assert payload["cells"][0]["ic"] == 0.02
    assert "sharpe" not in payload["cells"][0]


def test_missing_input_file_fails(tmp_path: Path) -> None:
    assert build.main(["--input", str(tmp_path / "nope.json")]) == 1
