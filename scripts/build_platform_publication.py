#!/usr/bin/env python3
"""Build a research platform publication bundle from an explicit JSON spec."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from research_contracts import build_platform_publication


def _parse_datetime(value: object) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.spec.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("publication spec must be a JSON object")
    manifest = build_platform_publication(
        artifacts=payload.get("artifacts", []),
        output_root=args.output_root,
        generated_at=_parse_datetime(payload.get("generated_at")),
        producer_repository=str(payload.get("producer_repository", "")),
        producer_commit=str(payload.get("producer_commit", "")),
        run_id=str(payload.get("run_id", "")),
    )
    print(json.dumps(manifest.to_mapping(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
