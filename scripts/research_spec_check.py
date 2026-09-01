#!/usr/bin/env python3
"""Validate research_spec.v1 experiment manifests (实验说明书).

Each experiment under ``strategy-research/research/experiments/<id>/`` may carry a
``research_spec.json`` that describes in one place what the experiment did:
universe, data, prediction target and horizon, model, portfolio construction,
cost, benchmark and out-of-sample protocol. The checker enforces the schema and,
for completed experiments, verifies that referenced evidence files exist.

Exit codes:
- 0: all found specs are valid
- 1: any spec is invalid or references a missing evidence file
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_NAME = "research_spec.json"
SPEC_VERSION = "research_spec.v1"
ALLOWED_STATUS = {"proposed", "in_progress", "complete", "archived"}
NOT_APPLICABLE = "n/a"
ALLOWED_CONSTRUCTIONS = {
    "top_k",
    "long_short",
    "long_only",
    "pairwise",
    NOT_APPLICABLE,
}
ALLOWED_TASKS = {"ranking", "regression", "classification", NOT_APPLICABLE}
REQUIRED_TOP_LEVEL = (
    "schema_version",
    "experiment_id",
    "title",
    "market",
    "status",
    "universe",
    "data",
    "prediction",
    "model",
    "portfolio",
    "cost",
    "benchmark",
    "evaluation",
    "evidence_refs",
)


@dataclass(frozen=True)
class SpecCheck:
    experiment_id: str
    issues: list[str]

    @property
    def ok(self) -> bool:
        return not self.issues


def _spec_files(root: Path) -> list[Path]:
    return sorted((root / "strategy-research" / "research" / "experiments").glob(f"*/{SPEC_NAME}"))


def _dict_field(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    if not isinstance(value, dict):
        return {}
    return value


def _require(
    payload: dict[str, Any],
    name: str,
    *,
    allow_na: bool = False,
) -> str | None:
    value = payload.get(name)
    if value is None:
        return f"{name} 缺失"
    if isinstance(value, str) and not value.strip():
        return f"{name} 为空"
    if allow_na and value == NOT_APPLICABLE:
        return None
    if not isinstance(value, str):
        return f"{name} 必须是字符串"
    return None


def _list_field(
    payload: dict[str, Any],
    name: str,
    *,
    allowed_types: tuple[type, ...] = (str,),
    allow_na: bool = False,
) -> str | None:
    value = payload.get(name)
    if value is None:
        return f"{name} 缺失"
    if allow_na and value == NOT_APPLICABLE:
        return None
    if not isinstance(value, list):
        return f"{name} 必须是列表或 {NOT_APPLICABLE}"
    if not value:
        return f"{name} 不能为空列表"
    if not all(isinstance(item, allowed_types) for item in value):
        return f"{name} 元素类型不正确"
    return None


def _check_top_level(payload: dict[str, Any], expected_id: str) -> list[str]:
    issues: list[str] = []
    missing = [name for name in REQUIRED_TOP_LEVEL if name not in payload]
    if missing:
        issues.append("缺少字段：" + ",".join(missing))
    if payload.get("schema_version") != SPEC_VERSION:
        issues.append(f"schema_version 必须是 {SPEC_VERSION}")
    if payload.get("experiment_id") != expected_id:
        issues.append(f"experiment_id 必须是 {expected_id}")
    status = payload.get("status")
    if status not in ALLOWED_STATUS:
        issues.append(f"status 必须是 {'、'.join(sorted(ALLOWED_STATUS))} 之一")
    market = payload.get("market")
    if not isinstance(market, str) or not market.strip():
        issues.append("market 缺失或为空")
    return issues


def _check_structured_fields(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    universe = _dict_field(payload, "universe")
    issues.extend(_issue("universe.description", _require(universe, "description")))
    data = _dict_field(payload, "data")
    issues.extend(_issue("data.source", _require(data, "source")))
    prediction = _dict_field(payload, "prediction")
    issues.extend(_issue("prediction.target", _require(prediction, "target")))
    issues.extend(_issue("prediction.horizon", _require(prediction, "horizon")))
    task = prediction.get("task")
    if task not in ALLOWED_TASKS:
        issues.append("prediction.task 必须属于 ranking、regression、classification 或 n/a")
    model = _dict_field(payload, "model")
    issues.extend(_issue("model.name", _require(model, "name")))
    issues.extend(_issue("model.training", _require(model, "training")))
    portfolio = _dict_field(payload, "portfolio")
    construction = portfolio.get("construction")
    if construction not in ALLOWED_CONSTRUCTIONS:
        allowed = "、".join(ALLOWED_CONSTRUCTIONS)
        issues.append(f"portfolio.construction 必须属于 {allowed} 之一")
    cost = _dict_field(payload, "cost")
    issues.extend(
        _issue(
            "cost.cost_bps",
            _list_field(cost, "cost_bps", allowed_types=(int,), allow_na=True),
        )
    )
    benchmark = _dict_field(payload, "benchmark")
    issues.extend(
        _issue(
            "benchmark.cohorts",
            _list_field(benchmark, "cohorts", allow_na=True),
        )
    )
    evaluation = _dict_field(payload, "evaluation")
    issues.extend(
        _issue(
            "evaluation.oos_protocol",
            _list_field(evaluation, "oos_protocol", allow_na=True),
        )
    )
    reserved = evaluation.get("final_oos_reserved")
    if not isinstance(reserved, bool):
        issues.append("evaluation.final_oos_reserved 必须是布尔值")
    return issues


def _check_evidence(payload: dict[str, Any], root: Path) -> list[str]:
    refs = payload.get("evidence_refs")
    if not isinstance(refs, list):
        return ["evidence_refs 必须是列表"]
    status = payload.get("status")
    if status in {"complete", "archived"} and not refs:
        return ["status 为 complete 或 archived 时 evidence_refs 不能为空"]
    issues: list[str] = []
    for ref in refs:
        if not isinstance(ref, str):
            issues.append("evidence_refs 元素必须是字符串")
            continue
        resolved = (root / ref).resolve()
        if not resolved.is_file():
            issues.append(f"evidence_ref 不存在：{ref}")
    return issues


def _trial_ledger_config(
    payload: dict[str, Any],
) -> tuple[str, str] | list[str] | None:
    config = payload.get("trial_ledger")
    if config is None:
        return None
    if not isinstance(config, dict):
        return ["trial_ledger 必须是对象"]
    relative_path = config.get("path")
    family = config.get("multiple_testing_family")
    issues: list[str] = []
    if not isinstance(relative_path, str) or not relative_path.strip():
        issues.append("trial_ledger.path 缺失或为空")
    if not isinstance(family, str) or not family.strip():
        issues.append("trial_ledger.multiple_testing_family 缺失或为空")
    if issues:
        return issues
    return relative_path, family


def _resolve_trial_ledger(root: Path, relative_path: str) -> tuple[Path | None, str | None]:
    strategy_root = (root / "strategy-research").resolve()
    resolved = (strategy_root / relative_path).resolve()
    try:
        resolved.relative_to(strategy_root)
    except ValueError:
        return None, "trial_ledger.path 不能逃逸 strategy-research"
    if not resolved.is_file():
        return None, f"trial_ledger 不存在：{relative_path}"
    return resolved, None


def _trial_ledger_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            issues.append(f"trial_ledger 第 {line_number} 行 JSON 无效")
            continue
        if not isinstance(row, dict):
            issues.append(f"trial_ledger 第 {line_number} 行必须是对象")
            continue
        rows.append(row)
    return rows, issues


def _check_trial_ledger(
    payload: dict[str, Any],
    expected_id: str,
    root: Path,
) -> list[str]:
    config = _trial_ledger_config(payload)
    if config is None:
        return []
    if isinstance(config, list):
        return config
    relative_path, family = config
    path, error = _resolve_trial_ledger(root, relative_path)
    if error:
        return [error]
    assert path is not None
    rows, issues = _trial_ledger_rows(path)
    counted_family = False
    for row in rows:
        if row.get("experiment_id") != expected_id:
            issues.append(f"trial_ledger experiment_id 必须是 {expected_id}")
        multiple = row.get("multiple_testing")
        if not isinstance(multiple, dict):
            continue
        if multiple.get("family_id") == family and multiple.get("counted") is True:
            counted_family = True
    if not counted_family:
        issues.append(f"trial_ledger.multiple_testing_family {family} 没有 counted=true trial")
    return issues


def _issue(prefix: str, message: str | None) -> list[str]:
    return [f"{prefix} {message}"] if message else []


def check_spec(path: Path, *, expected_id: str, root: Path) -> SpecCheck:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return SpecCheck(expected_id, ["research_spec.json 必须是 JSON 对象"])
    issues = _check_top_level(payload, expected_id)
    issues.extend(_check_structured_fields(payload))
    issues.extend(_check_evidence(payload, root))
    issues.extend(_check_trial_ledger(payload, expected_id, root))
    return SpecCheck(expected_id, issues)


def _render(checks: list[SpecCheck], *, as_json: bool) -> str:
    if as_json:
        payload = {
            "schema_version": "research_spec_check.v1",
            "specs": [
                {
                    "experiment_id": check.experiment_id,
                    "ok": check.ok,
                    "issues": check.issues,
                }
                for check in checks
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines = [f"[{'OK' if check.ok else 'ERROR'}] {check.experiment_id}" for check in checks]
    lines.extend(f"  - {issue}" for check in checks for issue in check.issues)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    root = args.root.resolve()
    if args.spec:
        path = args.spec.resolve()
        checks = [check_spec(path, expected_id=path.parent.name, root=root)]
    else:
        checks = [
            check_spec(path, expected_id=path.parent.name, root=root) for path in _spec_files(root)
        ]
    print(_render(checks, as_json=args.as_json))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
