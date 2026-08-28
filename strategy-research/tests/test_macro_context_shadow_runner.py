from pathlib import Path

import pandas as pd
import pytest

from experiments.macro_context_shadow.run_contextual_alpha_shadow import (
    ContextShadowInputs,
    build_feature_variants,
    context_pit_audit,
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
    fund = pd.DataFrame({"fund_accumulation_without_crowding": [1.0]})
    variants = build_feature_variants(
        base,
        context_features=context,
        interaction_features=interactions,
        pit_fundamentals=fundamentals,
        fund_features=fund,
    )
    assert (
        set(variants["C0"])
        < set(variants["C1"])
        < set(variants["C2"])
        < set(variants["C3"])
        < set(variants["C4"])
    )
    assert variants["C2"].iloc[0]["ctx__rate__x__rate_sensitivity"] == 0.3


def test_feature_variant_row_count_must_match() -> None:
    with pytest.raises(ValueError, match="identical row counts"):
        build_feature_variants(
            pd.DataFrame({"x": [1]}), context_features=pd.DataFrame({"y": [1, 2]})
        )


def test_context_pit_audit_is_derived_from_pit_rows() -> None:
    frame = pd.DataFrame(
        {
            "series_id": ["activity.x"],
            "period_start": ["2026-07-01"],
            "period_end": ["2026-07-31"],
            "value": [1.0],
            "unit": ["percent"],
            "published_at": [pd.NaT],
            "observed_at": ["2026-08-20T00:00:00Z"],
            "ingested_at": ["2026-08-20T00:00:00Z"],
            "source_retrieved_at": ["2026-08-20T00:00:00Z"],
            "available_at": ["2026-08-20T00:00:00Z"],
            "vintage_id": ["20260820T000000Z"],
            "revision_number": [0],
            "source_hash": ["a" * 64],
            "revision_covered": [True],
            "reconstructed": [False],
        }
    )
    audit = context_pit_audit(frame, as_of="2026-08-28T23:59:59Z")
    assert audit["revision_covered"] is True
    assert audit["freshness_verified"] is True
