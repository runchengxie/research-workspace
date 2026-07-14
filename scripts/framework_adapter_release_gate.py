#!/usr/bin/env python3
"""Enforce merge-before-pin policy for the framework-adapter release train."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "framework-adapter-release.yml"
SCHEMA = "framework_adapter_release.v1"
EXPECTED_COMPONENTS = {
    "market-data-platform",
    "alpha-research",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
}
MERGE_STATES = {"draft", "open", "merged"}
RELEASE_STATES = {"blocked_on_downstream_merge", "ready_to_validate", "verified"}
EVIDENCE_STATES = {"pending", "accepted"}
EVIDENCE_SCHEMA = "framework_adapter_integration_evidence.v1"
EVIDENCE_SOURCE_SCHEMAS = {
    "alpha": "backend_comparison_replay_receipt.v1",
    "backtest": "backtest_differential.v1",
    "execution": "execution_recovery_matrix.v1",
}
REQUIRED_VERIFIED_PATHS = (
    "alpha-research/src/alpha_research/research_artifacts.py",
    "quant-execution-engine/src/quant_execution_engine/domain.py",
)


@dataclass(frozen=True)
class ComponentCheck:
    """Normalized component result used by the release-level gate."""

    repository: str | None
    report: dict[str, Any] | None
    issues: tuple[str, ...]


def _is_commit(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _gitlink_commit(root: Path, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "ls-tree", "HEAD", "--", path],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    fields = completed.stdout.split()
    if len(fields) < 3 or fields[0] != "160000":
        return None
    return fields[2]


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("release manifest must contain an object")
    return payload


def _manifest_issues(payload: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != SCHEMA:
        issues.append(f"schema_version must be {SCHEMA}")
    if payload.get("pin_policy") != "after_downstream_merge_only":
        issues.append("pin_policy must be after_downstream_merge_only")
    release_state = payload.get("status")
    if release_state not in RELEASE_STATES:
        issues.append("release status is invalid")
    evidence_state = payload.get("evidence_status")
    if evidence_state not in EVIDENCE_STATES:
        issues.append("evidence_status must be pending or accepted")
    if not isinstance(payload.get("release_id"), str) or not payload.get("release_id"):
        issues.append("release_id must be non-empty")
    evidence = payload.get("integration_evidence")
    if not isinstance(evidence, Mapping):
        issues.append("integration_evidence must be an object")
    else:
        evidence_path = evidence.get("path")
        if not isinstance(evidence_path, str) or not evidence_path:
            issues.append("integration_evidence.path must be non-empty")
        evidence_digest = evidence.get("sha256")
        if evidence_digest is not None and not _is_sha256(evidence_digest):
            issues.append("integration_evidence.sha256 must be null or a lowercase SHA-256")
        if evidence_state == "accepted" and not _is_sha256(evidence_digest):
            issues.append("accepted evidence requires integration_evidence.sha256")
    return issues


def _component_metadata_issues(repository: str, raw: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    merge_state = raw.get("merge_state")
    if merge_state not in MERGE_STATES:
        issues.append(f"{repository}: invalid merge_state")
    for field in ("branch", "pr_url"):
        value = raw.get(field)
        if not isinstance(value, str) or not value:
            issues.append(f"{repository}: {field} must be non-empty")
    pr_url = raw.get("pr_url")
    if isinstance(pr_url, str) and not pr_url.startswith("https://github.com/"):
        issues.append(f"{repository}: pr_url must be a GitHub HTTPS URL")
    if not _is_commit(raw.get("candidate_commit")):
        issues.append(f"{repository}: candidate_commit must be a full lowercase Git SHA")
    if not _is_commit(raw.get("baseline_commit")):
        issues.append(f"{repository}: baseline_commit must be a full lowercase Git SHA")
    if merge_state == "merged" and not _is_commit(raw.get("merged_commit")):
        issues.append(f"{repository}: merged_commit must be a full lowercase Git SHA")
    return issues


def _component_pin_issues(
    repository: str,
    raw: Mapping[str, Any],
    pinned_commit: str | None,
) -> list[str]:
    issues: list[str] = []
    merge_state = raw.get("merge_state")
    if merge_state != "merged" and pinned_commit != raw.get("baseline_commit"):
        issues.append(f"{repository}: gitlink changed before downstream merge")
    merged_commit = raw.get("merged_commit")
    if merge_state == "merged" and pinned_commit != merged_commit:
        issues.append(f"{repository}: gitlink does not match merged_commit")
    return issues


def _check_component(root: Path, raw: object) -> ComponentCheck:
    if not isinstance(raw, Mapping):
        return ComponentCheck(None, None, ("every component must be an object",))
    repository = raw.get("repository")
    if not isinstance(repository, str) or not repository:
        return ComponentCheck(None, None, ("every component must name a repository",))
    typed_raw = cast(Mapping[str, Any], raw)
    issues = _component_metadata_issues(repository, typed_raw)
    pinned_commit = _gitlink_commit(root, repository)
    issues.extend(_component_pin_issues(repository, typed_raw, pinned_commit))
    merged_commit = typed_raw.get("merged_commit")
    report = {
        "repository": repository,
        "merge_state": typed_raw.get("merge_state"),
        "pr_url": typed_raw.get("pr_url"),
        "candidate_commit": typed_raw.get("candidate_commit"),
        "baseline_commit": typed_raw.get("baseline_commit"),
        "merged_commit": merged_commit,
        "pinned_commit": pinned_commit,
        "pinned": isinstance(merged_commit, str) and pinned_commit == merged_commit,
    }
    return ComponentCheck(repository, report, tuple(issues))


def _component_set_issues(seen: set[str]) -> list[str]:
    issues: list[str] = []
    missing = sorted(EXPECTED_COMPONENTS - seen)
    extra = sorted(seen - EXPECTED_COMPONENTS)
    if missing:
        issues.append("missing components: " + ", ".join(missing))
    if extra:
        issues.append("unexpected components: " + ", ".join(extra))
    return issues


def _release_state_issues(
    release_state: object,
    evidence_state: object,
    *,
    all_merged: bool,
    all_pinned: bool,
) -> list[str]:
    issues: list[str] = []
    if release_state == "blocked_on_downstream_merge" and all_merged:
        issues.append("release status is stale: all downstream components are merged")
    if release_state in {"ready_to_validate", "verified"} and not all_merged:
        issues.append("release cannot advance before every downstream PR is merged")
    if release_state == "verified" and not all_pinned:
        issues.append("verified release must pin every merged component")
    if release_state == "verified" and evidence_state != "accepted":
        issues.append("verified release requires accepted integration evidence")
    if evidence_state == "accepted" and not all_merged:
        issues.append("integration evidence cannot be accepted before every downstream merge")
    return issues


def _safe_evidence_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    resolved_root = root.resolve()
    candidate = (resolved_root / value).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None
    return candidate


def _evidence_binding_issues(
    root: Path,
    payload: Mapping[str, Any],
    components: list[dict[str, Any]],
) -> list[str]:
    release_state = payload.get("status")
    evidence_state = payload.get("evidence_status")
    if evidence_state != "accepted" and release_state != "verified":
        return []
    integration_evidence = payload.get("integration_evidence")
    if not isinstance(integration_evidence, Mapping):
        return ["accepted integration evidence metadata is missing"]
    envelope, load_issues = _load_evidence_envelope(root, integration_evidence)
    if envelope is None:
        return load_issues
    return [*load_issues, *_envelope_binding_issues(payload, components, envelope)]


def _load_evidence_envelope(
    root: Path,
    integration_evidence: Mapping[object, object],
) -> tuple[Mapping[str, Any] | None, list[str]]:
    evidence_path = _safe_evidence_path(root, integration_evidence.get("path"))
    if evidence_path is None:
        return None, ["integration evidence path must stay inside the workspace"]
    if not evidence_path.is_file():
        return None, ["integration evidence file does not exist"]
    expected_digest = integration_evidence.get("sha256")
    if not _is_sha256(expected_digest) or _sha256(evidence_path) != expected_digest:
        return None, ["integration evidence SHA-256 does not match the manifest"]
    try:
        envelope = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"integration evidence cannot be loaded: {exc}"]
    if not isinstance(envelope, Mapping):
        return None, ["integration evidence must contain an object"]
    return cast(Mapping[str, Any], envelope), []


def _envelope_binding_issues(
    payload: Mapping[str, Any],
    components: list[dict[str, Any]],
    envelope: Mapping[str, Any],
) -> list[str]:
    issues = _envelope_header_issues(envelope)
    issues.extend(_envelope_source_issues(envelope.get("evidence")))
    release = envelope.get("release")
    if not isinstance(release, Mapping):
        return [*issues, "integration evidence release binding is missing"]
    if set(release) != {"release_id", "components"}:
        issues.append("integration evidence release binding keys are invalid")
    if release.get("release_id") != payload.get("release_id"):
        issues.append("integration evidence release_id does not match")
    expected_commits = {
        item["repository"]: item["merged_commit"]
        for item in components
        if isinstance(item.get("merged_commit"), str)
    }
    if release.get("components") != expected_commits:
        issues.append("integration evidence component commits do not match merged commits")
    return issues


def _envelope_header_issues(envelope: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if set(envelope) != {"schema", "status", "issues", "release", "evidence"}:
        issues.append("integration evidence envelope keys are invalid")
    if envelope.get("schema") != EVIDENCE_SCHEMA or envelope.get("status") != "accepted":
        issues.append("integration evidence envelope is not accepted")
    if envelope.get("issues") != []:
        issues.append("accepted integration evidence must have no issues")
    return issues


def _envelope_source_issues(value: object) -> list[str]:
    if not isinstance(value, Mapping) or set(value) != set(EVIDENCE_SOURCE_SCHEMAS):
        return ["integration evidence owner receipts are incomplete"]
    issues: list[str] = []
    for owner, expected_schema in EVIDENCE_SOURCE_SCHEMAS.items():
        descriptor = value.get(owner)
        if not isinstance(descriptor, Mapping):
            issues.append(f"integration evidence {owner} receipt descriptor is missing")
            continue
        if set(descriptor) != {"name", "sha256", "schema"}:
            issues.append(f"integration evidence {owner} receipt descriptor keys are invalid")
        if not isinstance(descriptor.get("name"), str) or not descriptor.get("name"):
            issues.append(f"integration evidence {owner} receipt name is missing")
        if not _is_sha256(descriptor.get("sha256")):
            issues.append(f"integration evidence {owner} receipt SHA-256 is invalid")
        if descriptor.get("schema") != expected_schema:
            issues.append(f"integration evidence {owner} receipt schema is invalid")
    return issues


def _verified_surface_issues(root: Path, release_state: object) -> list[str]:
    if release_state != "verified":
        return []
    missing = [relative for relative in REQUIRED_VERIFIED_PATHS if not (root / relative).is_file()]
    return [f"verified release is missing required contract surface: {path}" for path in missing]


def build_report(root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    issues = _manifest_issues(payload)

    raw_components = payload.get("components")
    if not isinstance(raw_components, list):
        issues.append("components must be a list")
        raw_components = []
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_components:
        checked = _check_component(root, raw)
        issues.extend(checked.issues)
        if checked.repository is None or checked.report is None:
            continue
        if checked.repository in seen:
            issues.append(f"{checked.repository}: duplicate component")
        seen.add(checked.repository)
        components.append(checked.report)

    issues.extend(_component_set_issues(seen))
    all_merged = len(components) == len(EXPECTED_COMPONENTS) and all(
        item["merge_state"] == "merged" for item in components
    )
    all_pinned = len(components) == len(EXPECTED_COMPONENTS) and all(
        item["pinned"] is True for item in components
    )
    release_state = payload.get("status")
    evidence_state = payload.get("evidence_status")
    issues.extend(
        _release_state_issues(
            release_state,
            evidence_state,
            all_merged=all_merged,
            all_pinned=all_pinned,
        )
    )
    issues.extend(_evidence_binding_issues(root, payload, components))
    issues.extend(_verified_surface_issues(root, release_state))

    blocked = release_state == "blocked_on_downstream_merge" and not all_merged
    return {
        "schema_version": "framework_adapter_release_gate.v1",
        "release_id": payload.get("release_id"),
        "status": "failed" if issues else ("blocked" if blocked else "passed"),
        "blocked_reason": "downstream PRs are not merged" if blocked else None,
        "issues": issues,
        "all_downstream_merged": all_merged,
        "all_merged_commits_pinned": all_pinned,
        "evidence_status": evidence_state,
        "components": components,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat a merge-gated release as failure.",
    )
    args = parser.parse_args(argv)
    try:
        payload = load_manifest(args.manifest)
        report = build_report(args.root.resolve(), payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["status"] == "failed":
        return 1
    if args.strict and report["status"] == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
