#!/usr/bin/env python3
"""Run A-share 9-factor style analysis and publish results for strategy attribution.

Now directly imports style_factors (part of research-workspace).

Usage:
  python -m src.style_factors.style_factor_attribution --out-name 20260629
  python -m src.style_factors.style_factor_attribution \\
    --strategy-csv returns.csv --strategy-name strategy --out-name 20260629
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from src.research_contracts import (
    ArtifactEnvelopeV2,
    LineageInput,
    ProducerIdentity,
    build_file_receipts,
    canonical_json_sha256,
    file_receipt_payload,
    file_sha256,
)

from .workflow import run_style_factor_analysis

STYLE_ARTIFACT_SCHEMA_VERSION = "research.style-factors.v1"
REQUIRED_STYLE_FILES = (
    "factor_summary.json",
    "factor_correlation.json",
    "factor_yearly.csv",
    "style_analysis_report.md",
    "style_factor_nav.png",
    "style_factor_comparison.png",
    "style_factor_corr.png",
    "style_factor_yearly.png",
    "meta.json",
)


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _lineage(data_root: Path, strategy_csv: Path | None) -> tuple[LineageInput, ...]:
    candidates = [
        (
            "market-data-platform:a_share_current",
            data_root / "metadata" / "current_assets" / "a_share_current.json",
        )
    ]
    if strategy_csv is not None:
        candidates.append(("strategy_returns", strategy_csv))
    return tuple(
        LineageInput(artifact_id=artifact_id, sha256=file_sha256(path))
        for artifact_id, path in candidates
        if path.is_file()
    )


def _write_publish_manifest(
    *,
    outdir: Path,
    out_name: str,
    data_root: Path,
    strategy_csv: Path | None,
    strategy_name: str,
    quick: bool,
) -> None:
    artifact_paths = sorted(
        path for path in outdir.iterdir() if path.is_file() and path.name != "manifest.json"
    )
    receipt_payload = file_receipt_payload(build_file_receipts(outdir, artifact_paths))
    inventory_sha256 = str(receipt_payload["inventory_sha256"])
    configuration_sha256 = canonical_json_sha256(
        {
            "quick": quick,
            "strategy_name": strategy_name,
            "strategy_csv": str(strategy_csv.resolve()) if strategy_csv else None,
        }
    )
    envelope = ArtifactEnvelopeV2(
        artifact_id=f"style-factors:{out_name}",
        artifact_type="style_factor_analysis",
        run_id=out_name,
        created_at=datetime.now(UTC),
        producer=ProducerIdentity(
            repository="research-workspace",
            version="0.1.0",
            commit=_git_commit(),
            backend="style_factors",
        ),
        configuration_sha256=configuration_sha256,
        content_sha256=inventory_sha256,
        lineage=_lineage(data_root, strategy_csv),
    )
    manifest = {
        "schema_version": STYLE_ARTIFACT_SCHEMA_VERSION,
        "out_name": out_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "artifact_envelope": envelope.to_mapping(),
        "file_receipts": receipt_payload,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def _publish_latest(output_base: Path, out_name: str) -> None:
    output_base.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_base,
        prefix=".latest.",
        delete=False,
    ) as handle:
        handle.write(f"{out_name}\n")
        temporary = Path(handle.name)
    temporary.replace(output_base / "latest.txt")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-name", required=True, help="Output directory name")
    ap.add_argument("--strategy-csv", help="Strategy daily return CSV")
    ap.add_argument("--strategy-name", default="strategy")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    data_root_raw = os.environ.get("DATA_PLATFORM_ROOT", "").strip()
    if not data_root_raw:
        raise SystemExit(
            "环境变量 DATA_PLATFORM_ROOT 未设置。请先导出数据根目录，"
            "例如：export DATA_PLATFORM_ROOT=/path/to/market-data-platform"
        )
    data_root = Path(data_root_raw).expanduser().resolve()
    output_base = data_root / "strategy_outputs" / "style-factors"
    outdir = output_base / args.out_name
    if outdir.exists():
        raise SystemExit(f"版本化输出目录已存在，拒绝覆盖：{outdir}")
    output_base.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{args.out_name}.", dir=output_base))
    strategy_csv = Path(args.strategy_csv).expanduser().resolve() if args.strategy_csv else None

    print(f"[style_factors] staging={staging}")

    try:
        artifacts = run_style_factor_analysis(
            data_root=data_root,
            outdir=staging,
            quick=args.quick,
            strategy_csv=strategy_csv,
            strategy_name=args.strategy_name,
        )
        _write_publish_manifest(
            outdir=artifacts.outdir,
            out_name=args.out_name,
            data_root=data_root,
            strategy_csv=strategy_csv,
            strategy_name=args.strategy_name,
            quick=args.quick,
        )
        staging.replace(outdir)
        _publish_latest(output_base, args.out_name)
    except BaseException:
        if staging.exists():
            import shutil

            shutil.rmtree(staging)
        raise

    print(f"\n[OK] 9-factor results → {outdir}/")
    for f in sorted(outdir.iterdir()):
        print(f"     {f.name}")


if __name__ == "__main__":
    main()
