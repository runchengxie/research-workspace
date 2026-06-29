#!/usr/bin/env python3
"""Run A-share 9-factor style analysis and publish results for strategy attribution.

Now directly imports style_factors (part of research-workspace).

Usage:
  python scripts/style_factor_attribution.py --out-name 20260629
  python scripts/style_factor_attribution.py \\
    --strategy-csv returns.csv --strategy-name cstree --out-name 20260629
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

run_style_factor_analysis = import_module("style_factors.workflow").run_style_factor_analysis

DATA_PLATFORM_ROOT = Path(
    os.environ.get("DATA_PLATFORM_ROOT", "/home/richard/data/market-data-platform")
)
OUTPUT_BASE = DATA_PLATFORM_ROOT / "strategy_outputs" / "style_factors"


def _write_publish_manifest(outdir: Path, out_name: str) -> None:
    files = sorted(path.name for path in outdir.iterdir() if path.is_file())
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "out_name": out_name,
        "destination": str(outdir),
        "files": files,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUTPUT_BASE / "latest.txt").write_text(f"{out_name}\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-name", required=True, help="Output directory name")
    ap.add_argument("--strategy-csv", help="Strategy daily return CSV")
    ap.add_argument("--strategy-name", default="strategy")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    outdir = OUTPUT_BASE / args.out_name
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[style_factors] {outdir}")

    artifacts = run_style_factor_analysis(
        data_root=DATA_PLATFORM_ROOT,
        outdir=outdir,
        quick=args.quick,
        strategy_csv=Path(args.strategy_csv) if args.strategy_csv else None,
        strategy_name=args.strategy_name,
    )
    _write_publish_manifest(artifacts.outdir, args.out_name)

    print(f"\n[OK] 9-factor results → {outdir}/")
    for f in sorted(outdir.iterdir()):
        print(f"     {f.name}")


if __name__ == "__main__":
    main()
