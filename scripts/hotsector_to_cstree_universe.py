#!/usr/bin/env python3
"""Convert hot-sector-screener candidate universe to strategy-pipeline by_date format.

hot-sector-screener outputs:
  outputs/<YYYYMMDD>/candidate_universe.csv  (columns: ts_code, name, relevance, source_topics)
  outputs/<YYYYMMDD>/candidate_universe.json (candidate_universe array)

strategy-pipeline research_universe.by_date_file expects:
  trade_date,symbol[,selected]

Usage:
  # From a specific hotsector output directory (auto-detects date from dir name):
  python scripts/hotsector_to_cstree_universe.py \\
    --input ~/code/hot-sector-screener/outputs/20260619

  # Explicit trade date (overrides directory-name detection):
  python scripts/hotsector_to_cstree_universe.py \\
    --input ~/code/hot-sector-screener/outputs/20260619/candidate_universe.csv \\
    --trade-date 2026-06-19

  # Append mode (accumulate multiple days in one file):
  python scripts/hotsector_to_cstree_universe.py \\
    --input ~/code/hot-sector-screener/outputs/20260619 \\
    --out universe.csv --append

Output columns:
  trade_date  — YYYY-MM-DD
  symbol      — stock code (e.g. 300308.SZ)
  selected    — always true
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path


_DATE_FROM_DIR = re.compile(r"(\d{8})")


def detect_date(path: Path) -> str:
    """Try to extract YYYYMMDD from directory name, return YYYY-MM-DD."""
    for part in reversed(path.parts):
        m = _DATE_FROM_DIR.search(part)
        if m:
            raw = m.group(1)
            return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return ""


def read_candidates(input_path: Path) -> list[dict]:
    """Read candidates from JSON or CSV. Returns list of dicts with at least 'ts_code'."""
    if input_path.is_dir():
        json_file = input_path / "candidate_universe.json"
        csv_file = input_path / "candidate_universe.csv"
        if json_file.is_file():
            return _read_json(json_file)
        if csv_file.is_file():
            return _read_csv(csv_file)
        sys.exit(f"No candidate_universe.json or .csv found in {input_path}")

    if input_path.suffix == ".json":
        return _read_json(input_path)
    if input_path.suffix == ".csv":
        return _read_csv(input_path)

    sys.exit(f"Unsupported file type: {input_path}. Expected .json or .csv.")


def _read_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    candidates = data.get("candidate_universe", [])
    if not candidates:
        print(f"Warning: empty candidate_universe in {path}", file=sys.stderr)
    return candidates


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def convert(candidates: list[dict], trade_date: str) -> list[dict]:
    """Convert hotsector candidate records to cstree by_date rows."""
    rows = []
    seen = set()
    for c in candidates:
        symbol = c.get("ts_code", "").strip()
        if not symbol:
            continue
        if symbol in seen:
            continue
        seen.add(symbol)
        rows.append({
            "trade_date": trade_date,
            "symbol": symbol,
            "selected": "true",
        })
    return rows


def write_output(rows: list[dict], out_path: Path, append: bool) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append and out_path.exists() else "w"
    write_header = mode == "w"

    with open(out_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["trade_date", "symbol", "selected"])
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    action = "Appended" if (mode == "a" and rows) else "Wrote"
    print(f"{action} {len(rows)} rows to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert hotsector candidate universe to cstree by_date CSV."
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to hotsector output directory, candidate_universe.json, or .csv",
    )
    parser.add_argument(
        "--trade-date",
        default=None,
        help="Trade date as YYYY-MM-DD (default: auto-detect from directory name)",
    )
    parser.add_argument(
        "--out", "-o",
        default=None,
        help="Output CSV path. If not set, uses "
        "$DATA_PLATFORM_ROOT/strategy_outputs/hot_sector_screener/by_date/cstree_universe.csv",
    )
    parser.add_argument(
        "--append", "-a",
        action="store_true",
        help="Append to existing output file instead of overwriting",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        sys.exit(f"Input not found: {input_path}")

    candidates = read_candidates(input_path)
    if not candidates:
        print("No candidates to convert.", file=sys.stderr)
        sys.exit(1)

    trade_date = args.trade_date or detect_date(input_path)
    if not trade_date:
        sys.exit(
            "Could not detect trade date. Pass --trade-date YYYY-MM-DD explicitly."
        )

    rows = convert(candidates, trade_date)

    if args.out:
        out_path = Path(args.out).expanduser()
    else:
        root = os.environ.get("DATA_PLATFORM_ROOT", "")
        if not root:
            sys.exit(
                "DATA_PLATFORM_ROOT is not set. "
                "Export it or pass --out explicitly."
            )
        out_path = (
            Path(root).expanduser().resolve()
            / "strategy_outputs"
            / "hot_sector_screener"
            / "by_date"
            / "cstree_universe.csv"
        )

    write_output(rows, out_path, args.append)


if __name__ == "__main__":
    main()
