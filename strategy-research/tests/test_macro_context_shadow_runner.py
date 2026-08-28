from pathlib import Path

import pandas as pd
import pytest

from experiments.macro_context_shadow.run_contextual_alpha_shadow import (
    ContextShadowInputs,
    build_feature_variants,
    preflight_context,
)


def _inputs(audit: dict) -> ContextShadowInputs:
    return ContextShadowInputs(Path("/tmp/data"), object(), object(), object(), audit)


def test_reconstructed_context_is_explorable_but_not_promotion_safe() -> None:
    audit = {
        "revision_covered": False,
        "freshness_verified": True,
        "reconstructed_series": ["energy.x"],
    }
    exploratory = preflight_context(_inputs(audit), require_promotion_safe=False)
    blocked = preflight_context(_inputs(audit), require_promotion_safe=True)
    assert exploratory.status == "exploration_with_limitations"
    assert exploratory.promotion_eligible is False
    assert blocked.status == "rejected"
    assert "context_contains_reconstructed_series" in blocked.reasons


def test_feature_variants_only_add_configured_columns() -> None:
    base = pd.DataFrame(
        {"trade_date": ["2026-01-01"], "symbol": ["A"], "label": [1.0], "pv": [0.1]}
    )
    context = pd.DataFrame({"ctx__rate": [0.2]})
    interactions = pd.DataFrame({"ctx__rate__x__rate_sensitivity": [0.3]})
    fundamentals = pd.DataFrame({"roe": [0.4]})
    variants = build_feature_variants(
        base,
        context_features=context,
        interaction_features=interactions,
        pit_fundamentals=fundamentals,
    )
    assert set(variants["C0"]) < set(variants["C1"]) < set(variants["C2"]) < set(variants["C3"])
    assert variants["C2"].iloc[0]["ctx__rate__x__rate_sensitivity"] == 0.3


def test_feature_variant_row_count_must_match() -> None:
    with pytest.raises(ValueError, match="identical row counts"):
        build_feature_variants(
            pd.DataFrame({"x": [1]}), context_features=pd.DataFrame({"y": [1, 2]})
        )
