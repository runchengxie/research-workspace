# Platform Asset Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Add a machine-readable logical platform dependency graph without changing Git repository nesting.

**Spec:** `docs/superpowers/specs/2026-09-02-platform-asset-registry-design.md`

- [x] Add tests for a representative research flow, missing dependencies, cycles, and invalid freshness policy.
- [ ] Run focused tests and confirm RED before implementation.
- [x] Implement `PlatformAssetDefinition` and `PlatformAssetRegistry` with graph validation/topological ordering.
- [x] Document the distinction between logical asset graph and Git superproject/orchestrator.
- [ ] Run `uv run --project strategy-pipeline --extra dev python -m pytest tests/test_platform_asset_registry.py -q`.
- [ ] Run workspace hard/smoke contract gates.
