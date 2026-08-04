#!/usr/bin/env python3
"""Build the portable D11-H5 core and optional minute-data archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SUBMODULES = (
    "market-data-platform",
    "alpha-research",
    "portfolio-backtester",
    "research-apps",
    "strategy-pipeline",
    "quant-execution-engine",
)
RESEARCH_ARTIFACTS = (
    "trailing_weekly_strategy_20260803",
    "trailing_four_strategy_20260729",
    "multi_horizon_retrain_20260729",
    "five_direction_campaign_20260729",
    "weekly_direction_refresh_20260803",
)
PACKAGE_SCHEMA = "research.d11-h5-portable-package.v1"


@dataclass(frozen=True)
class PackageInputs:
    workspace: Path
    data_root: Path
    daily_clean: Path
    instruments: Path
    trade_cal: Path
    minute_snapshot: Path
    download_dir: Path
    package_date: str

    @property
    def package_name(self) -> str:
        return f"d11-h5-repro-{self.package_date}"


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _git_commit(repo: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], cwd=repo)


def _assert_clean(repo: Path, *, require_main: bool) -> None:
    branch = _run(["git", "branch", "--show-current"], cwd=repo)
    if require_main and branch != "main":
        raise ValueError(f"仓库未处于 main：{repo}（{branch or 'detached'}）")
    status = _run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo)
    if status:
        raise ValueError(f"仓库存在未提交内容：{repo}\n{status}")


def _current_assets(data_root: Path) -> tuple[Path, Path, Path, str]:
    contract = data_root / "metadata" / "current_assets" / "a_share_current.json"
    payload = json.loads(contract.read_text(encoding="utf-8"))

    def asset(key: str) -> Path:
        entry = payload["assets"][key]
        return Path(entry.get("resolved_path") or entry["alias_path"]).expanduser().resolve()

    daily_entry = payload["assets"]["daily_clean"]
    data_as_of = str(daily_entry["as_of"]).replace("-", "")
    return asset("daily_clean"), asset("instruments"), asset("trade_cal"), data_as_of


def _logical_size(path: Path) -> tuple[int, int]:
    if path.is_file():
        return 1, path.stat().st_size
    files = 0
    size = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            files += 1
            size += item.stat().st_size
    return files, size


def _human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    current = float(value)
    for unit in units:
        if current < 1024 or unit == units[-1]:
            return f"{current:.2f} {unit}"
        current /= 1024
    raise AssertionError("unreachable")


def _copy_tree(source: Path, destination: Path, *, ignore_receipt: bool = False) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)

    def ignore(_directory: str, names: list[str]) -> set[str]:
        if ignore_receipt and "_operational_receipt.json" in names:
            return {"_operational_receipt.json"}
        return set()

    shutil.copytree(
        source,
        destination,
        symlinks=True,
        copy_function=os.link,
        ignore=ignore,
    )


def _export_git(repo: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise FileExistsError(f"源码导出目录已有内容：{destination}")
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=repo,
        stdout=subprocess.PIPE,
    )
    if archive.stdout is None:
        raise RuntimeError("git archive did not expose stdout")
    with tarfile.open(fileobj=archive.stdout, mode="r|") as bundle:
        bundle.extractall(destination, filter="data")
    if archive.wait() != 0:
        raise subprocess.CalledProcessError(archive.returncode, archive.args)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_file_checksums(package_root: Path, filename: str, *, scope: Path | None = None) -> Path:
    output = package_root / filename
    scan_root = scope or package_root
    files = sorted(
        path
        for path in scan_root.rglob("*")
        if path.is_file() and not path.is_symlink() and path != output
    )
    lines = [f"{_sha256(path)}  {path.relative_to(package_root)}" for path in files]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _create_archive(package_root: Path, archive_path: Path, *, level: int) -> None:
    if archive_path.exists():
        raise FileExistsError(f"输出已存在：{archive_path}")
    environment = {**os.environ, "ZSTD_CLEVEL": str(level), "ZSTD_NBTHREADS": "0"}
    subprocess.run(
        [
            "tar",
            "--zstd",
            "--sort=name",
            "--mtime=@0",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "-cf",
            str(archive_path),
            "-C",
            str(package_root.parent),
            package_root.name,
        ],
        check=True,
        env=environment,
    )
    checksum = _sha256(archive_path)
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        f"{checksum}  {archive_path.name}\n",
        encoding="utf-8",
    )


def _copy_core_assets(inputs: PackageInputs, package_root: Path) -> dict[str, Any]:
    data_base = Path("data/market-data-platform/assets/tushare/a_share")
    destinations = {
        "daily_clean": data_base / "daily" / inputs.daily_clean.name,
        "instruments": data_base / "instruments" / inputs.instruments.name,
        "trade_cal": data_base / "trade_cal" / inputs.trade_cal.name,
    }
    _copy_tree(inputs.daily_clean, package_root / destinations["daily_clean"])
    for key, source in (("instruments", inputs.instruments), ("trade_cal", inputs.trade_cal)):
        destination = package_root / destinations[key]
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)
    return {
        key: {
            "source": str(source),
            "path": str(destination),
            "files": _logical_size(source)[0],
            "logical_bytes": _logical_size(source)[1],
        }
        for key, source, destination in (
            ("daily_clean", inputs.daily_clean, destinations["daily_clean"]),
            ("instruments", inputs.instruments, destinations["instruments"]),
            ("trade_cal", inputs.trade_cal, destinations["trade_cal"]),
        )
    }


def _export_code(inputs: PackageInputs, package_root: Path) -> dict[str, dict[str, str]]:
    code_root = package_root / "code" / "research-workspace"
    git_state: dict[str, dict[str, str]] = {}
    _assert_clean(inputs.workspace, require_main=True)
    _export_git(inputs.workspace, code_root)
    git_state["research-workspace"] = {"commit": _git_commit(inputs.workspace)}
    for name in SUBMODULES:
        repo = inputs.workspace / name
        _assert_clean(repo, require_main=False)
        commit = _git_commit(repo)
        pinned_commit = _run(["git", "rev-parse", f"HEAD:{name}"], cwd=inputs.workspace)
        if commit != pinned_commit:
            raise ValueError(
                f"子模块提交与顶层仓库记录不一致：{name}\n当前：{commit}\n记录：{pinned_commit}"
            )
        _export_git(repo, code_root / name)
        git_state[name] = {"commit": commit}
    return git_state


def _copy_research_artifacts(inputs: PackageInputs, package_root: Path) -> dict[str, Any]:
    source_root = inputs.workspace / "strategy-pipeline" / "artifacts"
    destination_root = package_root / "research-artifacts" / "strategy-pipeline"
    inventory: dict[str, Any] = {}
    for name in RESEARCH_ARTIFACTS:
        source = source_root / name
        _copy_tree(source, destination_root / name)
        files, logical_bytes = _logical_size(source)
        inventory[name] = {
            "source": str(source),
            "path": str(Path("research-artifacts/strategy-pipeline") / name),
            "files": files,
            "logical_bytes": logical_bytes,
        }
    return inventory


def _build_core(inputs: PackageInputs, staging: Path, *, level: int, data_as_of: str) -> Path:
    package_root = staging / inputs.package_name
    package_root.mkdir()
    git_state = _export_code(inputs, package_root)
    assets = _copy_core_assets(inputs, package_root)
    research_artifacts = _copy_research_artifacts(inputs, package_root)
    shutil.copy2(inputs.workspace / "packaging/d11_h5/README.md", package_root / "README.md")
    shutil.copy2(inputs.workspace / "packaging/d11_h5/start.sh", package_root / "start.sh")
    (package_root / "start.sh").chmod(0o755)
    manifest = {
        "schema_version": PACKAGE_SCHEMA,
        "package_name": inputs.package_name,
        "created_at": datetime.now(UTC).isoformat(),
        "data_as_of": data_as_of,
        "git": git_state,
        "assets": assets,
        "research_artifacts": research_artifacts,
        "optional_minute_archive": (
            f"d11-h5-minute-1m-tushare-{inputs.minute_snapshot.name.rsplit('_', 1)[-1]}"
            f"-for-{inputs.package_name}.tar.zst"
        ),
    }
    manifest_path = package_root / "package_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_file_checksums(package_root, "PACKAGE_FILES.sha256")
    archive_path = inputs.download_dir / f"{inputs.package_name}.tar.zst"
    shutil.copy2(manifest_path, archive_path.with_suffix(".manifest.json"))
    _create_archive(package_root, archive_path, level=level)
    return archive_path


def _build_minute(inputs: PackageInputs, staging: Path, *, level: int) -> Path:
    package_root = staging / inputs.package_name
    destination = (
        package_root
        / "data/market-data-platform/assets/derived/a_share"
        / inputs.minute_snapshot.name
    )
    _copy_tree(inputs.minute_snapshot, destination, ignore_receipt=True)
    files, logical_bytes = _logical_size(inputs.minute_snapshot)
    marker = {
        "schema_version": "research.d11-h5-minute-addon.v1",
        "package_name": inputs.package_name,
        "source": str(inputs.minute_snapshot),
        "path": str(destination.relative_to(package_root)),
        "files": files,
        "logical_bytes": logical_bytes,
        "portable_receipt": "start.sh setup 会按解压位置重新生成运行回执",
    }
    marker_path = package_root / "MINUTE_PACKAGE.json"
    marker_path.write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_file_checksums(package_root, "MINUTE_PACKAGE_FILES.sha256", scope=destination)
    date_suffix = inputs.minute_snapshot.name.rsplit("_", 1)[-1]
    archive_path = inputs.download_dir / (
        f"d11-h5-minute-1m-tushare-{date_suffix}-for-{inputs.package_name}.tar.zst"
    )
    shutil.copy2(marker_path, archive_path.with_suffix(".manifest.json"))
    _create_archive(package_root, archive_path, level=level)
    return archive_path


def _resolve_inputs(args: argparse.Namespace) -> tuple[PackageInputs, str]:
    workspace = args.workspace.expanduser().resolve()
    data_root = args.data_root.expanduser().resolve()
    daily, instruments, trade_cal, data_as_of = _current_assets(data_root)
    minute = args.minute_snapshot.expanduser().resolve()
    inputs = PackageInputs(
        workspace=workspace,
        data_root=data_root,
        daily_clean=(args.daily_clean.expanduser().resolve() if args.daily_clean else daily),
        instruments=instruments,
        trade_cal=trade_cal,
        minute_snapshot=minute,
        download_dir=args.download_dir.expanduser().resolve(),
        package_date=args.package_date,
    )
    return inputs, data_as_of


def _print_plan(inputs: PackageInputs, component: str) -> None:
    print(f"输出目录：{inputs.download_dir}")
    print(f"包名：{inputs.package_name}")
    if component in {"core", "all"}:
        sources = [inputs.daily_clean, inputs.instruments, inputs.trade_cal]
        sources.extend(
            inputs.workspace / "strategy-pipeline" / "artifacts" / x for x in RESEARCH_ARTIFACTS
        )
        total = sum(_logical_size(path)[1] for path in sources)
        print(f"完整复现包逻辑输入：{_human_bytes(total)}")
    if component in {"minute", "all"}:
        print(f"可选分钟包逻辑输入：{_human_bytes(_logical_size(inputs.minute_snapshot)[1])}")


def _build_parser() -> argparse.ArgumentParser:
    default_workspace = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="构建 D11-H5 可移植复现包")
    parser.add_argument("--workspace", type=Path, default=default_workspace)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path.home() / "data/market-data-platform",
    )
    parser.add_argument("--daily-clean", type=Path)
    parser.add_argument(
        "--minute-snapshot",
        type=Path,
        default=Path.home()
        / "data/market-data-platform/assets/derived/a_share/minute_1m_tushare_v1_20260803",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path.home() / "Downloads",
    )
    parser.add_argument("--package-date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--component", choices=("core", "minute", "all"), default="all")
    parser.add_argument("--compression-level", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    inputs, data_as_of = _resolve_inputs(args)
    _print_plan(inputs, args.component)
    if args.dry_run:
        return 0
    inputs.download_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    if args.component in {"core", "all"}:
        with tempfile.TemporaryDirectory(prefix=".d11-h5-core-", dir=inputs.download_dir) as temp:
            outputs.append(
                _build_core(inputs, Path(temp), level=args.compression_level, data_as_of=data_as_of)
            )
    if args.component in {"minute", "all"}:
        with tempfile.TemporaryDirectory(prefix=".d11-h5-minute-", dir=inputs.download_dir) as temp:
            outputs.append(_build_minute(inputs, Path(temp), level=args.compression_level))
    for output in outputs:
        print(f"完成：{output}（{_human_bytes(output.stat().st_size)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
