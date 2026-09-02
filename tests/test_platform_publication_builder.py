from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from research_contracts import build_platform_publication


def test_builder_copies_projection_and_writes_manifest_without_source_path(tmp_path: Path) -> None:
    source = tmp_path / "source-evidence.json"
    source.write_text('{"status":"pass"}', encoding="utf-8")
    output = tmp_path / "bundle"

    manifest = build_platform_publication(
        artifacts=[
            {
                "source_path": source,
                "artifact_id": "strategy.evidence",
                "relative_path": "strategies/evidence.json",
                "schema_version": "strategy.evidence.v1",
                "media_type": "application/json",
                "audience": "public",
                "consumers": ["trading-research-dashboard", "market-intel"],
            }
        ],
        output_root=output,
        generated_at=datetime(2026, 9, 2, 5, 20, tzinfo=timezone.utc),
        producer_repository="runchengxie/research-workspace",
        producer_commit="abc123",
        run_id="run-1",
    )

    payload = json.loads((output / "platform-publication.json").read_text(encoding="utf-8"))
    assert manifest.artifacts[0].sha256 == payload["artifacts"][0]["sha256"]
    assert "source_path" not in payload["artifacts"][0]
    assert (output / "strategies" / "evidence.json").read_text(encoding="utf-8") == (
        '{"status":"pass"}'
    )


def test_builder_replaces_previous_bundle_without_stale_projection(tmp_path: Path) -> None:
    source = tmp_path / "evidence.json"
    source.write_text("{}", encoding="utf-8")
    output = tmp_path / "bundle"
    stale = output / "old" / "stale.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    build_platform_publication(
        artifacts=[
            {
                "source_path": source,
                "artifact_id": "strategy.evidence",
                "relative_path": "strategies/evidence.json",
                "schema_version": "strategy.evidence.v1",
                "media_type": "application/json",
                "audience": "public",
                "consumers": ["trading-research-dashboard"],
            }
        ],
        output_root=output,
        generated_at=datetime(2026, 9, 2, 5, 20, tzinfo=timezone.utc),
        producer_repository="runchengxie/research-workspace",
        producer_commit="abc123",
        run_id="run-2",
    )

    assert not stale.exists()
