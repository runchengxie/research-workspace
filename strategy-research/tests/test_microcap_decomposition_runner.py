from __future__ import annotations

from experiments.style_factors.microcap_characteristic_decomposition_20260829 import (
    ARTIFACTS,
    build_decomposition_manifest,
)


def test_decomposition_manifest_freezes_primary_specification() -> None:
    manifest = build_decomposition_manifest(data_end="2026-07-31")
    assert manifest["illiquidity"] == {"window": 60, "min_observations": 45}
    assert manifest["max"] == {"window": 21, "min_observations": 15}
    assert manifest["ivol"] == {"window": 60, "min_observations": 40}
    assert manifest["turnover"] == {"window": 60, "min_observations": 45}
    assert manifest["hac_maxlags"] == 3
    assert manifest["holdout_start"] == "2024-01-01"
    assert manifest["exclusion_percentiles"] == [0.0, 0.1, 0.2, 0.3]


def test_decomposition_artifact_names_are_stable() -> None:
    assert set(ARTIFACTS.values()) == {
        "microcap_characteristics.csv",
        "microcap_double_sorts.csv",
        "microcap_cross_sectional_coefficients.csv",
        "microcap_coefficient_summary.csv",
        "microcap_decomposition_summary.json",
    }
