import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "migrate-production-venvs.sh"


def make_release(base: Path, name: str) -> Path:
    release = base / "releases" / name
    (release / ".venv/bin").mkdir(parents=True)
    (release / "pyproject.toml").write_text("project", encoding="utf-8")
    (release / "uv.lock").write_text("lock", encoding="utf-8")
    python = release / ".venv/bin/python"
    python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    python.chmod(0o755)
    return release


def test_migrates_old_release_but_excludes_current(tmp_path: Path) -> None:
    base = tmp_path / "market-intel"
    (base / "releases").mkdir(parents=True)
    old = make_release(base, "old")
    current = make_release(base, "current-release")
    os.symlink("releases/current-release", base / "current")

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--production-root",
            str(tmp_path),
            "--repo",
            "market-intel",
            "--max",
            "1",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (old / ".venv").is_symlink()
    assert (current / ".venv").is_dir()
