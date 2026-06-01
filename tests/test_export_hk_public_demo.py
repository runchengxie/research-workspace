from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_hk_public_demo.py"


def test_export_hk_public_demo_stages_and_verifies_offline(tmp_path: Path) -> None:
    stage = tmp_path / "hk-cross-sectional-strategy-demo"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads((stage / "export-manifest.json").read_text(encoding="utf-8"))
    assert manifest["offline_smoke"]["status"] == "passed"
    assert manifest["scan"]["status"] == "passed"
    assert manifest["public_repository"]["name"] == "hk-cross-sectional-strategy-demo"
    assert (stage / "samples" / "summary.json").is_file()
    assert (stage / "samples" / "targets.json").is_file()
    assert not (stage / ".git").exists()


def test_export_hk_public_demo_scan_rejects_private_files(tmp_path: Path) -> None:
    stage = tmp_path / "unsafe"
    stage.mkdir()
    (stage / ".env.local").write_text("ACCESS_TOKEN=private-value\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scan-only", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert {row["check"] for row in payload["issues"]} >= {
        "forbidden_path",
        "credential_assignment",
    }
