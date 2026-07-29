"""Data platform root and current-contract checks."""

from __future__ import annotations

import json
from pathlib import Path

import workspace_env
from doctor_common import DATA_PLATFORM_ROOT_CANDIDATES
from workspace_governance import Check


def _check_hk_current_or_freeze(hk_contract: Path, hk_freeze_marker: Path) -> list[Check]:
    if hk_contract.is_file():
        return [Check("OK", "current-contract", f"Found {hk_contract}.")]
    if not hk_freeze_marker.is_file():
        return [Check("WARN", "current-contract", f"Missing {hk_contract}.")]

    try:
        marker = json.loads(hk_freeze_marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            Check(
                "WARN",
                "frozen-market",
                f"Invalid HK cold-storage marker {hk_freeze_marker}: {exc}",
            )
        ]

    cold_snapshot = Path(str(marker.get("cold_snapshot") or "")).expanduser()
    if cold_snapshot.is_dir():
        return [
            Check(
                "OK",
                "frozen-market",
                f"HK assets are frozen in cold storage: {cold_snapshot}.",
            )
        ]
    if marker.get("status") == "frozen" and marker.get("local_snapshot_available") is False:
        release_url = str(marker.get("release_url") or "").strip()
        restore_hint = f" Restore from {release_url} before hydrate." if release_url else ""
        return [
            Check(
                "OK",
                "frozen-market",
                "HK assets are frozen remotely; local cold snapshot is not required by default."
                + restore_hint,
            )
        ]
    return [
        Check(
            "WARN",
            "frozen-market",
            f"HK cold-storage snapshot is missing: {cold_snapshot}.",
        )
    ]


def check_data_platform_root(
    root: Path | None = None,
    candidates: tuple[Path, ...] | None = None,
) -> list[Check]:
    candidate_roots = candidates if candidates is not None else DATA_PLATFORM_ROOT_CANDIDATES
    root_text, source = workspace_env.data_platform_root_text(root)
    if not root_text:
        existing_candidates = [
            str(candidate) for candidate in candidate_roots if candidate.exists()
        ]
        hint = (
            f" Candidate: export DATA_PLATFORM_ROOT={existing_candidates[0]}."
            if existing_candidates
            else " Common candidates: ~/data/market-data-platform or /data/market-data-platform."
        )
        return [
            Check(
                "WARN",
                "data-platform-root",
                "DATA_PLATFORM_ROOT is not set; current contract checks are skipped." + hint,
            )
        ]

    artifact_root = Path(root_text).expanduser()
    checks: list[Check] = []
    if not artifact_root.exists():
        return [
            Check(
                "WARN",
                "data-platform-root",
                f"DATA_PLATFORM_ROOT does not exist: {artifact_root}",
            )
        ]

    source_suffix = f" ({source})" if source else ""
    checks.append(
        Check("OK", "data-platform-root", f"DATA_PLATFORM_ROOT={artifact_root}{source_suffix}")
    )
    current_root = artifact_root / "metadata" / "current_assets"
    hk_contract = current_root / "hk_current.json"
    a_share_contract = current_root / "a_share_current.json"
    legacy_cn_contract = current_root / "cn_current.json"
    hk_freeze_marker = artifact_root / "metadata" / "frozen_markets" / "hk.json"
    dataset_registry = artifact_root / "metadata" / "dataset_registry.csv"
    checks.extend(_check_hk_current_or_freeze(hk_contract, hk_freeze_marker))
    if a_share_contract.is_file():
        checks.append(Check("OK", "current-contract", f"Found {a_share_contract}."))
    else:
        checks.append(Check("WARN", "current-contract", f"Missing {a_share_contract}."))
    if legacy_cn_contract.exists():
        checks.append(
            Check(
                "WARN",
                "current-contract-alias",
                "Legacy alias exists; do not use as canonical A-share entry: "
                f"{legacy_cn_contract}.",
            )
        )
    if dataset_registry.is_file():
        checks.append(Check("OK", "dataset-registry", f"Found {dataset_registry}."))
    else:
        checks.append(Check("WARN", "dataset-registry", f"Missing {dataset_registry}."))
    return checks
