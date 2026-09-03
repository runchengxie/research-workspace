"""Build lineage payloads and artifact envelopes for execution targets."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

from .artifact_envelope import ArtifactEnvelopeV2, LineageInput, ProducerIdentity
from .file_receipts import canonical_json_sha256, file_sha256

PRODUCER_REPOSITORY = "strategy-pipeline"
PRODUCER_BACKEND = "export_targets"
TARGET_CONTRACT = "quant-execution-engine.targets/v2"


def _producer_version() -> str:
    try:
        return package_version(PRODUCER_REPOSITORY)
    except PackageNotFoundError:
        return "0.0.0"


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def lineage_inputs(*, run_dir: Path, holdings_payload: dict[str, Any]) -> list[LineageInput]:
    inputs: list[LineageInput] = []
    for name in ("summary.json", "config.used.yml", "inputs.lock.json"):
        candidate = run_dir / name
        if candidate.exists():
            inputs.append(
                LineageInput(
                    artifact_id=f"strategy-pipeline.run:{name}",
                    sha256=file_sha256(candidate),
                )
            )
    positions_file = holdings_payload.get("positions_file")
    if isinstance(positions_file, str) and Path(positions_file).exists():
        inputs.append(
            LineageInput(
                artifact_id="strategy-pipeline.run:positions_file",
                sha256=file_sha256(Path(positions_file)),
            )
        )
    return inputs


def lineage_payload(
    *,
    holdings_payload: dict[str, Any],
    targets_path: Path,
    target_source: str,
    target_gross_exposure: float,
    weight_sum: float,
    target_count: int,
    markets: str,
    run_dir: Path,
    fail_on_quality: str | None,
    target_pruning: dict[str, object],
) -> dict[str, object]:
    upstream_files: dict[str, str] = {}
    summary_payload: dict[str, Any] = {}
    for name in ("summary.json", "config.used.yml", "inputs.lock.json"):
        candidate = run_dir / name
        if candidate.exists():
            upstream_files[name] = str(candidate)
            if name == "summary.json":
                loaded = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    summary_payload = loaded
    strategy_payload: dict[str, Any] = {}
    positions = summary_payload.get("positions")
    if isinstance(positions, dict) and isinstance(positions.get("strategy"), dict):
        strategy_payload = dict(positions["strategy"])
    elif isinstance(summary_payload.get("backtest"), dict) and isinstance(
        summary_payload["backtest"].get("strategy"), dict
    ):
        strategy_payload = dict(summary_payload["backtest"]["strategy"])
    signals = summary_payload.get("signals")
    canonical_signals = (
        signals.get("canonical")
        if isinstance(signals, dict) and isinstance(signals.get("canonical"), dict)
        else {}
    )
    return {
        "schema_version": 1,
        "artifact_type": "strategy_pipeline.execution_targets_lineage",
        "target_contract": TARGET_CONTRACT,
        "targets_file": str(targets_path),
        "generated_at": datetime.now(UTC).isoformat(),
        "target_source": target_source,
        "target_gross_exposure": target_gross_exposure,
        "selection": {
            "as_of": holdings_payload.get("as_of"),
            "entry_date": holdings_payload.get("entry_date"),
            "signal_asof": holdings_payload.get("signal_asof"),
            "data_end_date": holdings_payload.get("data_end_date"),
            "market": markets,
            "source": holdings_payload.get("source"),
            "run_dir": str(run_dir),
            "positions_file": holdings_payload.get("positions_file"),
            "target_count": target_count,
            "weight_sum": weight_sum,
        },
        "quality_gate": {"checked": True, "fail_on_quality_override": fail_on_quality},
        "target_pruning": target_pruning,
        "strategy": strategy_payload,
        "signals": canonical_signals,
        "upstream_files": upstream_files,
    }


def targets_envelope_v2(
    *, run_id: str, targets_path: Path, configuration: dict[str, Any], lineage: list[LineageInput]
) -> ArtifactEnvelopeV2:
    return ArtifactEnvelopeV2(
        artifact_id=f"targets:{run_id}",
        artifact_type="targets.json",
        run_id=run_id,
        created_at=datetime.now(UTC),
        producer=ProducerIdentity(
            repository=PRODUCER_REPOSITORY,
            version=_producer_version(),
            commit=_git_commit(),
            backend=PRODUCER_BACKEND,
        ),
        configuration_sha256=canonical_json_sha256(configuration),
        content_sha256=file_sha256(targets_path),
        lineage=tuple(lineage),
    )


__all__ = ["lineage_inputs", "lineage_payload", "targets_envelope_v2"]
