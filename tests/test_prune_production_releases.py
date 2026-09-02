import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "prune-production-releases.sh"


def make_release_tree(
    tmp_path: Path,
    names: list[str],
    current: str,
    app_name: str = "app",
) -> Path:
    base = tmp_path / app_name
    releases = base / "releases"
    releases.mkdir(parents=True)
    for index, name in enumerate(names):
        release = releases / name
        release.mkdir()
        (release / "marker").write_text(name, encoding="utf-8")
        timestamp = 1_000_000_000 + index
        os.utime(release, ns=(timestamp, timestamp))
    os.symlink(f"releases/{current}", base / "current")
    return base


def run_prune(base: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "--base", str(base), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_dry_run_keeps_current_and_reports_old_releases(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2", "r3", "r4"], "r2")

    result = run_prune(base, "--keep", "2", "--dry-run")

    assert result.returncode == 0
    assert "would remove" in result.stdout
    assert sorted(p.name for p in (base / "releases").iterdir()) == ["r1", "r2", "r3", "r4"]
    assert os.readlink(base / "current") == "releases/r2"


def test_prune_removes_only_releases_outside_keep_set(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2", "r3", "r4"], "r2")

    result = run_prune(base, "--keep", "2")

    assert result.returncode == 0
    assert sorted(p.name for p in (base / "releases").iterdir()) == ["r2", "r4"]
    assert os.readlink(base / "current") == "releases/r2"


def test_prune_rejects_keep_less_than_two(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2"], "r2")

    result = run_prune(base, "--keep", "1")

    assert result.returncode == 2
    assert "at least 2" in result.stderr


def test_prune_uses_manifest_time_before_release_directory_time(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2", "r3", "r4"], "r2")
    manifests = base / "manifests"
    manifests.mkdir()
    (manifests / "r1.txt").write_text("r1", encoding="utf-8")
    timestamp = 2_000_000_000
    os.utime(manifests / "r1.txt", ns=(timestamp, timestamp))

    result = run_prune(base, "--keep", "2")

    assert result.returncode == 0
    assert sorted(p.name for p in (base / "releases").iterdir()) == ["r1", "r2"]


def test_prune_removes_unreferenced_shared_environments(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2", "r3"], "r2")
    shared = tmp_path / "shared"
    referenced = shared / "strategy-pipeline" / "keep"
    orphan = shared / "strategy-pipeline" / "orphan"
    referenced.mkdir(parents=True)
    orphan.mkdir(parents=True)
    os.symlink(referenced, base / "releases" / "r2" / ".venv")

    result = run_prune(base, "--keep", "2", "--shared-root", str(shared))

    assert result.returncode == 0
    assert referenced.is_dir()
    assert not orphan.exists()


def test_prune_preserves_shared_environment_referenced_by_sibling_app(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2", "r3"], "r2")
    sibling = make_release_tree(tmp_path, ["s1", "s2"], "s2", "sibling")
    shared = tmp_path / "shared"
    referenced = shared / "market-intel" / "keep"
    referenced.mkdir(parents=True)
    os.symlink(referenced, sibling / "releases" / "s2" / ".venv")

    result = run_prune(base, "--keep", "2", "--shared-root", str(shared))

    assert result.returncode == 0
    assert referenced.is_dir()


def test_prune_handles_current_nested_shared_venv_layout(tmp_path: Path) -> None:
    base = make_release_tree(tmp_path, ["r1", "r2"], "r2")
    shared = tmp_path / "shared"
    referenced = shared / "venvs" / "market-intel" / "keep"
    orphan = shared / "venvs" / "market-intel" / "orphan"
    referenced.mkdir(parents=True)
    orphan.mkdir(parents=True)
    os.symlink(referenced, base / "releases" / "r2" / ".venv")

    result = run_prune(base, "--keep", "2", "--shared-root", str(shared))

    assert result.returncode == 0
    assert referenced.is_dir()
    assert not orphan.exists()
