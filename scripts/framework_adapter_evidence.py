#!/usr/bin/env python3
"""Validate framework-neutral Qlib/backtest/vn.py integration evidence.

The workspace deliberately validates persisted JSON receipts instead of importing
optional framework runtimes.  Producers remain responsible for replaying their own
evidence before handing the receipt to this release gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from framework_adapter_execution_evidence import (
    RECOVERY_SCENARIOS as RECOVERY_SCENARIOS,
)
from framework_adapter_execution_evidence import validate_execution_evidence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_MANIFEST = ROOT / "docs" / "framework-adapter-release.yml"
ALPHA_SCHEMA = "backend_comparison_replay_receipt.v1"
BACKTEST_SCHEMA = "backtest_differential.v1"
ENVELOPE_SCHEMA = "framework_adapter_integration_evidence.v1"

BACKTEST_DIMENSIONS = {"dates", "positions", "turnover", "cost", "pnl"}
EXPECTED_RELEASE_COMPONENTS = {
    "market-data-platform",
    "alpha-research",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
}
FORBIDDEN_TYPE_PREFIXES = ("qlib.", "vnpy.", "QuantConnect.")


class EvidenceError(ValueError):
    """Raised when an evidence file is missing or is not a JSON object."""


def _load_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EvidenceError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidenceError(f"{path} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_commit(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _release_binding(path: Path) -> dict[str, Any]:
    payload = _load_mapping(path)
    if payload.get("schema_version") != "framework_adapter_release.v1":
        raise EvidenceError("release manifest schema must be framework_adapter_release.v1")
    release_id = payload.get("release_id")
    if not isinstance(release_id, str) or not release_id:
        raise EvidenceError("release manifest must contain a non-empty release_id")
    raw_components = payload.get("components")
    if not isinstance(raw_components, list):
        raise EvidenceError("release manifest components must be a list")
    components: dict[str, str] = {}
    for raw in raw_components:
        if not isinstance(raw, Mapping):
            raise EvidenceError("release manifest components must be objects")
        component = cast(Mapping[str, Any], raw)
        repository = component.get("repository")
        commit = (
            component.get("merged_commit")
            if component.get("merge_state") == "merged"
            else component.get("candidate_commit")
        )
        if not isinstance(repository, str) or repository in components:
            raise EvidenceError("release manifest repositories must be unique strings")
        if not _is_commit(commit):
            raise EvidenceError(f"{repository}: release evidence commit must be a full Git SHA")
        components[repository] = cast(str, commit)
    if set(components) != EXPECTED_RELEASE_COMPONENTS:
        raise EvidenceError("release manifest must contain the five framework adapter owners")
    return {
        "release_id": release_id,
        "components": dict(sorted(components.items())),
    }


def _walk_strings(value: Any, path: str = "$") -> list[tuple[str, str]]:
    strings: list[tuple[str, str]] = []
    if isinstance(value, str):
        strings.append((path, value))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            strings.extend(_walk_strings(item, f"{path}.{key}"))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            strings.extend(_walk_strings(item, f"{path}[{index}]"))
    return strings


def _framework_type_issues(payload: Mapping[str, Any], label: str) -> list[str]:
    issues: list[str] = []
    for path, value in _walk_strings(payload):
        if value.startswith(FORBIDDEN_TYPE_PREFIXES):
            issues.append(f"{label}: framework runtime type leaked at {path}: {value}")
    return issues


def _alpha_header_issues(payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema") != ALPHA_SCHEMA:
        issues.append(f"alpha: schema must be {ALPHA_SCHEMA}")
    if payload.get("replay_verified") is not True:
        issues.append("alpha: owner replay receipt must set replay_verified=true")
    if payload.get("source_schema") != "backend_comparison.v1":
        issues.append("alpha: source_schema must be backend_comparison.v1")
    if payload.get("verification_method") != "artifact-digest-and-decision-replay":
        issues.append("alpha: verification method must replay artifact digests and decision")
    if not isinstance(payload.get("thresholds"), Mapping):
        issues.append("alpha: replay receipt thresholds must be an object")
    return issues


def _alpha_decision_issues(decision: object) -> list[str]:
    if not isinstance(decision, Mapping):
        return ["alpha: decision must be an object"]
    issues: list[str] = []
    if decision.get("status") != "promotable":
        issues.append("alpha: backend comparison is not promotable")
    if decision.get("failures") != []:
        issues.append("alpha: backend comparison failures must be empty")
    return issues


def _alpha_source_issues(payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    source_digest = payload.get("source_report_sha256")
    if not _is_sha256(source_digest):
        issues.append("alpha: source report SHA-256 is missing")
    source_report = payload.get("source_report")
    if not isinstance(source_report, Mapping):
        return [*issues, "alpha: source_report handle must be an object"]
    if source_report.get("artifact_type") != "backend_comparison":
        issues.append("alpha: source report artifact_type must be backend_comparison")
    if source_report.get("schema_version") != "v1":
        issues.append("alpha: source report schema_version must be v1")
    if source_report.get("sha256") != source_digest:
        issues.append("alpha: source report handle digest does not match receipt digest")
    return issues


def _alpha_comparison_issues(comparison: object) -> list[str]:
    if not isinstance(comparison, Mapping):
        return ["alpha: comparison must be an object"]
    issues: list[str] = []
    if comparison.get("native_backend_id") != "native":
        issues.append("alpha: reference backend must be native")
    if comparison.get("candidate_backend_id") != "qlib":
        issues.append("alpha: candidate backend must be qlib")
    return issues


def validate_alpha_evidence(payload: Mapping[str, Any]) -> list[str]:
    issues = _framework_type_issues(payload, "alpha")
    issues.extend(_alpha_header_issues(payload))
    decision = payload.get("decision")
    issues.extend(_alpha_decision_issues(decision))
    issues.extend(_alpha_source_issues(payload))
    issues.extend(_alpha_comparison_issues(payload.get("comparison")))
    return issues


def _index_comparisons(
    comparisons: list[object],
    *,
    label: str,
    key: str,
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    by_dimension: dict[str, Mapping[str, Any]] = {}
    issues: list[str] = []
    for item in comparisons:
        if not isinstance(item, Mapping) or not isinstance(item.get(key), str):
            issues.append(f"{label}: every item must have a string {key}")
            continue
        typed_item = cast(Mapping[str, Any], item)
        dimension = str(typed_item[key])
        if dimension in by_dimension:
            issues.append(f"{label}: duplicate {key} {dimension}")
        by_dimension[dimension] = typed_item
    return by_dimension, issues


def _backtest_item_issues(dimension: str, item: Mapping[str, Any]) -> list[str]:
    status = item.get("status")
    if status not in {"matched", "explained"}:
        return [f"backtest: {dimension} is neither matched nor explained"]
    if status != "explained":
        return []
    explanation = item.get("explanation")
    required = ("code", "detail")
    if isinstance(explanation, Mapping) and all(
        isinstance(explanation.get(field), str) and explanation.get(field) for field in required
    ):
        return []
    return [f"backtest: {dimension} explanation is missing"]


def validate_backtest_evidence(payload: Mapping[str, Any]) -> list[str]:
    issues = _framework_type_issues(payload, "backtest")
    if payload.get("schema") != BACKTEST_SCHEMA:
        issues.append(f"backtest: schema must be {BACKTEST_SCHEMA}")
    if payload.get("accepted") is not True:
        issues.append("backtest: differential report must be accepted")
    if payload.get("reference_backend") != "native-a-share-replay":
        issues.append("backtest: reference_backend must be native-a-share-replay")
    if payload.get("candidate_backend") != "qlib-backtest":
        issues.append("backtest: candidate_backend must be qlib-backtest")
    comparisons = payload.get("comparisons")
    if not isinstance(comparisons, list):
        return [*issues, "backtest: comparisons must be a list"]
    by_dimension, index_issues = _index_comparisons(
        comparisons,
        label="backtest",
        key="dimension",
    )
    issues.extend(index_issues)
    if set(by_dimension) != BACKTEST_DIMENSIONS:
        issues.append(
            "backtest: dimensions must be exactly " + ", ".join(sorted(BACKTEST_DIMENSIONS))
        )
    for dimension, item in by_dimension.items():
        issues.extend(_backtest_item_issues(dimension, item))
    return issues


def build_evidence_envelope(
    alpha_path: Path,
    backtest_path: Path,
    execution_path: Path,
    release_manifest_path: Path,
) -> dict[str, Any]:
    paths = {
        "alpha": alpha_path.resolve(),
        "backtest": backtest_path.resolve(),
        "execution": execution_path.resolve(),
    }
    payloads = {name: _load_mapping(path) for name, path in paths.items()}
    release = _release_binding(release_manifest_path.resolve())
    issues = [
        *validate_alpha_evidence(payloads["alpha"]),
        *validate_backtest_evidence(payloads["backtest"]),
        *validate_execution_evidence(payloads["execution"]),
    ]
    return {
        "schema": ENVELOPE_SCHEMA,
        "status": "accepted" if not issues else "rejected",
        "issues": issues,
        "release": release,
        "evidence": {
            name: {
                "name": path.name,
                "sha256": _sha256(path),
                "schema": payloads[name].get("schema"),
            }
            for name, path in paths.items()
        },
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alpha", type=Path, required=True, help="Replayed alpha comparison JSON.")
    parser.add_argument("--backtest", type=Path, required=True, help="Backtest differential JSON.")
    parser.add_argument("--execution", type=Path, required=True, help="Recovery matrix JSON.")
    parser.add_argument(
        "--release-manifest",
        type=Path,
        default=DEFAULT_RELEASE_MANIFEST,
        help="Release manifest whose candidate/merged commits are bound into the envelope.",
    )
    parser.add_argument("--output", type=Path, help="Optional integration evidence output path.")
    args = parser.parse_args(argv)

    try:
        envelope = build_evidence_envelope(
            args.alpha,
            args.backtest,
            args.execution,
            args.release_manifest,
        )
    except EvidenceError as exc:
        print(json.dumps({"schema": ENVELOPE_SCHEMA, "status": "error", "error": str(exc)}))
        return 2
    if args.output is not None:
        _write_json(args.output, envelope)
    print(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if envelope["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
