"""Owner-API-only preflight and feature composition for the shadow experiment."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import EXPERIMENT_ID


@dataclass(frozen=True)
class ContextShadowInputs:
    data_root: Path
    a_share_contract: Any
    context_contract: Any
    context_pit_ref: Any
    context_audit: Mapping[str, Any]


@dataclass(frozen=True)
class ContextShadowAudit:
    status: str
    promotion_eligible: bool
    reasons: tuple[str, ...]
    context_audit: Mapping[str, Any]


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).with_name("experiment.yml")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("invalid macro context shadow configuration")
    if payload.get("horizons") != [5, 20, 60] or payload.get("primary_horizon") != 20:
        raise ValueError("macro context shadow horizons are frozen at [5, 20, 60] with primary 20")
    if set(payload.get("challengers", {})) != {"C0", "C1", "C2", "C3"}:
        raise ValueError("macro context shadow challengers must be exactly C0, C1, C2, C3")
    if payload.get("production_eligible") is not False:
        raise ValueError("macro context shadow cannot be production eligible")
    return payload


def load_inputs(
    data_root: str | Path, config: Mapping[str, Any] | None = None
) -> ContextShadowInputs:
    """Load the two current contracts through the published-data owner API."""

    del config
    from market_data_platform.published_assets import PublishedAssetContract

    root = Path(data_root).expanduser().resolve()
    a_share = PublishedAssetContract.load_current(root, market="a_share")
    context = PublishedAssetContract.load_current(root, market="cn_context")
    context_pit = context.asset("context_pit")
    audit = context_pit.manifest.get("pit_audit", {})
    if not isinstance(audit, Mapping):
        audit = {}
    return ContextShadowInputs(root, a_share, context, context_pit, audit)


def preflight_context(
    inputs: ContextShadowInputs,
    *,
    require_promotion_safe: bool,
) -> ContextShadowAudit:
    reasons: list[str] = []
    audit = inputs.context_audit
    if audit.get("revision_covered") is not True:
        reasons.append("context_not_revision_covered")
    if audit.get("freshness_verified") is not True:
        reasons.append("context_freshness_unverified")
    reconstructed = tuple(str(item) for item in audit.get("reconstructed_series", ()))
    if reconstructed:
        reasons.append("context_contains_reconstructed_series")
    if require_promotion_safe and reasons:
        return ContextShadowAudit("rejected", False, tuple(reasons), audit)
    status = "exploration_with_limitations" if reasons else "ready"
    return ContextShadowAudit(status, not reasons, tuple(reasons), audit)


def build_feature_variants(
    base_frame: Any,
    *,
    context_features: Any | None = None,
    interaction_features: Any | None = None,
    pit_fundamentals: Any | None = None,
) -> dict[str, Any]:
    """Compose challenger columns without implementing owner feature logic."""

    variants = {"C0": base_frame.copy()}
    variants["C1"] = _join_columns(variants["C0"], context_features)
    variants["C2"] = _join_columns(variants["C1"], interaction_features)
    variants["C3"] = _join_columns(variants["C2"], pit_fundamentals)
    return variants


def _join_columns(frame: Any, extra: Any | None) -> Any:
    if extra is None:
        return frame.copy()
    left = frame.reset_index(drop=True)
    right = extra.reset_index(drop=True)
    if len(left) != len(right):
        raise ValueError("contextual challenger frames must have identical row counts")
    overlap = set(left.columns).intersection(right.columns)
    if overlap:
        raise ValueError(f"contextual challenger columns overlap: {sorted(overlap)}")
    return left.join(right)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--config")
    parser.add_argument("--require-promotion-safe", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    inputs = load_inputs(args.data_root, config)
    audit = preflight_context(inputs, require_promotion_safe=args.require_promotion_safe)
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "dry_run": bool(args.dry_run),
        "status": audit.status,
        "promotion_eligible": audit.promotion_eligible,
        "reasons": list(audit.reasons),
        "contract_hashes": {
            "a_share": inputs.a_share_contract.contract_sha256,
            "cn_context": inputs.context_contract.contract_sha256,
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if audit.status != "rejected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
