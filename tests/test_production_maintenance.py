import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "maintain-production.sh"
PROMOTE_SCRIPT = Path(__file__).parents[1] / "scripts" / "promote-production.sh"


def make_app(root: Path, name: str) -> Path:
    base = root / name
    releases = base / "releases"
    releases.mkdir(parents=True)
    (releases / "current-release").mkdir()
    (releases / "old-release").mkdir()
    (releases / "oldest-release").mkdir()
    os.symlink("releases/current-release", base / "current")
    return base


def test_maintenance_dry_run_is_safe_and_checks_both_apps(tmp_path: Path) -> None:
    make_app(tmp_path, "research-workspace")
    make_app(tmp_path, "market-intel")

    result = subprocess.run(
        ["bash", str(SCRIPT), "--production-root", str(tmp_path), "--dry-run", "--keep", "2"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("would remove") == 2
    assert (tmp_path / "research-workspace/releases/oldest-release").is_dir()
    assert (tmp_path / "market-intel/releases/oldest-release").is_dir()


def test_maintenance_stops_when_disk_threshold_is_not_met(tmp_path: Path) -> None:
    make_app(tmp_path, "research-workspace")
    make_app(tmp_path, "market-intel")

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--production-root",
            str(tmp_path),
            "--min-free-gb",
            "999999",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "free space" in result.stderr


def test_promotion_does_not_recheck_generated_venv_links_as_source_changes() -> None:
    script = PROMOTE_SCRIPT.read_text(encoding="utf-8")

    assert "local commit release current tmp fresh=0" in script
    assert "(( fresh )) || assert_clean \"$release\"" in script
