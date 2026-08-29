from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "strategy-research" / "experiments" / "pipeline_research" / "runner_manifest.json"


def _manifest() -> dict[str, object]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_every_public_research_entrypoint_has_one_explicit_owner() -> None:
    payload = _manifest()
    entries = payload["public_entrypoints"]
    assert isinstance(entries, list)

    pipeline_files = {
        path.relative_to(ROOT / "strategy-pipeline").as_posix()
        for path in (ROOT / "strategy-pipeline" / "scripts" / "research").glob("*.py")
    }
    declared = {item["path"] for item in entries}
    assert declared == {f"scripts/research/{Path(path).name}" for path in pipeline_files}

    for item in entries:
        assert item["owner"] in {"strategy-app", "strategy-pipeline"}
        assert item["research_spec"] in {
            "strategy-research/experiments/configs/daily_watch20_research.yml",
            None,
        }
        assert item["operational_responsibilities"]


def test_private_runner_inventory_is_disjoint_from_public_entrypoints() -> None:
    payload = _manifest()
    private = payload["private_runners"]
    public = payload["public_entrypoints"]
    assert isinstance(private, list)
    assert isinstance(public, list)
    public_names = {Path(item["path"]).name for item in public}
    private_names = {Path(item["path"]).name for item in private}
    assert public_names.isdisjoint(private_names)

    for item in private:
        path = ROOT / "strategy-research" / item["path"]
        assert path.is_file(), path
        assert item["owner"] == "strategy-research"
