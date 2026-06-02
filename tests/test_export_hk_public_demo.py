from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_hk_public_demo.py"


def test_export_hk_public_demo_stages_and_verifies_offline(tmp_path: Path) -> None:
    stage = tmp_path / "hk-cross-sectional-strategy-demo"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads((stage / "export-manifest.json").read_text(encoding="utf-8"))
    assert manifest["offline_smoke"]["status"] == "passed"
    assert manifest["quality_checks"]["status"] == "passed"
    assert manifest["scan"]["status"] == "passed"
    assert manifest["split_manifest"]["schema_version"] == "hk_public_split_manifest.v1"
    assert manifest["split_manifest"]["validation"]["status"] == "passed"
    assert "top-level-hk-public-demo-staging" in manifest["split_manifest"]["record_ids"]
    assert manifest["public_repository"]["name"] == "hk-cross-sectional-strategy-demo"
    assert (stage / "samples" / "summary.json").is_file()
    assert (stage / "samples" / "targets.json").is_file()
    assert not (stage / ".git").exists()


def test_export_hk_public_demo_scan_rejects_private_files(tmp_path: Path) -> None:
    stage = tmp_path / "unsafe"
    stage.mkdir()
    (stage / ".env.local").write_text("ACCESS_TOKEN=private-value\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scan-only", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert {row["check"] for row in payload["issues"]} >= {
        "forbidden_path",
        "credential_assignment",
    }


def test_export_hk_public_demo_scan_rejects_data_archives_and_cache(tmp_path: Path) -> None:
    stage = tmp_path / "unsafe"
    cache_dir = stage / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "prices.parquet").write_text("not public demo content\n", encoding="utf-8")
    (stage / "bundle.zip").write_text("archive placeholder\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scan-only", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    issues = {(row["path"], row["check"]) for row in payload["issues"]}
    assert ("cache/prices.parquet", "forbidden_path") in issues
    assert ("cache/prices.parquet", "licensed_or_archive_suffix") in issues
    assert ("bundle.zip", "licensed_or_archive_suffix") in issues


def test_export_hk_public_demo_scan_rejects_local_absolute_paths(tmp_path: Path) -> None:
    stage = tmp_path / "unsafe"
    stage.mkdir()
    (stage / "README.md").write_text(
        "local debug path: " + "/home/example/private-run\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scan-only", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert {"path": "README.md", "check": "absolute_local_path"} in payload["issues"]


def test_export_hk_public_demo_scan_rejects_workspace_imports(tmp_path: Path) -> None:
    stage = tmp_path / "unsafe"
    source_dir = stage / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "bad.py").write_text("import cstree\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scan-only", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert {"path": "src/bad.py", "check": "workspace_import"} in payload["issues"]


def test_export_hk_public_demo_scan_rejects_provider_runtime_markers(
    tmp_path: Path,
) -> None:
    stage = tmp_path / "unsafe"
    scripts_dir = stage / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "bad.py").write_text("import longport\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scan-only", str(stage)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert {"path": "scripts/bad.py", "check": "runtime_dependency_import"} in payload["issues"]


def test_export_hk_public_demo_allowlist_has_no_template_drift() -> None:
    template_root = ROOT / "demo" / "hk-public-demo-template-v1"
    allowlist = {
        line.strip()
        for line in (ROOT / "demo" / "hk-public-demo-allowlist-v1.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.startswith("#")
    }
    template_files = {
        path.relative_to(template_root).as_posix()
        for path in template_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
        and "samples" not in path.parts
    }

    assert template_files == allowlist
