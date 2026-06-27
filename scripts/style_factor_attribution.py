#!/usr/bin/env python3
"""
Run full-market A-share style factor analysis and publish results for strategy attribution.

Wraps financial-research/scripts/style_analysis.py via subprocess (CLI only —
no Python imports from financial_research, per workspace convention).

Produces 5 classic factors (Size, Value, Momentum, Quality, LowVol) as monthly-
rebalanced long-short portfolios, plus an optional strategy attribution report
that regresses your strategy's daily returns against factor returns.

Output lands under $DATA_PLATFORM_ROOT/strategy_outputs/style_factors/.

Usage:
  # Factor analysis only (no strategy input):
  python scripts/style_factor_attribution.py --out-name 20260627

  # Strategy attribution (the main workspace use case):
  python scripts/style_factor_attribution.py \\
    --strategy-csv ~/code/cross-sectional-trees/outputs/cstree_returns.csv \\
    --strategy-name cstree \\
    --out-name 20260627

  # Quick iteration (2020+ only, ~1 min):
  python scripts/style_factor_attribution.py --quick --out-name test
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


FIN_RESEARCH = Path("~/code/financial-research").expanduser()
STYLE_SCRIPT = FIN_RESEARCH / "scripts" / "style_analysis.py"
MDP_VENV_PYTHON = Path(
    "~/code/research-workspace/market-data-platform/.venv/bin/python3"
).expanduser()
MDP_ENV_FILE = Path(
    "~/code/research-workspace/market-data-platform/.env.local"
).expanduser()
MDP_ROOT = Path("~/code/research-workspace/market-data-platform").expanduser()

FACTOR_NAMES = ["size", "value", "momentum", "quality", "lowvol"]


def resolve_data_platform_root() -> Path:
    env = os.environ.get("DATA_PLATFORM_ROOT", "")
    if not env:
        sys.exit("DATA_PLATFORM_ROOT is not set.")
    root = Path(env).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"DATA_PLATFORM_ROOT ({root}) is not a directory.")
    return root


def validate_prerequisites() -> None:
    missing = []
    if not STYLE_SCRIPT.is_file():
        missing.append(f"style_analysis.py not found at {STYLE_SCRIPT}")
    if not MDP_VENV_PYTHON.is_file():
        missing.append(f"mdp venv python not found at {MDP_VENV_PYTHON}")
    if not MDP_ENV_FILE.is_file():
        missing.append(f".env.local not found at {MDP_ENV_FILE}")
    if missing:
        sys.exit("\n".join(missing))
    # Check for matplotlib + tabulate in mdp venv
    for pkg in ("matplotlib", "tabulate"):
        r = subprocess.run(
            [str(MDP_VENV_PYTHON), "-c", f"import {pkg}"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            sys.exit(
                f"{pkg} is not installed in mdp venv. Run:\n"
                f"  cd {MDP_ROOT} && uv pip install matplotlib tabulate"
            )


def run_style_analysis(
    data_root: str,
    outdir: Path,
    quick: bool,
    strategy_csv: str | None,
    strategy_name: str,
) -> Path:
    """Run style_analysis.py via subprocess. Returns path to output directory."""
    cmd = [
        str(MDP_VENV_PYTHON),
        str(STYLE_SCRIPT),
        "--data-root", data_root,
        "--outdir", str(outdir),
    ]
    if quick:
        cmd.append("--quick")
    if strategy_csv:
        cmd.extend(["--strategy-csv", strategy_csv, "--strategy-name", strategy_name])

    env = os.environ.copy()
    env["DATA_PLATFORM_ROOT"] = data_root
    # Source .env.local equivalents (read key vars)
    _load_env_local(env)

    print(f"[run] {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, env=env, cwd=str(FIN_RESEARCH))
    if result.returncode != 0:
        sys.exit(f"style_analysis.py exited with code {result.returncode}")
    return outdir


def _load_env_local(env: dict) -> None:
    """Read .env.local into env dict (simple key=value, no shell syntax)."""
    try:
        with open(MDP_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in env:
                    env[key] = val
    except OSError:
        pass  # env file optional at this layer; caller sets DATA_PLATFORM_ROOT


def publish(artifacts_dir: Path, dst_root: Path, out_name: str) -> Path:
    """Copy factor CSVs, summary, correlation, and report to standard location."""
    dst_dir = dst_root / out_name
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Copy factor daily returns
    files_copied: list[str] = []
    for name in FACTOR_NAMES:
        src = artifacts_dir / f"factor_{name}_daily.csv"
        if src.is_file():
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
            files_copied.append(src.name)

    # Copy summary + correlation
    for base in ("factor_summary.json", "factor_correlation.json", "factor_yearly.csv"):
        src = artifacts_dir / base
        if src.is_file():
            shutil.copy2(src, dst_dir / base)
            files_copied.append(base)

    # Copy report
    report_src = artifacts_dir / "style_analysis_report.md"
    if report_src.is_file():
        shutil.copy2(report_src, dst_dir / "style_analysis_report.md")
        files_copied.append("style_analysis_report.md")

    # Copy charts
    for chart in (
        "style_factor_nav.png",
        "style_factor_comparison.png",
        "style_factor_corr.png",
        "style_factor_yearly.png",
    ):
        src = artifacts_dir / chart
        if src.is_file():
            shutil.copy2(src, dst_dir / chart)
            files_copied.append(chart)

    # Write manifest
    manifest = {
        "source": str(artifacts_dir),
        "destination": str(dst_dir),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "files": files_copied,
    }
    manifest_path = dst_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    # Update latest pointer
    latest_file = dst_root / "latest.txt"
    latest_file.write_text(f"{out_name}\n")

    print(f"\n[publish] {len(files_copied)} files -> {dst_dir}")
    for f in sorted(files_copied):
        print(f"          {f}")
    print(f"          manifest.json")
    return dst_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run A-share 5-factor style analysis and publish for strategy attribution."
    )
    parser.add_argument(
        "--strategy-csv",
        default=None,
        help="Path to strategy daily return CSV (date, daily_return) for OLS attribution.",
    )
    parser.add_argument(
        "--strategy-name",
        default="strategy",
        help="Strategy name for report (default: 'strategy').",
    )
    parser.add_argument(
        "--out-name",
        required=True,
        help="Subdirectory name under strategy_outputs/style_factors/ (e.g. 20260627).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Sample mode: 2020-2026 only (~1 min vs ~5 min full).",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Override DATA_PLATFORM_ROOT (default: from env).",
    )
    args = parser.parse_args()

    # Resolve paths
    data_root = args.data_root or str(resolve_data_platform_root())
    platform_root = resolve_data_platform_root()

    validate_prerequisites()

    # Run in a temp dir inside financial-research, then publish to platform
    tmp_out = FIN_RESEARCH / "artifacts" / f"style_analysis_{args.out_name}"
    tmp_out.mkdir(parents=True, exist_ok=True)

    artifacts_dir = run_style_analysis(
        data_root=data_root,
        outdir=tmp_out,
        quick=args.quick,
        strategy_csv=args.strategy_csv,
        strategy_name=args.strategy_name,
    )

    # Publish to workspace standard location
    dst_root = platform_root / "strategy_outputs" / "style_factors"
    publish(artifacts_dir, dst_root, args.out_name)
    print(f"\n[OK] Published to {dst_root / args.out_name}/")


if __name__ == "__main__":
    main()
