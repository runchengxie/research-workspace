from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.research_contracts import (
    build_file_receipts,
    file_receipt_payload,
    validate_file_receipts,
)


def test_file_receipts_bind_inventory_and_content(tmp_path: Path) -> None:
    artifact = tmp_path / "summary.json"
    artifact.write_text('{"ok": true}\n', encoding="utf-8")
    payload = file_receipt_payload(build_file_receipts(tmp_path, [artifact]))

    receipts = validate_file_receipts(tmp_path, payload, required_files=("summary.json",))

    assert receipts[0].path == "summary.json"
    assert len(receipts[0].sha256) == 64


def test_file_receipts_reject_mutated_content(tmp_path: Path) -> None:
    artifact = tmp_path / "summary.json"
    artifact.write_text('{"ok": true}\n', encoding="utf-8")
    payload = file_receipt_payload(build_file_receipts(tmp_path, [artifact]))
    artifact.write_text('{"ok": false}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="file (size|SHA-256) mismatch"):
        validate_file_receipts(tmp_path, payload)


def test_file_receipts_payload_is_json_serializable(tmp_path: Path) -> None:
    artifact = tmp_path / "summary.json"
    artifact.write_text("{}\n", encoding="utf-8")

    json.dumps(file_receipt_payload(build_file_receipts(tmp_path, [artifact])))
