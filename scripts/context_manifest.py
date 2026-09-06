#!/usr/bin/env python3
"""Render an explicit, task-scoped context manifest for coding agents."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContractRoute:
    """One producer-to-consumer artifact boundary."""

    producer: str
    contract: str
    consumers: tuple[str, ...]
    test_command: str


@dataclass(frozen=True, slots=True)
class ContextManifest:
    """The bounded repositories and contracts needed for one work area."""

    area: str
    target_repository: str
    repositories: tuple[str, ...]
    direct_consumers: tuple[str, ...]
    default_context: tuple[str, ...]
    contracts: tuple[ContractRoute, ...]


_COMMON_CONTEXT = ("AGENTS.md", "docs/governance/agent-context-boundaries.md")

_MANIFESTS = {
    "data": ContextManifest(
        area="data",
        target_repository="quant-platform/data",
        repositories=("market-data-platform",),
        direct_consumers=(
            "alpha-research",
            "strategy-app",
            "strategy-pipeline",
        ),
        default_context=(*_COMMON_CONTEXT, "market-data-platform/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="market-data-platform",
                contract="metadata/current_assets/a_share_current.json",
                consumers=("alpha-research", "strategy-app", "strategy-pipeline"),
                test_command="pytest tests/test_artifact_contract_manifest.py -q",
            ),
            ContractRoute(
                producer="market-data-platform",
                contract="research_features.parquet",
                consumers=("alpha-research", "strategy-pipeline"),
                test_command="pytest market-data-platform/tests/test_research_features.py -q",
            ),
        ),
    ),
    "microstructure": ContextManifest(
        area="microstructure",
        target_repository="quant-platform/microstructure",
        repositories=("deep-learning-tick-data-prediction",),
        direct_consumers=("alpha-research",),
        default_context=(*_COMMON_CONTEXT, "deep-learning-tick-data-prediction/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="deep-learning-tick-data-prediction",
                contract="L2 prediction artifact",
                consumers=("alpha-research",),
                test_command=(
                    "pytest deep-learning-tick-data-prediction/"
                    "tests/test_research_prediction_contract.py -q"
                ),
            ),
        ),
    ),
    "alpha": ContextManifest(
        area="alpha",
        target_repository="quant-platform/alpha",
        repositories=("alpha-research",),
        direct_consumers=(
            "portfolio-backtester",
            "strategy-pipeline",
        ),
        default_context=(*_COMMON_CONTEXT, "alpha-research/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="alpha-research",
                contract="signals.parquet",
                consumers=("portfolio-backtester", "strategy-pipeline"),
                test_command="pytest alpha-research/tests/test_signal_artifact.py -q",
            ),
            ContractRoute(
                producer="alpha-research",
                contract="signals.meta.json",
                consumers=("portfolio-backtester", "strategy-pipeline"),
                test_command="pytest tests/test_artifact_contract_manifest.py -q",
            ),
        ),
    ),
    "portfolio": ContextManifest(
        area="portfolio",
        target_repository="quant-platform/portfolio",
        repositories=("portfolio-backtester",),
        direct_consumers=("strategy-pipeline",),
        default_context=(*_COMMON_CONTEXT, "portfolio-backtester/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="alpha-research",
                contract="signals.parquet",
                consumers=("portfolio-backtester",),
                test_command="pytest alpha-research/tests/test_signal_artifact.py -q",
            ),
            ContractRoute(
                producer="portfolio-backtester",
                contract="positions_by_rebalance.csv",
                consumers=("strategy-pipeline",),
                test_command="pytest portfolio-backtester/tests/test_position_outputs.py -q",
            ),
        ),
    ),
    "strategy": ContextManifest(
        area="strategy",
        target_repository="quant-research",
        repositories=("strategy-research", "strategy-app"),
        direct_consumers=("strategy-pipeline",),
        default_context=(
            *_COMMON_CONTEXT,
            "strategy-research/AGENTS.md",
            "strategy-app/AGENTS.md",
        ),
        contracts=(
            ContractRoute(
                producer="strategy-research",
                contract="catalog.json",
                consumers=("strategy-app", "strategy-pipeline"),
                test_command="pytest strategy-research/tests/test_root_layout.py -q",
            ),
        ),
    ),
    "orchestration": ContextManifest(
        area="orchestration",
        target_repository="quant-platform/orchestration",
        repositories=("strategy-pipeline",),
        direct_consumers=("strategy-research", "quant-execution-engine", "market-intel"),
        default_context=(*_COMMON_CONTEXT, "strategy-pipeline/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="strategy-pipeline",
                contract="research-run.manifest.json",
                consumers=("strategy-research", "research-workspace"),
                test_command="pytest strategy-pipeline/tests/control_plane/test_contracts.py -q",
            ),
            ContractRoute(
                producer="strategy-pipeline",
                contract="targets.json",
                consumers=("quant-execution-engine",),
                test_command="pytest strategy-pipeline/tests/control_plane/test_targets.py -q",
            ),
            ContractRoute(
                producer="strategy-pipeline",
                contract="watchlist_20.csv",
                consumers=("market-intel",),
                test_command="pytest tests/test_artifact_contract_manifest.py -q",
            ),
        ),
    ),
    "execution": ContextManifest(
        area="execution",
        target_repository="quant-platform/execution",
        repositories=("quant-execution-engine",),
        direct_consumers=(),
        default_context=(*_COMMON_CONTEXT, "quant-execution-engine/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="strategy-pipeline",
                contract="targets.json",
                consumers=("quant-execution-engine",),
                test_command=(
                    "pytest quant-execution-engine/tests/unit/test_targets_contract.py -q"
                ),
            ),
        ),
    ),
    "market-intel": ContextManifest(
        area="market-intel",
        target_repository="market-intel",
        repositories=("market-intel",),
        direct_consumers=(),
        default_context=(*_COMMON_CONTEXT, "external checkout: market-intel/AGENTS.md"),
        contracts=(
            ContractRoute(
                producer="strategy-pipeline",
                contract="watchlist_20.csv",
                consumers=("market-intel",),
                test_command="pytest tests/test_artifact_contract_manifest.py -q",
            ),
        ),
    ),
}


def available_areas() -> tuple[str, ...]:
    """Return task areas in stable display order."""

    return tuple(_MANIFESTS)


def build_manifest(area: str) -> ContextManifest:
    """Return the explicit context manifest for one work area."""

    try:
        return _MANIFESTS[area]
    except KeyError as error:
        choices = ", ".join(available_areas())
        raise ValueError(f"unknown task area {area!r}; choose one of: {choices}") from error


def render_manifest(manifest: ContextManifest) -> str:
    """Render the manifest as agent-readable Markdown."""

    lines = [f"# Task context: {manifest.area}", "", "## Target repository"]
    lines.append(f"- `{manifest.target_repository}`")
    lines.extend(("", "## Default context"))
    lines.extend(f"- `{path}`" for path in manifest.default_context)
    lines.extend(("", "## Repositories"))
    lines.extend(f"- `{repository}`" for repository in manifest.repositories)
    lines.extend(("", "## Direct consumers"))
    lines.extend(f"- `{consumer}`" for consumer in manifest.direct_consumers)
    lines.extend(("", "## Contract routes"))
    for route in manifest.contracts:
        lines.append(f"- Producer: `{route.producer}`")
        lines.append(f"  - Contract: `{route.contract}`")
        lines.extend(f"  - Consumer: `{consumer}`" for consumer in route.consumers)
        lines.append(f"  - Test: `{route.test_command}`")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, choices=available_areas())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(render_manifest(build_manifest(args.task)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
