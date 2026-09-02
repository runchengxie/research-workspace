from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "ensure-shared-production-venv.sh"


def test_shared_environment_install_is_non_editable() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "uv_args=(sync --locked --no-editable)" in script


def test_reuses_shared_environment_but_refreshes_project_binding(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (project / "uv.lock").write_text("lock\n", encoding="utf-8")
    shared = tmp_path / "shared"
    log = tmp_path / "uv.log"
    uv = tmp_path / "uv"
    uv.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' \"$UV_PROJECT_ENVIRONMENT\" >> {log}\n"
        'mkdir -p "$UV_PROJECT_ENVIRONMENT/bin"\n'
        'touch "$UV_PROJECT_ENVIRONMENT/bin/python"\n'
        'chmod +x "$UV_PROJECT_ENVIRONMENT/bin/python"\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)
    command = [
        "bash",
        str(SCRIPT),
        "--project",
        str(project),
        "--name",
        "demo",
        "--shared-root",
        str(shared),
        "--uv",
        str(uv),
    ]

    first = subprocess.run(command, capture_output=True, text=True, check=False)
    second = subprocess.run(command, capture_output=True, text=True, check=False)

    assert first.returncode == second.returncode == 0, second.stderr
    assert log.read_text(encoding="utf-8").splitlines() == [
        str((project / ".venv").resolve()),
        str((project / ".venv").resolve()),
    ]


def write_fake_uv(tmp_path: Path) -> tuple[Path, Path]:
    log = tmp_path / "uv.log"
    uv = tmp_path / "uv"
    uv.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' \"$UV_PROJECT_ENVIRONMENT\" >> {log!s}\n"
        'mkdir -p "$UV_PROJECT_ENVIRONMENT/bin"\n'
        'touch "$UV_PROJECT_ENVIRONMENT/bin/python"\n'
        'chmod +x "$UV_PROJECT_ENVIRONMENT/bin/python"\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)
    return uv, log


def run_script(project: Path, shared: Path, uv: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--project",
            str(project),
            "--name",
            "strategy-pipeline",
            "--shared-root",
            str(shared),
            "--uv",
            str(uv),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_creates_shared_environment_and_links_project_venv(tmp_path: Path) -> None:
    project = tmp_path / "strategy-pipeline"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (project / "uv.lock").write_text("lock-v1\n", encoding="utf-8")
    shared = tmp_path / "shared" / "venvs"
    uv, log = write_fake_uv(tmp_path)

    result = run_script(project, shared, uv)

    assert result.returncode == 0, result.stderr
    assert (project / ".venv").is_symlink()
    target = (project / ".venv").resolve()
    assert target.is_dir()
    assert target.parent == shared / "strategy-pipeline"
    assert (target / "bin/python").exists()
    assert log.read_text(encoding="utf-8").count("\n") == 1


def test_refuses_to_replace_real_project_venv(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("project", encoding="utf-8")
    (project / "uv.lock").write_text("lock", encoding="utf-8")
    (project / ".venv").mkdir()
    uv, _ = write_fake_uv(tmp_path)

    result = run_script(project, tmp_path / "shared", uv)

    assert result.returncode == 1
    assert "refusing to replace" in result.stderr


def test_migrate_existing_venv_moves_it_into_shared_storage(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("project", encoding="utf-8")
    (project / "uv.lock").write_text("lock", encoding="utf-8")
    old_venv = project / ".venv"
    (old_venv / "bin").mkdir(parents=True)
    python = old_venv / "bin/python"
    python.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    python.chmod(0o755)
    uv, _ = write_fake_uv(tmp_path)

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--project",
            str(project),
            "--name",
            "project",
            "--shared-root",
            str(tmp_path / "shared"),
            "--uv",
            str(uv),
            "--migrate-existing",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (project / ".venv").is_symlink()
    assert (project / ".venv").resolve().is_dir()
    assert not (project / ".venv.migration-backup").exists()
