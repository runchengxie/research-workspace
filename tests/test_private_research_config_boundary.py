from pathlib import Path

import pytest
from strategy_pipeline.config_utils import resolve_pipeline_config

ROOT = Path(__file__).resolve().parents[1]


def test_private_research_config_is_explicitly_resolvable_from_workspace():
    private_config = ROOT / "strategy-research/experiments/configs/daily_watch20_research.yml"

    assert private_config.is_file()
    resolved = resolve_pipeline_config(private_config)

    assert resolved.data["metadata"]["owner"] == "strategy-research"
    assert resolved.data["eval"]["run_name"] == "daily_watch20_private_research"


def test_private_research_config_missing_from_workspace_fails_closed():
    with pytest.raises(SystemExit, match="git submodule update --init strategy-research"):
        resolve_pipeline_config(
            "strategy-research/experiments/configs/missing_private_research.yml"
        )
