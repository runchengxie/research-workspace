from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic-style-factor.csv"


def _assert_allowed_package_sources(lock: dict[str, object]) -> None:
    packages = lock["package"]
    assert isinstance(packages, list)
    for package in packages:
        assert isinstance(package, dict)
        source = package["source"]
        if package["name"] == "quant-platform-local-prototype":
            assert source == {"editable": "."}
        else:
            assert source == {"registry": "https://pypi.org/simple"}


def _cli_artifact(tmp_path: Path) -> dict[str, object]:
    output = tmp_path / "style-factor-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "portfolio_backtester.style_factor_cli",
            "--input",
            str(EXAMPLE),
            "--output",
            str(output),
            "--signal",
            "size",
            "--quantiles",
            "2",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(output.read_text(encoding="utf-8"))


def test_distribution_declares_only_public_registry_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    dev_dependencies = project["dependency-groups"]["dev"]

    assert dependencies == ["numpy>=2.5.2", "pandas>=2.0"]
    assert dev_dependencies == ["jsonschema>=4.25", "pytest>=9.0.3", "ruff>=0.8"]
    assert "tool" not in project or "uv" not in project["tool"]


def test_cli_artifact_validates_against_draft_2020_12_schema(tmp_path: Path) -> None:
    schema = json.loads(
        (ROOT / "contracts" / "style-factor-backtest-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)

    validator.validate(_cli_artifact(tmp_path))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda artifact: artifact.update({"unexpected": True}),
        lambda artifact: artifact.update({"observations": "1"}),
        lambda artifact: artifact["returns"][0].update({"long_return": "0.01"}),
    ],
)
def test_schema_rejects_additional_properties_and_type_drift(
    tmp_path: Path,
    mutation,
) -> None:
    schema = json.loads(
        (ROOT / "contracts" / "style-factor-backtest-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    artifact = deepcopy(_cli_artifact(tmp_path))
    mutation(artifact)

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(artifact)


def test_lock_allows_only_pypi_and_the_project_editable_source() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

    _assert_allowed_package_sources(lock)


@pytest.mark.parametrize(
    "source",
    [
        {"git": "https://github.com/example/package.git"},
        {"directory": "../workspace-package"},
        {"registry": "https://packages.example.internal/simple"},
        {"editable": "../unexpected-local-package"},
    ],
)
def test_lock_source_policy_rejects_nonpublic_or_unexpected_sources(
    source: dict[str, str],
) -> None:
    lock = {"package": [{"name": "unexpected-package", "source": source}]}

    with pytest.raises(AssertionError):
        _assert_allowed_package_sources(lock)
