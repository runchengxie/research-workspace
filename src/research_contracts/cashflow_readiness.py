"""Fail-closed readiness contract for the cashflow strategy candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .promotion_evidence_checks import check_errors

CASHFLOW_GRAY_GATES = (
    "pit",
    "walk_forward",
    "benchmark_matrix",
    "cost",
    "final_oos",
    "cpcv",
    "regime",
    "capacity",
)
READINESS_BLOCKED_EXIT = 20


@dataclass(frozen=True)
class CashflowReadinessDecision:
    """The only promotion decision consumable by later runtime layers."""

    strategy_id: str
    decision: str
    eligible_for_gray_push: bool
    production_eligible: bool
    failed_gates: tuple[str, ...]
    evidence_refs: tuple[str, ...]


def _checks(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    checks = payload.get("checks")
    if not isinstance(checks, Mapping):
        raise ValueError("cashflow readiness payload requires a checks mapping")
    return checks


def _outcome(checks: Mapping[str, Any], gate: str) -> tuple[bool, str | None]:
    entry = checks.get(gate)
    if not isinstance(entry, Mapping):
        return False, None
    if str(entry.get("outcome") or "").strip().lower() != "pass":
        return False, None
    # An outcome label alone is not evidence. Reuse the canonical field-level
    # validators so a hand-edited or underspecified "pass" cannot authorize a
    # gray publication.
    normalized = {**dict(entry), "status": "passed"}
    if check_errors({"checks": {gate: normalized}}, gate):
        return False, None
    evidence = str(entry.get("evidence") or "").strip()
    return True, evidence or None


def _evidence_attestation_passes(payload: Mapping[str, Any]) -> bool:
    attestation = payload.get("evidence_attestation")
    if not isinstance(attestation, Mapping):
        return False
    digest = str(attestation.get("bundle_sha256") or "")
    return (
        attestation.get("status") == "verified"
        and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
    )


def evaluate_cashflow_readiness(
    payload: Mapping[str, Any], *, require_production: bool = False
) -> CashflowReadinessDecision:
    """Evaluate research evidence without ever granting production eligibility."""

    if not isinstance(payload, Mapping):
        raise ValueError("cashflow readiness payload must be a mapping")
    checks = _checks(payload)
    failed: list[str] = []
    evidence_refs: list[str] = []
    for gate in CASHFLOW_GRAY_GATES:
        passed, evidence = _outcome(checks, gate)
        if not passed:
            failed.append(gate)
        elif evidence is not None:
            evidence_refs.append(evidence)

    gray_ready = not failed
    if not _evidence_attestation_passes(payload):
        failed.append("evidence_integrity")
        gray_ready = False
    if require_production:
        failed.append("production_authorization")

    return CashflowReadinessDecision(
        strategy_id=str(payload.get("strategy_id") or "cashflow_quality_top50_v1"),
        decision=(
            "candidate_for_gray_push"
            if gray_ready and not require_production
            else "continue_shadow"
        ),
        eligible_for_gray_push=gray_ready,
        production_eligible=False,
        failed_gates=tuple(failed),
        evidence_refs=tuple(evidence_refs),
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_artifacts_pass(bundle: Mapping[str, Any], *, root: Path) -> tuple[bool, list[str]]:
    declared = bundle.get("source_artifacts")
    if declared is None:
        return True, []
    if not isinstance(declared, list):
        return False, ["source_artifacts_not_a_list"]
    errors: list[str] = []
    for index, item in enumerate(declared):
        if not isinstance(item, Mapping):
            errors.append(f"source_artifacts[{index}]:not_an_object")
            continue
        raw_path = str(item.get("path") or "")
        expected = str(item.get("sha256") or "")
        if not raw_path or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            errors.append(f"source_artifacts[{index}]:invalid_identity")
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            errors.append(f"source_artifacts[{index}]:missing:{raw_path}")
            continue
        if _file_sha256(path) != expected:
            errors.append(f"source_artifacts[{index}]:hash_mismatch:{raw_path}")
    return not errors, errors


def _runtime_evidence_bundle(
    bundle: Mapping[str, Any], *, pit_audit_path: str | Path | None
) -> dict[str, Any]:
    checks = bundle.get("checks")
    if not isinstance(checks, Mapping):
        raise ValueError("cashflow evidence bundle requires a checks mapping")
    effective_checks = {str(name): dict(value) for name, value in checks.items()}
    effective_source_artifacts = [
        dict(item) for item in bundle.get("source_artifacts", []) if isinstance(item, Mapping)
    ]
    if pit_audit_path is None:
        return {
            **dict(bundle),
            "checks": effective_checks,
            "source_artifacts": effective_source_artifacts,
        }
    current_pit = Path(pit_audit_path).expanduser().resolve()
    audit = json.loads(current_pit.read_text(encoding="utf-8"))
    if not isinstance(audit, Mapping):
        raise ValueError("runtime PIT audit must be a mapping")
    pit_check = dict(effective_checks.get("pit") or {})
    previous_evidence = str(pit_check.get("evidence") or "")
    pit_check["evidence"] = str(current_pit)
    if audit.get("status") != "passed" or audit.get("historical_revision_safe") is not True:
        pit_check["outcome"] = "partial"
        blockers = audit.get("blockers") or ["runtime_pit_audit_failed"]
        pit_check["detail"] = "runtime PIT audit blocked: " + ", ".join(map(str, blockers))
    effective_checks["pit"] = pit_check
    replacement = next(
        (
            item
            for item in effective_source_artifacts
            if str(item.get("path") or "") == previous_evidence
        ),
        None,
    )
    if replacement is None:
        replacement = {"path": str(current_pit), "sha256": ""}
        effective_source_artifacts.append(replacement)
    replacement["path"] = str(current_pit)
    replacement["sha256"] = _file_sha256(current_pit)
    return {
        **dict(bundle),
        "checks": effective_checks,
        "source_artifacts": effective_source_artifacts,
    }


def build_cashflow_readiness_payload(
    evidence_bundle_path: str | Path,
    *,
    root: str | Path,
    pit_audit_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a runtime readiness receipt from one evidence bundle.

    Evidence is attested only when every gray gate is passing and each declared
    evidence path exists under ``root`` (or is an existing absolute path).
    """
    bundle_path = Path(evidence_bundle_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, Mapping):
        raise ValueError("cashflow evidence bundle must be a mapping")
    effective_bundle = _runtime_evidence_bundle(bundle, pit_audit_path=pit_audit_path)
    effective_checks = effective_bundle["checks"]
    root_path = Path(root)
    evidence_complete = True
    for gate in CASHFLOW_GRAY_GATES:
        entry = effective_checks.get(gate)
        if not isinstance(entry, Mapping) or entry.get("outcome") != "pass":
            evidence_complete = False
            continue
        evidence = str(entry.get("evidence") or "")
        evidence_path = Path(evidence)
        if not evidence_path.is_absolute():
            evidence_path = root_path / evidence_path
        if not evidence_path.is_file():
            evidence_complete = False
    source_artifacts_valid, source_artifact_errors = _source_artifacts_pass(
        effective_bundle, root=root_path
    )
    evidence_complete = evidence_complete and source_artifacts_valid
    attestation = {
        "status": "verified" if evidence_complete else "unverified",
        "bundle_sha256": _file_sha256(bundle_path),
        "source_artifact_count": len(bundle.get("source_artifacts") or [])
        if isinstance(bundle.get("source_artifacts"), list)
        else 0,
        "source_artifact_errors": source_artifact_errors,
    }
    payload: dict[str, Any] = {
        "schema_version": "cashflow_readiness.v1",
        "strategy_id": str(bundle.get("strategy_id") or "cashflow_quality_top50_v1"),
        "checks": effective_checks,
        "evidence_attestation": attestation,
    }
    decision = evaluate_cashflow_readiness(payload)
    payload.update(
        {
            "decision": decision.decision,
            "eligible_for_gray_push": decision.eligible_for_gray_push,
            "production_eligible": decision.production_eligible,
            "failed_gates": list(decision.failed_gates),
            "evidence_refs": list(decision.evidence_refs),
        }
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m research_contracts.cashflow_readiness")
    parser.add_argument("--evidence-bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pit-audit", type=Path)
    args = parser.parse_args(argv)
    payload = build_cashflow_readiness_payload(
        args.evidence_bundle,
        root=args.root,
        pit_audit_path=args.pit_audit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["eligible_for_gray_push"] else READINESS_BLOCKED_EXIT


__all__ = [
    "CASHFLOW_GRAY_GATES",
    "READINESS_BLOCKED_EXIT",
    "CashflowReadinessDecision",
    "build_cashflow_readiness_payload",
    "evaluate_cashflow_readiness",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
