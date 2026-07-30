from __future__ import annotations

import json
from pathlib import Path

from src.research_contracts import read_artifact_envelope, validate_file_receipts
from src.style_factors.style_factor_attribution import (
    REQUIRED_STYLE_FILES,
    STYLE_ARTIFACT_SCHEMA_VERSION,
    _write_publish_manifest,
)


def test_style_publish_manifest_uses_shared_receipts(tmp_path: Path) -> None:
    for name in REQUIRED_STYLE_FILES:
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")

    _write_publish_manifest(
        outdir=tmp_path,
        out_name="test-run",
        data_root=tmp_path,
        strategy_csv=None,
        strategy_name="strategy",
        quick=True,
    )

    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == STYLE_ARTIFACT_SCHEMA_VERSION
    assert read_artifact_envelope(payload, allow_legacy=False).artifact_id == (
        "style-factors:test-run"
    )
    receipts = validate_file_receipts(
        tmp_path,
        payload["file_receipts"],
        required_files=REQUIRED_STYLE_FILES,
    )
    assert len(receipts) == len(REQUIRED_STYLE_FILES)
