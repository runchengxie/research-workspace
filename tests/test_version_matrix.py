from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "print_version_matrix.py"
DOC = ROOT / "docs" / "version-matrix.md"


def test_version_matrix_current_checkout_runs() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "| workspace |" in completed.stdout
    assert "| alpha-research |" in completed.stdout
    assert "| market-data-platform |" in completed.stdout
    assert "| portfolio-backtester |" in completed.stdout
    assert "| strategy-pipeline |" in completed.stdout
    assert "| quant-execution-engine |" in completed.stdout


def test_version_matrix_source_snapshot_message(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 2
    assert "requires a git checkout with initialized submodules" in completed.stdout


def test_version_matrix_doc_does_not_pin_static_current_checkout() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "当前本地输出：" not in text
    assert "不要手工维护当前输出的静态表" in text


def test_version_matrix_records_stage3_boundary_hardening_snapshot() -> None:
    text = DOC.read_text(encoding="utf-8")

    for phrase in (
        "2026-06-28",
        "`945ce43`",
        "`f606f86`",
        "`7af023f`",
        "`7495902`",
        "`91b4e0e`",
        "`0617076`",
        "阶段 3 边界加固组合",
        "GitHub CodeQL `28325877208`",
    ):
        assert phrase in text
