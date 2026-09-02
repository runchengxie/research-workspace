from __future__ import annotations

import pytest

from research_contracts.asset_registry import (
    PlatformAssetDefinition,
    PlatformAssetRegistry,
)


def _asset(asset_id: str, *, dependencies: tuple[str, ...] = ()) -> PlatformAssetDefinition:
    return PlatformAssetDefinition(
        asset_id=asset_id,
        owner_repository="runchengxie/research-workspace",
        schema_version="example.v1",
        dependencies=dependencies,
        external_inputs=(),
        consumers=("trading-research-dashboard",),
        freshness_kind="market_days",
        freshness_value=1,
    )


def test_registry_topological_order_describes_platform_flow() -> None:
    registry = PlatformAssetRegistry()
    registry.register(_asset("market.a_share_daily_clean"))
    registry.register(
        _asset("features.dailywatch20.v17", dependencies=("market.a_share_daily_clean",))
    )
    registry.register(
        _asset("signals.dailywatch20", dependencies=("features.dailywatch20.v17",))
    )
    registry.register(
        _asset("publication.dashboard", dependencies=("signals.dailywatch20",))
    )

    registry.validate_graph()

    assert registry.topological_order() == (
        "market.a_share_daily_clean",
        "features.dailywatch20.v17",
        "signals.dailywatch20",
        "publication.dashboard",
    )


def test_registry_rejects_missing_internal_dependency() -> None:
    registry = PlatformAssetRegistry()
    registry.register(_asset("signals.dailywatch20", dependencies=("missing.features",)))

    with pytest.raises(ValueError, match="missing dependency"):
        registry.validate_graph()


def test_registry_rejects_dependency_cycle() -> None:
    registry = PlatformAssetRegistry()
    registry.register(_asset("a", dependencies=("b",)))
    registry.register(_asset("b", dependencies=("a",)))

    with pytest.raises(ValueError, match="cycle"):
        registry.validate_graph()


def test_asset_rejects_invalid_freshness_policy() -> None:
    with pytest.raises(ValueError, match="freshness_value"):
        PlatformAssetDefinition(
            asset_id="bad",
            owner_repository="owner/repo",
            schema_version="example.v1",
            dependencies=(),
            external_inputs=(),
            consumers=("market-intel",),
            freshness_kind="market_days",
            freshness_value=None,
        )
