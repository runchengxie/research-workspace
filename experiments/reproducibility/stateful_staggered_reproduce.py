"""Recompute and verify the two frozen stateful-staggered result snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from research_apps.daily_watch20 import run_stateful_staggered_campaign

SOURCE_IDS = (
    "slow_volume_discovery_20251223",
    "slow_volume_cross_source_20260706",
)
INPUT_FILENAMES = ("scores.parquet", "execution_prices.parquet", "trade_calendar.parquet")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _default_input_root(artifact_root: Path) -> Path:
    research_apps = artifact_root.parents[1]
    return research_apps.parent / "strategy-pipeline/artifacts/minute_alpha_campaign_v3"


def _verify_source(source_id: str, input_root: Path, artifact_root: Path) -> dict[str, object]:
    source = input_root / source_id
    output = artifact_root / source_id
    missing = [path for name in INPUT_FILENAMES if not (path := source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen inputs for {source_id}: {missing}")

    inputs = {name: pd.read_parquet(source / name) for name in INPUT_FILENAMES}
    bundle = run_stateful_staggered_campaign(
        inputs["scores.parquet"],
        inputs["execution_prices.parquet"],
        inputs["trade_calendar.parquet"],
        input_lineage={"source_artifact": source_id, "score_variant": "D"},
    )

    frame_receipt: dict[str, object] = {}
    for name, actual in sorted(bundle.frames.items()):
        saved_path = output / f"{name}.parquet"
        expected = pd.read_parquet(saved_path)
        pd.testing.assert_frame_equal(
            actual.reset_index(drop=True),
            expected.reset_index(drop=True),
            check_dtype=True,
            check_exact=True,
            check_like=False,
        )
        frame_receipt[name] = {
            "rows": len(actual),
            "sha256": _sha256(saved_path),
            "status": "exact_frame_match",
        }

    report_path = output / "report.json"
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    if _canonical_json(bundle.report) != _canonical_json(saved_report):
        raise AssertionError(f"report mismatch for {source_id}")

    return {
        "status": "passed",
        "input_files": {
            name: {
                "path": f"{source_id}/{name}",
                "rows": len(inputs[name]),
                "size": (source / name).stat().st_size,
                "sha256": _sha256(source / name),
            }
            for name in INPUT_FILENAMES
        },
        "frames": frame_receipt,
        "report": {
            "path": f"{source_id}/report.json",
            "sha256": _sha256(report_path),
            "status": "exact_json_match",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Existing stateful-staggered snapshot root.",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=None,
        help="Frozen slow-volume artifact root; defaults to the sibling strategy-pipeline.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=None,
        help="Receipt path; defaults to ARTIFACT_ROOT/reproduction_receipt.json.",
    )
    args = parser.parse_args()

    artifact_root = args.artifact_root.expanduser().resolve()
    input_root = (
        args.input_root.expanduser().resolve()
        if args.input_root is not None
        else _default_input_root(artifact_root).resolve()
    )
    receipt_path = (
        args.receipt.expanduser().resolve()
        if args.receipt is not None
        else artifact_root / "reproduction_receipt.json"
    )
    sources = {
        source_id: _verify_source(source_id, input_root, artifact_root)
        for source_id in SOURCE_IDS
    }
    receipt = {
        "schema_version": "daily_watch20.stateful_staggered_reproduction.v1",
        "status": "passed",
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "input_root": "../strategy-pipeline/artifacts/minute_alpha_campaign_v3",
        "artifact_root": "artifacts/stateful_staggered_20260722",
        "comparison": "exact pandas frame equality and canonical JSON equality",
        "sources": sources,
    }
    temporary = receipt_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(receipt_path)
    print(receipt_path)


if __name__ == "__main__":
    main()
