from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "docs" / "hk-research-lane-inventory.json"
DEFAULT_TEMPLATE = ROOT / "demo" / "hk-research-lane-template-v1"
REQUIRED_FIELDS = {
    "id",
    "path",
    "owner",
    "category",
    "lifecycle",
    "action",
    "dependencies",
    "migration_status",
    "deletion_gate",
}
ALLOWED_ACTIONS = {"move", "keep", "archive", "delete_later", "removed"}
FORBIDDEN_SUFFIXES = {".parquet", ".zip", ".tar", ".gz", ".zst", ".jsonl"}
FORBIDDEN_NAMES = {".env", ".env.local", ".envrc"}
SECRET_MARKERS = {
    "ACCESS_TOKEN",
    "LONGPORT_ACCESS_TOKEN",
    "RQDATA_PASSWORD",
    "TUSHARE_TOKEN",
}
IGNORED_PARTS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
Issue = dict[str, str]


def load_inventory(path: Path = DEFAULT_INVENTORY) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("HK research lane inventory must be a JSON object.")
    return payload


def _issue(check: str, message: str) -> Issue:
    return {"check": check, "message": message}


def _record_issues(record: object, index: int, seen: set[str]) -> list[Issue]:
    if not isinstance(record, dict):
        return [_issue("record_type", f"record {index} is not an object")]

    issues: list[Issue] = []
    record_id = str(record.get("id") or f"record_{index}")
    if record_id in seen:
        issues.append(_issue("duplicate_id", record_id))
    seen.add(record_id)

    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        issues.append(_issue("missing_fields", f"{record_id}: {missing}"))
    if record.get("action") not in ALLOWED_ACTIONS:
        issues.append(_issue("action", f"{record_id}: invalid action"))
    gate = record.get("deletion_gate")
    if not isinstance(gate, dict):
        issues.append(_issue("deletion_gate", f"{record_id}: gate missing"))
    elif (
        record.get("action") in {"move", "archive", "delete_later"}
        and gate.get("status") == "ready"
    ):
        issues.append(
            _issue(
                "premature_deletion_gate",
                f"{record_id}: ready gates require a separate removal change",
            )
        )
    return issues


def _has_retained_owner(records: list[Any], owner: str) -> bool:
    return any(
        isinstance(record, dict) and record.get("owner") == owner and record.get("action") == "keep"
        for record in records
    )


def _boundary_issues(records: list[Any]) -> list[Issue]:
    issues: list[Issue] = []
    if not _has_retained_owner(records, "quant-execution-engine"):
        issues.append(
            _issue("execution_boundary", "standard execution contract must remain retained")
        )
    if not _has_retained_owner(records, "market-data-platform"):
        issues.append(
            _issue(
                "data_platform_boundary",
                "HK data production must remain with market-data-platform",
            )
        )
    return issues


def validate_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    issues: list[Issue] = []
    if payload.get("schema_version") != "hk_research_lane_inventory.v1":
        issues.append(_issue("schema_version", "unsupported schema_version"))
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        issues.append(_issue("records", "records must be a non-empty list"))
        records = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        issues.extend(_record_issues(record, index, seen))
    issues.extend(_boundary_issues(records))
    return {
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "record_count": len(records),
    }


def scan_template(path: Path = DEFAULT_TEMPLATE) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not path.exists():
        return {
            "status": "failed",
            "issues": [{"path": str(path), "check": "missing_template"}],
        }
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        if IGNORED_PARTS & set(item.relative_to(path).parts):
            continue
        rel = item.relative_to(path).as_posix()
        if item.name in FORBIDDEN_NAMES:
            issues.append({"path": rel, "check": "forbidden_env_file"})
        if item.suffix.lower() in FORBIDDEN_SUFFIXES:
            issues.append({"path": rel, "check": "runtime_or_archive_suffix"})
        text = item.read_text(encoding="utf-8", errors="ignore")
        for marker in SECRET_MARKERS:
            if marker in text:
                issues.append({"path": rel, "check": "secret_marker"})
                break
    return {"status": "passed" if not issues else "failed", "issues": issues}


def build_report(
    *,
    inventory_path: Path = DEFAULT_INVENTORY,
    template_path: Path = DEFAULT_TEMPLATE,
) -> dict[str, Any]:
    inventory = load_inventory(inventory_path)
    inventory_validation = validate_inventory(inventory)
    template_scan = scan_template(template_path)
    status = (
        "passed"
        if inventory_validation["status"] == "passed" and template_scan["status"] == "passed"
        else "failed"
    )
    return {
        "status": status,
        "inventory": inventory_validation,
        "template_scan": template_scan,
        "policy": inventory.get("policy", {}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate HK research lane inventory.")
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args(argv)

    report = build_report(
        inventory_path=Path(args.inventory),
        template_path=Path(args.template),
    )
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"HK research lane inventory: {report['status']}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
