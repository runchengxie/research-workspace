#!/usr/bin/env python3
"""Publish guan-etf-rotation-v3 industry signal to DATA_PLATFORM_ROOT standard location.

guan-etf-rotation-v3 writes industry_signal.csv to its own
  artifacts/signals/<run>/industry_signal.csv

hot-sector-screener expects it at:
  $DATA_PLATFORM_ROOT/strategy_outputs/etf_rotation_v3/<run>/industry_signal.csv

This script bridges the gap by copying the output and writing a manifest.

Usage:
  python scripts/publish_etf_industry_signal.py \\
    --src ~/code/guan-etf-rotation-v3/artifacts/signals/20260620_093000 \\
    --dst-name 20260620

The --dst-name becomes the subdirectory under strategy_outputs/etf_rotation_v3/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def resolve_data_platform_root() -> Path:
    env = os.environ.get("DATA_PLATFORM_ROOT", "")
    if not env:
        sys.exit("DATA_PLATFORM_ROOT is not set. Export it or pass --dst explicitly.")
    root = Path(env).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"DATA_PLATFORM_ROOT ({root}) is not a directory.")
    return root


def validate_src(src: Path) -> Path:
    src = src.expanduser().resolve()
    if not src.is_dir():
        sys.exit(f"Source directory not found: {src}")
    csv_path = src / "industry_signal.csv"
    if not csv_path.is_file():
        sys.exit(f"industry_signal.csv not found in {src}")
    return src


def publish(src: Path, dst_root: Path, dst_name: str) -> Path:
    dst_dir = dst_root / dst_name
    dst_dir.mkdir(parents=True, exist_ok=True)

    csv_src = src / "industry_signal.csv"
    csv_dst = dst_dir / "industry_signal.csv"
    shutil.copy2(csv_src, csv_dst)
    print(f"Copied: {csv_src} -> {csv_dst}")

    # Copy summary if present
    summary_src = src / "industry_signal_summary.json"
    if summary_src.is_file():
        summary_dst = dst_dir / "industry_signal_summary.json"
        shutil.copy2(summary_src, summary_dst)
        print(f"Copied: {summary_src} -> {summary_dst}")

    # Write manifest
    manifest = {
        "source": str(src),
        "destination": str(dst_dir),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "files": ["industry_signal.csv"],
    }
    if summary_src.is_file():
        manifest["files"].append("industry_signal_summary.json")

    manifest_path = dst_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Manifest: {manifest_path}")

    # Update or create "latest" pointer
    latest_file = dst_root / "latest.txt"
    latest_file.write_text(f"{dst_name}\n")
    print(f"Latest pointer: {latest_file} -> {dst_name}")

    return dst_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish ETF rotation industry signal to DATA_PLATFORM_ROOT."
    )
    parser.add_argument(
        "--src",
        required=True,
        help="Source run directory containing industry_signal.csv",
    )
    parser.add_argument(
        "--dst-name",
        default=None,
        help="Subdirectory name under strategy_outputs/etf_rotation_v3/ "
        "(default: basename of --src)",
    )
    parser.add_argument(
        "--dst",
        default=None,
        help="Full destination path under DATA_PLATFORM_ROOT "
        "(overrides --dst-name; default: strategy_outputs/etf_rotation_v3/<dst-name>)",
    )
    args = parser.parse_args()

    src = validate_src(Path(args.src))

    if args.dst:
        dst_dir = Path(args.dst).expanduser()
        dst_root = dst_dir.parent
        dst_name = dst_dir.name
    else:
        dst_name = args.dst_name or src.name
        data_root = resolve_data_platform_root()
        dst_root = data_root / "strategy_outputs" / "etf_rotation_v3"

    published = publish(src, dst_root, dst_name)
    print(f"\nPublished to: {published}")


if __name__ == "__main__":
    main()
