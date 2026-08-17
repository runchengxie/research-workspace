from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from research_contracts import (
    ArtifactEnvelopeV2,
    read_artifact_envelope,
    validate_file_receipts,
)

from style_factors.style_factor_attribution import (
    REQUIRED_STYLE_FILES,
    STYLE_ARTIFACT_SCHEMA_VERSION,
    _validate_out_name,
    _validate_required_style_files,
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
    envelope = cast(
        ArtifactEnvelopeV2,
        read_artifact_envelope(payload, allow_legacy=False),
    )
    assert envelope.artifact_id == ("style-factors:test-run")
    receipts = validate_file_receipts(
        tmp_path,
        payload["file_receipts"],
        required_files=REQUIRED_STYLE_FILES,
    )
    assert len(receipts) == len(REQUIRED_STYLE_FILES)


def test_style_publish_rejects_unsafe_output_names() -> None:
    for value in ("", ".", "..", "../escape", "nested/name", "nested\\name"):
        try:
            _validate_out_name(value)
        except ValueError:
            continue
        raise AssertionError(f"unsafe output name accepted: {value!r}")

    assert _validate_out_name("20260801-full") == "20260801-full"


def test_style_publish_requires_complete_source_artifacts(tmp_path: Path) -> None:
    (tmp_path / "meta.json").write_text("{}\n", encoding="utf-8")

    try:
        _validate_required_style_files(tmp_path)
    except ValueError as exc:
        assert "factor_summary.json" in str(exc)
    else:
        raise AssertionError("incomplete source artifacts were accepted")


def test_copied_artifacts_manifest_records_source_provenance(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for name in REQUIRED_STYLE_FILES:
        content = '{"quick": false}\n' if name == "meta.json" else f"{name}\n"
        (source / name).write_text(content, encoding="utf-8")
        (output / name).write_text(content, encoding="utf-8")

    _write_publish_manifest(
        outdir=output,
        out_name="copied-run",
        data_root=tmp_path,
        strategy_csv=None,
        strategy_name="strategy",
        quick=False,
        source_artifacts=source,
    )

    payload = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert payload["publish_mode"] == "copied_artifacts"
    assert payload["source_artifacts"]["meta_sha256"]
