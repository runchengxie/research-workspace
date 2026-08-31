from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from data_path_audit import classify_path, scan_data_root, write_inventory  # noqa: E402


def test_classify_path_distinguishes_canonical_and_mixed_roots() -> None:
    assert classify_path("reports") == {
        "canonical_terms": ["reports"],
        "status": "已统一",
        "action": "按报告引用和 retention 审查历史版本",
    }
    assert classify_path("strategy_outputs") == {
        "canonical_terms": ["runs", "features", "snapshots", "reports", "receipts"],
        "status": "拆分待审",
        "action": "不能整体改名，保留 latest 和兼容 symlink",
    }


def test_scan_data_root_reports_files_bytes_and_symlink_without_following_it(
    tmp_path: Path,
) -> None:
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "report.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "strategy_outputs").mkdir()
    (tmp_path / "strategy_outputs" / "run.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "current_assets").symlink_to("reports", target_is_directory=True)

    inventory = scan_data_root(tmp_path)

    by_path = {entry["path"]: entry for entry in inventory["entries"]}
    assert by_path["reports"]["file_count"] == 1
    assert by_path["reports"]["byte_count"] == 3
    assert by_path["strategy_outputs"]["status"] == "拆分待审"
    assert by_path["strategy_outputs"]["children"][0]["path"] == "strategy_outputs/run.csv"
    assert by_path["current_assets"]["object_kind"] == "symlink"
    assert by_path["current_assets"]["file_count"] == 0


def test_write_inventory_creates_parent_and_json_document(tmp_path: Path) -> None:
    output = tmp_path / "metadata" / "lifecycle" / "audit.json"
    payload = scan_data_root(tmp_path)

    write_inventory(output, payload)

    assert json.loads(output.read_text(encoding="utf-8")) == payload
