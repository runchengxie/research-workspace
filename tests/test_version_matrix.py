from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "print_version_matrix.py"


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
    assert "| market-data-platform |" in completed.stdout
    assert "| cross-sectional-trees |" in completed.stdout
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
