from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workspace_architecture.py"

sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("workspace_architecture", SCRIPT)
workspace_architecture = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = workspace_architecture
spec.loader.exec_module(workspace_architecture)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _synthetic_model(root: Path, *, cyclic: bool = False) -> Path:
    model_path = root / "docs" / "architecture-model.yml"
    _write(
        model_path,
        """
schema_version: workspace_architecture.v1
components:
  - id: producer
    repo_path: producer
    plane: research
    role: producer
    package_roots: [producer_pkg]
    source_roots: [src/producer_pkg]
    runtime_cycle_check: true
  - id: consumer
    repo_path: consumer
    plane: application
    role: consumer
    package_roots: [consumer_pkg]
    source_roots: [src/consumer_pkg]
    runtime_cycle_check: true
external_components: [external-system]
""".strip()
        + "\n",
    )
    _write(root / "consumer" / "src" / "consumer_pkg" / "api.py", "def run():\n    return 1\n")
    producer_source = "from consumer_pkg import api\n\ndef execute():\n    return api.run()\n"
    _write(root / "producer" / "src" / "producer_pkg" / "main.py", producer_source)
    if cyclic:
        _write(
            root / "consumer" / "src" / "consumer_pkg" / "cycle.py",
            "from producer_pkg import main\n\ndef bounce():\n    return main.execute()\n",
        )
    return model_path


def test_import_and_call_graph_resolve_first_party_edges(tmp_path: Path) -> None:
    model_path = _synthetic_model(tmp_path)
    model = workspace_architecture.load_model(tmp_path, model_path=model_path)

    import_graph = workspace_architecture.build_import_graph(tmp_path, model)
    call_graph = workspace_architecture.build_call_graph(tmp_path, model)

    assert any(
        edge["source"] == "producer"
        and edge["target"] == "consumer"
        and edge["module"] == "consumer_pkg"
        for edge in import_graph["edges"]
    )
    assert any(
        edge["source"] == "producer"
        and edge["target"] == "consumer"
        and edge["target_symbol"] == "consumer_pkg.api.run"
        for edge in call_graph["edges"]
    )
    assert call_graph["completeness"] == "conservative-static"


def test_artifact_graph_projects_producer_and_consumers(tmp_path: Path) -> None:
    model_path = _synthetic_model(tmp_path)
    model = workspace_architecture.load_model(tmp_path, model_path=model_path)
    manifest_path = tmp_path / "docs" / "artifact-contracts.yml"
    _write(
        manifest_path,
        json.dumps(
            {
                "schema_version": "artifact_contracts.v1",
                "artifact_envelope": {},
                "artifacts": [
                    {
                        "artifact": "signals.parquet",
                        "owner": "producer",
                        "producer": "producer",
                        "consumers": ["consumer", "external-system"],
                    }
                ],
            }
        ),
    )

    graph = workspace_architecture.build_artifact_graph(
        tmp_path,
        model,
        manifest_path=manifest_path,
    )

    assert {tuple((edge["source"], edge["target"], edge["kind"])) for edge in graph["edges"]} == {
        ("producer", "artifact:signals.parquet", "produces"),
        ("artifact:signals.parquet", "consumer", "consumes"),
        ("artifact:signals.parquet", "external-system", "consumes"),
    }
    assert graph["errors"] == []


def test_version_pin_differences_are_warnings() -> None:
    differences = workspace_architecture.compare_version_pins(
        workspace_revisions={"producer": "aaaaaaaa"},
        local_pins={"consumer": {"producer": "bbbbbbbb"}},
    )

    assert differences == [
        {
            "consumer": "consumer",
            "dependency": "producer",
            "workspace_revision": "aaaaaaaa",
            "standalone_revision": "bbbbbbbb",
            "severity": "warning",
        }
    ]


def test_version_graph_uses_workspace_head_for_root_subdirectory_packages(tmp_path: Path) -> None:
    model_path = tmp_path / "docs" / "architecture-model.yml"
    _write(
        model_path,
        """
schema_version: workspace_architecture.v1
components:
  - id: research-contracts
    repo_path: .
    plane: contract
    role: shared-contracts
    package_roots: [research_contracts]
    source_roots: [src/research_contracts]
    runtime_cycle_check: true
  - id: consumer
    repo_path: consumer
    plane: application
    role: consumer
    package_roots: [consumer_pkg]
    source_roots: [src/consumer_pkg]
    runtime_cycle_check: true
external_components: []
""".strip()
        + "\n",
    )
    _write(
        tmp_path / "consumer" / "pyproject.toml",
        """
[project]
name = "consumer"
version = "0.1.0"

[tool.uv.sources]
research-contracts = { git = "https://example.invalid/workspace.git", rev = "deadbeef" }
""".strip()
        + "\n",
    )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Architecture Test",
            "-c",
            "user.email=architecture@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    model = workspace_architecture.load_model(tmp_path, model_path=model_path)

    graph = workspace_architecture.build_version_graph(tmp_path, model)

    assert graph["workspace_revisions"]["research-contracts"] == head
    assert graph["standalone_pin_differences"] == [
        {
            "consumer": "consumer",
            "dependency": "research-contracts",
            "workspace_revision": head,
            "standalone_revision": "deadbeef",
            "severity": "warning",
        }
    ]


def test_version_graph_reports_invalid_pyproject_as_error(tmp_path: Path) -> None:
    model_path = _synthetic_model(tmp_path)
    _write(tmp_path / "consumer" / "pyproject.toml", "[project\n")
    model = workspace_architecture.load_model(tmp_path, model_path=model_path)

    graph = workspace_architecture.build_version_graph(tmp_path, model)

    assert graph["errors"]
    assert graph["errors"][0].startswith("consumer: cannot parse pyproject.toml:")


def test_runtime_import_cycle_is_reported(tmp_path: Path) -> None:
    model_path = _synthetic_model(tmp_path, cyclic=True)
    model = workspace_architecture.load_model(tmp_path, model_path=model_path)
    graph = workspace_architecture.build_import_graph(tmp_path, model)

    cycles = workspace_architecture.find_runtime_cycles(model, graph["edges"])

    assert cycles == [["consumer", "producer", "consumer"]]
