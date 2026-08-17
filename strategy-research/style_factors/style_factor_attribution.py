#!/usr/bin/env python3
"""Run A-share style factor analysis and publish results for strategy attribution.

Now directly imports style_factors (part of research-workspace). Supports 15
factors (incl. PIT SW-L1 industry-neutralized Value). Use --from-artifacts to
publish an existing full-sample run without recomputation.

Usage:
  python -m style_factors.style_factor_attribution --out-name 20260629
  python -m style_factors.style_factor_attribution \\
    --strategy-csv returns.csv --strategy-name strategy --out-name 20260629
  python -m style_factors.style_factor_attribution \\
    --out-name 20260730-full-value --from-artifacts artifacts/style_analysis_2008
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from research_contracts import (
    ArtifactEnvelopeV2,
    LineageInput,
    ProducerIdentity,
    build_file_receipts,
    canonical_json_sha256,
    file_receipt_payload,
    file_sha256,
)

from .workflow import StyleFactorArtifacts, run_style_factor_analysis

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


def _validate_out_name(value: str) -> str:
    name = value.strip()
    if not name or name in {".", ".."} or Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError(f"--out-name 必须是单个安全目录名：{value!r}")
    return name


def _validate_required_style_files(directory: Path) -> None:
    missing = [name for name in REQUIRED_STYLE_FILES if not (directory / name).is_file()]
    if missing:
        raise ValueError("风格因子产物缺少必需文件：" + ", ".join(missing))


def _source_artifact_provenance(source_artifacts: Path | None) -> dict | None:
    if source_artifacts is None:
        return None
    payload = {
        "mode": "copied_artifacts",
        "meta_sha256": file_sha256(source_artifacts / "meta.json"),
    }
    source_manifest = source_artifacts / "manifest.json"
    if source_manifest.is_file():
        payload["manifest_sha256"] = file_sha256(source_manifest)
    return payload


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
    source_artifacts: Path | None = None,
) -> None:
    artifact_paths = sorted(
        path for path in outdir.iterdir() if path.is_file() and path.name != "manifest.json"
    )
    receipt_payload = file_receipt_payload(build_file_receipts(outdir, artifact_paths))
    inventory_sha256 = str(receipt_payload["inventory_sha256"])
    source_provenance = _source_artifact_provenance(source_artifacts)
    configuration = {
        "quick": quick,
        "strategy_name": strategy_name,
        "strategy_csv": str(strategy_csv.resolve()) if strategy_csv else None,
        "publish_mode": "copied_artifacts" if source_provenance else "computed",
        "source_artifacts": source_provenance,
    }
    configuration_sha256 = canonical_json_sha256(configuration)
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
        "publish_mode": configuration["publish_mode"],
        "artifact_envelope": envelope.to_mapping(),
        "file_receipts": receipt_payload,
    }
    if source_provenance is not None:
        manifest["source_artifacts"] = source_provenance
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


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-name", required=True, help="Output directory name")
    ap.add_argument("--strategy-csv", help="Strategy daily return CSV")
    ap.add_argument("--strategy-name", default="strategy")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument(
        "--from-artifacts",
        help="Publish an existing artifacts directory as-is (skip recomputation). "
        "Use this to publish a known full-sample run without re-running the analysis.",
    )
    return ap.parse_args()


def _validate_cli_options(args: argparse.Namespace) -> str:
    try:
        out_name = _validate_out_name(args.out_name)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.from_artifacts and args.strategy_csv:
        raise SystemExit("--from-artifacts 不能与 --strategy-csv 同时使用；复制产物不会重新归因")
    if args.from_artifacts and args.quick:
        raise SystemExit("--from-artifacts 的 quick 状态取自源 meta.json，不能同时传 --quick")
    return out_name


def _resolve_data_root() -> Path:
    data_root_raw = os.environ.get("DATA_PLATFORM_ROOT", "").strip()
    if not data_root_raw:
        raise SystemExit(
            "环境变量 DATA_PLATFORM_ROOT 未设置。请先导出数据根目录，"
            "例如：export DATA_PLATFORM_ROOT=/path/to/market-data-platform"
        )
    return Path(data_root_raw).expanduser().resolve()


def _prepare_artifacts(
    args: argparse.Namespace,
    *,
    staging: Path,
    data_root: Path,
    strategy_csv: Path | None,
) -> tuple[StyleFactorArtifacts | SimpleNamespace, bool, Path | None]:
    if not args.from_artifacts:
        artifacts = run_style_factor_analysis(
            data_root=data_root,
            outdir=staging,
            quick=args.quick,
            strategy_csv=strategy_csv,
            strategy_name=args.strategy_name,
        )
        return artifacts, bool(args.quick), None

    source = Path(args.from_artifacts).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"--from-artifacts 目录不存在：{source}")
    _validate_required_style_files(source)
    try:
        source_meta = json.loads((source / "meta.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"无法读取源产物 meta.json：{source / 'meta.json'}") from exc
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, staging / item.name)
    return SimpleNamespace(outdir=staging), bool(source_meta.get("quick", False)), source


def main() -> None:
    args = _parse_args()
    out_name = _validate_cli_options(args)
    data_root = _resolve_data_root()
    output_base = data_root / "strategy_outputs" / "style-factors"
    outdir = output_base / out_name
    if outdir.exists():
        raise SystemExit(f"版本化输出目录已存在，拒绝覆盖：{outdir}")
    output_base.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out_name}.", dir=output_base))
    strategy_csv = Path(args.strategy_csv).expanduser().resolve() if args.strategy_csv else None

    print(f"[style_factors] staging={staging}")

    try:
        artifacts, publish_quick, source_artifacts = _prepare_artifacts(
            args,
            staging=staging,
            data_root=data_root,
            strategy_csv=strategy_csv,
        )
        _validate_required_style_files(artifacts.outdir)
        _write_publish_manifest(
            outdir=artifacts.outdir,
            out_name=out_name,
            data_root=data_root,
            strategy_csv=strategy_csv,
            strategy_name=args.strategy_name,
            quick=publish_quick,
            source_artifacts=source_artifacts,
        )
        staging.replace(outdir)
        _publish_latest(output_base, out_name)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    print(f"\n[OK] style-factors results → {outdir}/")
    for f in sorted(outdir.iterdir()):
        print(f"     {f.name}")


if __name__ == "__main__":
    main()
