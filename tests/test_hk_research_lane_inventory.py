from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import hk_research_lane_inventory  # noqa: E402


def test_hk_research_lane_inventory_keeps_data_and_execution_boundaries() -> None:
    inventory = hk_research_lane_inventory.load_inventory()

    report = hk_research_lane_inventory.validate_inventory(inventory)

    assert report["status"] == "passed"
    records = {row["id"]: row for row in inventory["records"]}
    assert records["market-data-platform-hk-assets-control-plane"]["action"] == "keep"
    assert records["qexec-shared-market-execution"]["action"] == "keep"
    assert records["cstree-hk-allocation-liveops"]["action"] == "move"
    assert records["cstree-hk-allocation-liveops"]["deletion_gate"]["status"] == "blocked"


def test_hk_research_lane_template_scan_rejects_runtime_artifacts(tmp_path: Path) -> None:
    template = tmp_path / "template"
    template.mkdir()
    (template / "README.md").write_text("safe\n", encoding="utf-8")
    (template / "data.parquet").write_text("runtime data\n", encoding="utf-8")

    scan = hk_research_lane_inventory.scan_template(template)

    assert scan["status"] == "failed"
    assert {"path": "data.parquet", "check": "runtime_or_archive_suffix"} in scan["issues"]


def test_hk_research_lane_inventory_cli_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "hk_research_lane_inventory.py"),
            "--check",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "passed"
    assert payload["policy"]["primary_lane"] == "A 股"
