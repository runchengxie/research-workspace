"""Logical platform asset graph without adding another Git superproject layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PLATFORM_ASSET_REGISTRY_SCHEMA = "research.platform-asset-registry.v1"
FRESHNESS_KINDS = frozenset({"none", "market_days", "calendar_hours"})


def _text(value: object, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _tuple(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list/tuple")
    values = tuple(_text(item, f"{field_name}[]") for item in value)
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must contain unique values")
    return values


@dataclass(frozen=True)
class PlatformAssetDefinition:
    asset_id: str
    owner_repository: str
    schema_version: str
    dependencies: tuple[str, ...]
    external_inputs: tuple[str, ...]
    consumers: tuple[str, ...]
    freshness_kind: str = "none"
    freshness_value: int | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _text(self.asset_id, "asset_id"))
        object.__setattr__(
            self,
            "owner_repository",
            _text(self.owner_repository, "owner_repository"),
        )
        object.__setattr__(self, "schema_version", _text(self.schema_version, "schema_version"))
        object.__setattr__(self, "dependencies", _tuple(self.dependencies, "dependencies"))
        object.__setattr__(self, "external_inputs", _tuple(self.external_inputs, "external_inputs"))
        object.__setattr__(self, "consumers", _tuple(self.consumers, "consumers"))
        if self.freshness_kind not in FRESHNESS_KINDS:
            raise ValueError("freshness_kind must be one of " + ", ".join(sorted(FRESHNESS_KINDS)))
        if self.freshness_kind == "none":
            if self.freshness_value is not None:
                raise ValueError("freshness_value must be null when freshness_kind=none")
        else:
            if isinstance(self.freshness_value, bool) or not isinstance(self.freshness_value, int):
                raise ValueError("freshness_value must be a positive integer")
            if self.freshness_value <= 0:
                raise ValueError("freshness_value must be > 0 for an active freshness policy")
        if self.asset_id in self.dependencies:
            raise ValueError("asset cannot depend on itself")
        if self.description is not None:
            object.__setattr__(self, "description", _text(self.description, "description"))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "owner_repository": self.owner_repository,
            "schema_version": self.schema_version,
            "dependencies": list(self.dependencies),
            "external_inputs": list(self.external_inputs),
            "consumers": list(self.consumers),
            "freshness": {
                "kind": self.freshness_kind,
                "value": self.freshness_value,
            },
            "description": self.description,
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> PlatformAssetDefinition:
        freshness = payload.get("freshness", {})
        if not isinstance(freshness, dict):
            raise ValueError("freshness must be an object")
        return cls(
            asset_id=payload.get("asset_id", ""),
            owner_repository=payload.get("owner_repository", ""),
            schema_version=payload.get("schema_version", ""),
            dependencies=_tuple(payload.get("dependencies", ()), "dependencies"),
            external_inputs=_tuple(payload.get("external_inputs", ()), "external_inputs"),
            consumers=_tuple(payload.get("consumers", ()), "consumers"),
            freshness_kind=str(freshness.get("kind", "none")),
            freshness_value=freshness.get("value"),
            description=payload.get("description"),
        )


@dataclass
class PlatformAssetRegistry:
    _assets: dict[str, PlatformAssetDefinition] = field(default_factory=dict)

    def register(self, asset: PlatformAssetDefinition) -> None:
        if asset.asset_id in self._assets:
            raise ValueError(f"platform asset already registered: {asset.asset_id}")
        self._assets[asset.asset_id] = asset

    def get(self, asset_id: str) -> PlatformAssetDefinition:
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise KeyError(f"unknown platform asset: {asset_id}") from exc

    def validate_graph(self) -> None:
        known = set(self._assets)
        for asset in self._assets.values():
            missing = [dependency for dependency in asset.dependencies if dependency not in known]
            if missing:
                raise ValueError(
                    f"platform asset {asset.asset_id} has missing dependency: "
                    + ", ".join(sorted(missing))
                )
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        known = set(self._assets)
        for asset in self._assets.values():
            missing = [dependency for dependency in asset.dependencies if dependency not in known]
            if missing:
                raise ValueError(
                    f"platform asset {asset.asset_id} has missing dependency: "
                    + ", ".join(sorted(missing))
                )
        indegree = {asset_id: 0 for asset_id in self._assets}
        children: dict[str, list[str]] = {asset_id: [] for asset_id in self._assets}
        for asset in self._assets.values():
            indegree[asset.asset_id] = len(asset.dependencies)
            for dependency in asset.dependencies:
                children[dependency].append(asset.asset_id)
        for values in children.values():
            values.sort()
        queue = sorted(asset_id for asset_id in self._assets if indegree[asset_id] == 0)
        ordered: list[str] = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for child in children[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
            queue.sort()
        if len(ordered) != len(self._assets):
            unresolved = [asset_id for asset_id, value in indegree.items() if value > 0]
            raise ValueError("platform asset dependency cycle: " + ", ".join(sorted(unresolved)))
        return tuple(ordered)

    def to_mapping(self) -> dict[str, Any]:
        self.validate_graph()
        return {
            "schema_version": PLATFORM_ASSET_REGISTRY_SCHEMA,
            "assets": [
                self._assets[asset_id].to_mapping() for asset_id in self.topological_order()
            ],
        }

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> PlatformAssetRegistry:
        if payload.get("schema_version") != PLATFORM_ASSET_REGISTRY_SCHEMA:
            raise ValueError(
                f"unsupported platform asset registry schema: {payload.get('schema_version')!r}"
            )
        raw_assets = payload.get("assets")
        if not isinstance(raw_assets, list):
            raise ValueError("assets must be a list")
        registry = cls()
        for index, raw_asset in enumerate(raw_assets):
            if not isinstance(raw_asset, dict):
                raise ValueError(f"assets[{index}] must be an object")
            registry.register(PlatformAssetDefinition.from_mapping(raw_asset))
        registry.validate_graph()
        return registry


__all__ = [
    "FRESHNESS_KINDS",
    "PLATFORM_ASSET_REGISTRY_SCHEMA",
    "PlatformAssetDefinition",
    "PlatformAssetRegistry",
]
