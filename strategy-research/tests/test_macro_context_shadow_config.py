from pathlib import Path

from experiments.macro_context_shadow.run_contextual_alpha_shadow import load_config


def test_macro_context_shadow_config_is_frozen_and_non_production() -> None:
    config = load_config()
    assert config["experiment_id"] == "macro_context_shadow_v1"
    assert config["horizons"] == [5, 20, 60]
    assert config["primary_horizon"] == 20
    assert set(config["challengers"]) == {"C0", "C1", "C2", "C3"}
    assert config["lifecycle"] == "exploration"
    assert config["production_eligible"] is False


def test_config_can_be_loaded_from_explicit_path() -> None:
    assert (
        load_config(Path(__file__).parents[1] / "experiments/macro_context_shadow/experiment.yml")[
            "primary_horizon"
        ]
        == 20
    )
