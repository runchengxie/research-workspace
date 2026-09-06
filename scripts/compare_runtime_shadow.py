#!/usr/bin/env python3
"""Compare two cashflow shadow publications without depending on local source paths."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

WEIGHT_TOLERANCE = Decimal("1e-12")


def _targets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    targets = payload.get("targets")
    if not isinstance(targets, list):
        return []
    return sorted(
        (item for item in targets if isinstance(item, dict)),
        key=lambda item: str(item.get("symbol", "")),
    )


def _core(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload.get(key)
        for key in (
            "schema_version",
            "strategy_id",
            "policy_id",
            "policy",
            "source_date",
            "signal_date",
            "research_only",
            "eligible_for_live",
        )
    }


def compare_artifacts(old_payload: dict[str, Any], new_payload: dict[str, Any]) -> dict[str, Any]:
    """Return a machine-readable parity report for two selection payloads."""
    differences: dict[str, Any] = {}
    old_core, new_core = _core(old_payload), _core(new_payload)
    for key in old_core:
        if old_core[key] != new_core[key]:
            differences[key] = {"old": old_core[key], "new": new_core[key]}

    old_targets, new_targets = _targets(old_payload), _targets(new_payload)
    old_symbols = [item.get("symbol") for item in old_targets]
    new_symbols = [item.get("symbol") for item in new_targets]
    if old_symbols != new_symbols:
        differences["symbols"] = {"old": old_symbols, "new": new_symbols}
    else:
        weight_drift = []
        for old, new in zip(old_targets, new_targets, strict=True):
            old_weight = Decimal(str(old.get("target_weight")))
            new_weight = Decimal(str(new.get("target_weight")))
            if abs(old_weight - new_weight) > WEIGHT_TOLERANCE:
                weight_drift.append(
                    {
                        "symbol": old.get("symbol"),
                        "old": str(old_weight),
                        "new": str(new_weight),
                    }
                )
        if weight_drift:
            differences["weights"] = weight_drift

    return {
        "schema_version": "quant.runtime_shadow_comparison.v1",
        "status": "match" if not differences else "mismatch",
        "differences": differences,
        "old": {
            "target_count": len(old_targets),
            "publication_sha256": old_payload.get("publication_sha256"),
            "producer_repository": old_payload.get("producer_repository"),
            "producer_commit": old_payload.get("producer_commit"),
            "platform_repository": old_payload.get("platform_repository"),
            "platform_commit": old_payload.get("platform_commit"),
        },
        "new": {
            "target_count": len(new_targets),
            "publication_sha256": new_payload.get("publication_sha256"),
            "producer_repository": new_payload.get("producer_repository"),
            "producer_commit": new_payload.get("producer_commit"),
            "platform_repository": new_payload.get("platform_repository"),
            "platform_commit": new_payload.get("platform_commit"),
        },
    }


def _load_publication(root: Path) -> dict[str, Any]:
    target_path = root / "targets.json"
    receipt_path = root / "receipt.json"
    targets = json.loads(target_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(targets, dict) or not isinstance(receipt, dict):
        raise ValueError("publication files must contain JSON objects")
    merged = dict(targets)
    merged.update({key: value for key, value in receipt.items() if key not in merged})
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = compare_artifacts(_load_publication(args.old), _load_publication(args.new))
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
