from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_distribution_declares_only_public_registry_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    dev_dependencies = project["dependency-groups"]["dev"]

    assert dependencies == ["numpy>=2.5.2", "pandas>=2.0"]
    assert dev_dependencies == ["pytest>=9.0.3", "ruff>=0.8"]
    assert "tool" not in project or "uv" not in project["tool"]


def test_artifact_schema_requires_the_observable_report_fields() -> None:
    schema = json.loads(
        (ROOT / "contracts" / "style-factor-backtest-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert schema["$id"] == "portfolio_backtester.style_factor_backtest.v1"
    assert schema["required"] == [
        "artifact_type",
        "schema_version",
        "signal",
        "n_quantiles",
        "observations",
        "cumulative_return",
        "returns",
    ]
    assert schema["properties"]["returns"]["items"]["required"] == [
        "period_end",
        "long_return",
        "short_return",
        "long_short_return",
    ]
