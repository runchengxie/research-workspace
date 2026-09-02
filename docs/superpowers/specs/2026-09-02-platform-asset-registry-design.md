# Platform Asset Registry Design

## Goal

Represent the logical cross-repository data/research/publication graph without introducing a nested superproject or another orchestration control plane.

## Design

A `PlatformAssetDefinition` owns identity, owner repository, output schema, internal dependencies, external inputs, consumers, and a small freshness policy. `PlatformAssetRegistry` validates missing dependencies and cycles and yields a deterministic topological order.

The registry describes what depends on what. It does not execute assets, clone repositories, schedule jobs, or replace existing owner-specific quality gates.
