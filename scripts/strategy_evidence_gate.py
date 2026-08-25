#!/usr/bin/env python3
"""Enforce lifecycle-aware strategy evidence requirements (anti-overfitting gate).

The gate maps each strategy lifecycle to a mandatory set of evidence checks
defined in ``strategy-research/evidence_policy.json`` and validates per-strategy
evidence bundles against those requirements. A single backtest point estimate
cannot satisfy the ``benchmark_matrix`` check: the unified exam table must cover
at least two of universe, horizon, regime and cost axes.

Exit codes:
- 0: all evaluated strategies compliant, or default report mode without ``--strict``
- 1: ``--strict`` and any strategy misses mandatory evidence, the promotion gate
  (``--strategy`` + ``--require``) fails, or the configuration is invalid
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
_promotion = importlib.import_module("research_contracts.promotion_evidence")

DEFAULT_POLICY = "strategy-research/evidence_policy.json"
DEFAULT_CATALOG = "strategy-research/catalog.json"
DEFAULT_EVIDENCE_DIR = "strategy-research/evidence"
DEFAULT_PROMOTION_PROFILES = "strategy-research/promotion_profiles.json"
BENCHMARK_MATRIX_AXES = ("universe", "horizon", "regime", "cost_bps")


@dataclass(frozen=True)
class StrategyResult:
    strategy_id: str
    lifecycle: str
    required: list[str]
    present: list[str]
    missing: list[str]
    verdict: bool
    known_gaps_waived: bool = False
    unregistered_gaps: list[str] = field(default_factory=list)
    production_eligible: bool = False
    promotion_profile: str | None = None
    validated_promotion_checks: list[str] = field(default_factory=list)
    invalid_evidence: dict[str, list[str]] = field(default_factory=dict)
    profile_failures: list[str] = field(default_factory=list)


def _normalize_gap_keys(known_gaps: Any) -> set[str]:
    """Collect the check keys referenced by a bundle's known_gaps entries.

    Each known_gaps string is expected to start with ``"<check>:`` so that the
    gate can match it against a missing requirement. Plain strings without a
    colon are treated as free-form notes and ignored for matching.
    """
    if not isinstance(known_gaps, list):
        return set()
    keys: set[str] = set()
    for item in known_gaps:
        if not isinstance(item, str):
            continue
        head = item.split(":", 1)[0].strip()
        if head:
            keys.add(head)
    return keys


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} 必须是 JSON 对象")
    return payload


def _policy_checks(policy: dict[str, Any]) -> dict[str, Any]:
    checks = policy.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("evidence_policy.json 缺少 checks 对象")
    return checks


def _required_for(policy: dict[str, Any], lifecycle: str) -> list[str]:
    table = policy.get("required_by_lifecycle")
    if not isinstance(table, dict) or lifecycle not in table:
        raise ValueError(f"evidence_policy.json 缺少生命周期 {lifecycle} 的要求")
    required = table[lifecycle]
    if not isinstance(required, list):
        raise ValueError(f"生命周期 {lifecycle} 的要求必须是列表")
    return required


def _bundle_for(evidence_dir: Path, strategy_id: str) -> dict[str, Any] | None:
    path = evidence_dir / f"{strategy_id}.json"
    if not path.is_file():
        return None
    return _load_json(path)


def _entry_valid(entry: dict[str, Any] | None, requirement: dict[str, Any]) -> bool:
    if entry is None:
        return False
    if entry.get("outcome") != "pass":
        return False
    evidence = entry.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        return False
    evidence_keys = requirement.get("evidence_keys")
    if not isinstance(evidence_keys, list) or not evidence_keys:
        return True
    return any(entry.get(key) for key in evidence_keys)


def _validate_benchmark_cells(entry: dict[str, Any]) -> tuple[bool, str]:
    cells = entry.get("cells")
    if not isinstance(cells, list) or len(cells) < 2:
        return False, "cells 不足两条"
    span = sum(
        1
        for axis in BENCHMARK_MATRIX_AXES
        if len({cell.get(axis) for cell in cells if cell.get(axis) is not None}) > 1
    )
    if span < 2:
        return False, "cells 未覆盖至少两个维度"
    return True, ""


def _evaluate(
    strategy: dict[str, Any],
    policy: dict[str, Any],
    bundle: dict[str, Any] | None,
    *,
    require_lifecycle: str | None,
) -> StrategyResult:
    lifecycle = require_lifecycle or strategy["lifecycle"]
    required = _required_for(policy, lifecycle)
    checks = _policy_checks(policy)
    bundle_checks = bundle.get("checks") if bundle else None
    if not isinstance(bundle_checks, dict):
        bundle_checks = {}

    present: list[str] = []
    missing: list[str] = []
    for key in required:
        requirement = checks.get(key, {})
        entry = bundle_checks.get(key)
        ok = _entry_valid(entry, requirement)
        if ok and key == "benchmark_matrix" and isinstance(entry, dict):
            ok, _reason = _validate_benchmark_cells(entry)
        if ok:
            present.append(key)
        else:
            missing.append(key)

    production_eligible = bool(strategy.get("production_eligible", False))
    known_gap_keys = _normalize_gap_keys(bundle.get("known_gaps") if bundle else None)
    waived = [key for key in missing if key in known_gap_keys]
    unregistered = [key for key in missing if key not in known_gap_keys]

    # A non-production strategy may carry explicitly registered known gaps
    # without blocking the strict gate; production strategies must close every
    # required check, so any missing item (registered or not) stays a hard fail.
    known_gaps_waived = bool(waived) and not unregistered and not production_eligible
    verdict = not missing if production_eligible else (not unregistered)
    return StrategyResult(
        strategy_id=str(strategy["id"]),
        lifecycle=lifecycle,
        required=required,
        present=present,
        missing=missing,
        verdict=verdict,
        known_gaps_waived=known_gaps_waived,
        unregistered_gaps=unregistered,
        production_eligible=production_eligible,
    )


def _promotion_cells(result: StrategyResult) -> tuple[str, str]:
    if result.promotion_profile is None:
        return "-", "-"
    source_count = f"{len(result.validated_promotion_checks)}/{len(result.present)}"
    profile_state = "通过" if not result.profile_failures else "未通过"
    return source_count, profile_state


def _render_table(results: list[StrategyResult], *, show_promotion: bool = False) -> str:
    rows: list[tuple[str, ...]] = []
    for result in results:
        row = (
            result.strategy_id,
            result.lifecycle,
            "通过" if result.verdict else "未通过",
            f"{len(result.present)}/{len(result.required)}",
            ",".join(result.missing) if result.missing else "-",
            "已知缺口豁免" if result.known_gaps_waived else "-",
            ",".join(result.unregistered_gaps) if result.unregistered_gaps else "-",
        )
        if show_promotion:
            source_count, profile_state = _promotion_cells(result)
            row = (*row, source_count, profile_state)
        rows.append(row)

    headers = ("策略", "生命周期", "结论", "检查", "缺失", "豁免", "未登记缺口")
    if show_promotion:
        headers = (*headers, "晋级源", "Profile")
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = ["  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))]
    lines.append("  ".join("-" * width for width in widths))
    lines.extend(
        "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)) for row in rows
    )
    return "\n".join(lines)


def _as_json(results: list[StrategyResult]) -> str:
    payload = {
        "schema_version": "strategy_evidence_gate.v1",
        "strategies": [
            {
                "strategy_id": result.strategy_id,
                "lifecycle": result.lifecycle,
                "required": result.required,
                "present": result.present,
                "missing": result.missing,
                "verdict": result.verdict,
                "production_eligible": result.production_eligible,
                "known_gaps_waived": result.known_gaps_waived,
                "unregistered_gaps": result.unregistered_gaps,
                "promotion_profile": result.promotion_profile,
                "validated_promotion_checks": result.validated_promotion_checks,
                "invalid_evidence": result.invalid_evidence,
                "profile_failures": result.profile_failures,
            }
            for result in results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _gate_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    policy_path = args.policy or args.root / DEFAULT_POLICY
    catalog_path = args.catalog or args.root / DEFAULT_CATALOG
    evidence_dir = args.evidence_dir or args.root / DEFAULT_EVIDENCE_DIR
    if not policy_path.is_file():
        raise SystemExit(f"缺少证据策略文件：{policy_path}")
    if not catalog_path.is_file():
        raise SystemExit(f"缺少策略目录：{catalog_path}")
    return policy_path, catalog_path, evidence_dir


def _load_catalog(catalog_path: Path) -> list[dict[str, Any]]:
    catalog = _load_json(catalog_path)
    strategies = catalog.get("strategies")
    if not isinstance(strategies, list):
        raise SystemExit("catalog.json 缺少 strategies 列表")
    return strategies


def _promotion_results(
    strategies: list[dict[str, Any]],
    args: argparse.Namespace,
    policy: dict[str, Any],
    evidence_dir: Path,
) -> list[StrategyResult]:
    candidates = [item for item in strategies if item.get("id") == args.strategy_id]
    if not candidates:
        raise SystemExit(f"策略目录中不存在策略：{args.strategy_id}")
    if not args.require_lifecycle:
        raise SystemExit("单独指定 --strategy 时必须同时指定 --require 目标生命周期")
    bundle = _bundle_for(evidence_dir, str(args.strategy_id))
    result = _evaluate(
        candidates[0],
        policy,
        bundle,
        require_lifecycle=args.require_lifecycle,
    )
    return [result]


def _review_results(
    strategies: list[dict[str, Any]],
    policy: dict[str, Any],
    evidence_dir: Path,
) -> list[StrategyResult]:
    return [
        _evaluate(
            item,
            policy,
            _bundle_for(evidence_dir, str(item.get("id", ""))),
            require_lifecycle=None,
        )
        for item in strategies
    ]


def _profiles(args: argparse.Namespace) -> dict[str, Any]:
    path = args.promotion_profiles or args.root / DEFAULT_PROMOTION_PROFILES
    return _load_json(path) if path.is_file() else {}


def _data_platform_root(args: argparse.Namespace) -> Path | None:
    if args.data_platform_root is not None:
        return args.data_platform_root
    value = os.environ.get("DATA_PLATFORM_ROOT", "").strip()
    return Path(value).expanduser() if value else None


def _validate_promotion_results(
    results: list[StrategyResult],
    *,
    args: argparse.Namespace,
    evidence_dir: Path,
) -> list[StrategyResult]:
    profiles = _profiles(args)
    data_root = _data_platform_root(args)
    validated: list[StrategyResult] = []
    for result in results:
        bundle = _bundle_for(evidence_dir, result.strategy_id)
        source_result = _promotion.validate_strategy_promotion(
            root=args.root,
            strategy_id=result.strategy_id,
            required_checks=result.required,
            bundle=bundle,
            profiles=profiles,
            data_platform_root=data_root,
        )
        validated.append(
            replace(
                result,
                promotion_profile=source_result.profile_id,
                validated_promotion_checks=source_result.validated_checks,
                invalid_evidence=source_result.invalid_evidence,
                profile_failures=source_result.profile_failures,
            )
        )
    return validated


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--promotion-profiles", type=Path)
    parser.add_argument("--data-platform-root", type=Path)
    parser.add_argument("--strategy", dest="strategy_id")
    parser.add_argument("--require", dest="require_lifecycle")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--zero-gaps",
        dest="zero_gaps",
        action="store_true",
        help="晋级评审档：与 --strict 同用，要求缺口归零且 canonical 晋级证据有效",
    )
    parser.add_argument("--json", dest="as_json", action="store_true")
    return parser.parse_args(argv)


def _run_gate(argv: list[str]) -> int:
    args = _parse_args(argv)
    policy_path, catalog_path, evidence_dir = _gate_paths(args)
    policy = _load_json(policy_path)
    _policy_checks(policy)
    strategies = _load_catalog(catalog_path)

    if args.strategy_id:
        results = _promotion_results(strategies, args, policy, evidence_dir)
    else:
        results = _review_results(strategies, policy, evidence_dir)

    if args.zero_gaps and not args.strict:
        raise SystemExit("--zero-gaps 必须与 --strict 同用")
    if args.zero_gaps:
        results = _validate_promotion_results(results, args=args, evidence_dir=evidence_dir)

    if args.as_json:
        print(_as_json(results))
    else:
        print(_render_table(results, show_promotion=args.zero_gaps))

    blocked = _blocked_strategy_ids(results, zero_gaps=args.zero_gaps)
    if blocked and (args.strict or args.strategy_id):
        if args.zero_gaps:
            ids = ", ".join(blocked)
            print(
                "晋级评审未通过（--zero-gaps）："
                f"{ids} 仍带缺口、缺失检查或无效 canonical 晋级证据"
            )
        return 1
    return 0


def _blocked_strategy_ids(results: list[StrategyResult], *, zero_gaps: bool) -> list[str]:
    """Return strategy IDs that fail the active evidence gate tier."""
    blocked: list[str] = []
    for result in results:
        hard = bool(result.unregistered_gaps or (result.production_eligible and result.missing))
        soft = bool(
            result.known_gaps_waived
            or result.missing
            or result.invalid_evidence
            or result.profile_failures
        )
        if hard or (zero_gaps and soft):
            blocked.append(result.strategy_id)
    return blocked


def main(argv: list[str] | None = None) -> int:
    try:
        return _run_gate(list(argv) if argv is not None else sys.argv[1:])
    except (OSError, ValueError) as exc:
        print(f"策略证据门禁失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
