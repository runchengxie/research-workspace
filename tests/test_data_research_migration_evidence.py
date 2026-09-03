from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "migrations" / "strategy-pipeline-internal-migration-manifest.md"


def test_data_documentation_records_have_owner_and_runtime_evidence() -> None:
    text = MANIFEST.read_text(encoding="utf-8")
    start = text.index("```json") + len("```json")
    end = text.index("```", start)
    payload = json.loads(text[start:end])
    records = {item["source_path"]: item for item in payload["planned_documents"]}
    for source_path in (
        "docs/concepts/data-sources.md",
        "docs/concepts/pit-coverage.md",
        "docs/concepts/shared-hk-data-platform.md",
        "docs/providers.md",
        "docs/reference/outputs/platform-assets.md",
    ):
        record = records[source_path]
        assert record["status"] == "complete"
        assert record["owner_repo"] == "market-data-platform"
        assert record["test_evidence"]
