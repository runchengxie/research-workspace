"""Quality coverage drift checks for workspace governance."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from workspace_governance_common import Check

QUALITY_REGISTER_FIELDS = {
    "repo",
    "path",
    "tool",
    "owner",
    "reason",
    "next_include_target",
    "review_milestone",
    "coverage_patterns",
}
PER_FILE_IGNORE_REGISTER_FIELDS = {
    "repo",
    "path",
    "tool",
    "rules",
    "owner",
    "reason",
    "next_action",
    "review_milestone",
}
QUALITY_DEBT_BUDGET_FIELDS = {
    "broad_exclude_register_max",
    "per_file_ignore_register_max",
    "policy",
}
EXPECTED_QUALITY_REPOS = {
    "alpha-research",
    "market-data-platform",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
}
NON_DEBT_QUALITY_EXCLUDES = {
    ".venv",
    "artifacts",
    "build",
    "data",
    "dist",
    "docs/archive",
    "outputs",
    "reports",
}


def _load_pyproject(root: Path, repo: str) -> tuple[dict[str, Any] | None, str | None]:
    path = root / repo / "pyproject.toml"
    if not path.is_file():
        return None, f"Missing {repo}/pyproject.toml"
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, f"Invalid {repo}/pyproject.toml: {exc}"


def _quality_config_entries(pyproject: dict[str, Any], tool_name: str) -> list[str]:
    tool = pyproject.get("tool", {})
    if not isinstance(tool, dict):
        return []
    if tool_name == "ruff":
        ruff = tool.get("ruff", {})
        if not isinstance(ruff, dict):
            return []
        entries = ruff.get("extend-exclude", [])
    elif tool_name == "pyright":
        pyright = tool.get("pyright", {})
        if not isinstance(pyright, dict):
            return []
        entries = pyright.get("exclude", [])
    elif tool_name == "basedpyright":
        basedpyright = tool.get("basedpyright", {})
        if not isinstance(basedpyright, dict):
            return []
        entries = basedpyright.get("exclude", [])
    elif tool_name == "ty":
        ty = tool.get("ty", {})
        if not isinstance(ty, dict):
            return []
        src = ty.get("src", {})
        if not isinstance(src, dict):
            return []
        entries = src.get("exclude", [])
    else:
        return []
    if not isinstance(entries, list):
        return []
    return [str(entry) for entry in entries if isinstance(entry, str)]


def _ruff_per_file_ignores(pyproject: dict[str, Any]) -> dict[str, set[str]]:
    tool = pyproject.get("tool", {})
    if not isinstance(tool, dict):
        return {}
    ruff = tool.get("ruff", {})
    if not isinstance(ruff, dict):
        return {}
    lint = ruff.get("lint", {})
    if not isinstance(lint, dict):
        return {}
    ignores = lint.get("per-file-ignores", {})
    if not isinstance(ignores, dict):
        return {}
    return {
        str(path): {str(rule) for rule in rules if isinstance(rule, str)}
        for path, rules in ignores.items()
        if isinstance(path, str) and isinstance(rules, list)
    }


def _quality_debt_entries(entries: list[str]) -> set[str]:
    return {entry for entry in entries if entry not in NON_DEBT_QUALITY_EXCLUDES}


def _entry_matches_pattern(entry: str, pattern: str) -> bool:
    normalized = pattern.rstrip("/")
    return entry == normalized or entry.startswith(f"{normalized}/")


def _registered_patterns(register: list[Any], repo: str, tool_name: str) -> list[str]:
    patterns: list[str] = []
    for record in register:
        if (
            isinstance(record, dict)
            and record.get("repo") == repo
            and record.get("tool") == tool_name
            and isinstance(record.get("coverage_patterns"), list)
        ):
            patterns.extend(str(pattern) for pattern in record["coverage_patterns"])
    return patterns


def _unregistered_quality_excludes(entries: set[str], patterns: list[str]) -> list[str]:
    return sorted(
        entry
        for entry in entries
        if not any(_entry_matches_pattern(entry, pattern) for pattern in patterns)
    )


def _stale_quality_patterns(entries: set[str], patterns: list[str]) -> list[str]:
    return sorted(
        pattern
        for pattern in patterns
        if not any(_entry_matches_pattern(entry, pattern) for entry in entries)
    )


def _check_quality_exclude_drift(
    *,
    root: Path,
    register: list[Any],
) -> list[Check]:
    checks: list[Check] = []
    issues: list[str] = []
    for repo in sorted(EXPECTED_QUALITY_REPOS):
        pyproject, error = _load_pyproject(root, repo)
        if error:
            issues.append(error)
            continue
        assert pyproject is not None
        for tool_name in ("ruff", "basedpyright", "pyright", "ty"):
            entries = _quality_debt_entries(_quality_config_entries(pyproject, tool_name))
            patterns = _registered_patterns(register, repo, tool_name)
            missing = _unregistered_quality_excludes(entries, patterns)
            stale = _stale_quality_patterns(entries, patterns)
            if missing:
                issues.append(f"{repo}:{tool_name} unregistered excludes: {', '.join(missing)}")
            if stale:
                issues.append(f"{repo}:{tool_name} stale registered patterns: {', '.join(stale)}")

    if issues:
        checks.append(
            Check(
                "ERROR",
                "governance-quality",
                "Quality exclude register drift: " + "; ".join(issues),
            )
        )
    elif register:
        checks.append(
            Check(
                "WARN",
                "governance-quality",
                f"Registered broad quality excludes remain: {len(register)}.",
            )
        )
    return checks


def _registered_per_file_ignores(register: list[Any], repo: str) -> dict[str, set[str]]:
    records: dict[str, set[str]] = {}
    for record in register:
        if (
            isinstance(record, dict)
            and record.get("repo") == repo
            and record.get("tool") == "ruff"
            and isinstance(record.get("path"), str)
            and isinstance(record.get("rules"), list)
        ):
            records[str(record["path"])] = {
                str(rule) for rule in record["rules"] if isinstance(rule, str)
            }
    return records


def _check_per_file_ignore_drift(
    *,
    root: Path,
    register: list[Any],
) -> list[Check]:
    issues: list[str] = []
    for repo in sorted(EXPECTED_QUALITY_REPOS):
        pyproject, error = _load_pyproject(root, repo)
        if error:
            issues.append(error)
            continue
        assert pyproject is not None
        actual = _ruff_per_file_ignores(pyproject)
        registered = _registered_per_file_ignores(register, repo)
        missing = sorted(set(actual) - set(registered))
        stale = sorted(set(registered) - set(actual))
        changed = sorted(
            path for path in set(actual) & set(registered) if actual[path] != registered[path]
        )
        if missing:
            issues.append(f"{repo}:ruff unregistered per-file ignores: {', '.join(missing)}")
        if stale:
            issues.append(f"{repo}:ruff stale per-file ignore records: {', '.join(stale)}")
        if changed:
            issues.append(f"{repo}:ruff per-file ignore rule drift: {', '.join(changed)}")
    if issues:
        return [
            Check(
                "ERROR",
                "governance-quality",
                "Per-file ignore register drift: " + "; ".join(issues),
            )
        ]
    if register:
        return [
            Check(
                "WARN",
                "governance-quality",
                f"Registered per-file ignores remain: {len(register)}.",
            )
        ]
    return []


def _valid_budget_limit(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _check_quality_debt_budget(
    manifest: dict[str, Any],
    *,
    broad_exclude_count: int,
    per_file_ignore_count: int,
) -> list[Check]:
    budget = manifest.get("debt_budget")
    if not isinstance(budget, dict):
        return [
            Check(
                "ERROR",
                "governance-quality",
                "Quality debt budget is missing or invalid.",
            )
        ]
    if not QUALITY_DEBT_BUDGET_FIELDS <= set(budget):
        return [
            Check(
                "ERROR",
                "governance-quality",
                "Quality debt budget is missing fields: "
                + ", ".join(sorted(QUALITY_DEBT_BUDGET_FIELDS - set(budget))),
            )
        ]

    issues: list[str] = []
    broad_limit = budget["broad_exclude_register_max"]
    per_file_limit = budget["per_file_ignore_register_max"]
    policy = budget["policy"]
    if not _valid_budget_limit(broad_limit):
        issues.append("broad_exclude_register_max must be a non-negative integer")
    elif broad_exclude_count > broad_limit:
        issues.append(
            f"broad_exclude_register count {broad_exclude_count} exceeds max {broad_limit}"
        )
    if not _valid_budget_limit(per_file_limit):
        issues.append("per_file_ignore_register_max must be a non-negative integer")
    elif per_file_ignore_count > per_file_limit:
        issues.append(
            f"per_file_ignore_register count {per_file_ignore_count} exceeds max {per_file_limit}"
        )
    if not isinstance(policy, str) or not policy.strip():
        issues.append("policy must be a non-empty string")
    if issues:
        return [
            Check(
                "ERROR",
                "governance-quality",
                "Quality debt budget violation: " + "; ".join(issues),
            )
        ]

    return [
        Check(
            "OK",
            "governance-quality",
            (
                "Quality debt budgets hold: "
                f"broad_excludes={broad_exclude_count}/{broad_limit}, "
                f"per_file_ignores={per_file_ignore_count}/{per_file_limit}."
            ),
        )
    ]


def check_quality_coverage(root: Path, manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    repo_names = {
        str(record.get("repo", ""))
        for record in manifest.get("repos", [])
        if isinstance(record, dict)
    }
    if repo_names != EXPECTED_QUALITY_REPOS:
        checks.append(
            Check(
                "ERROR",
                "governance-quality",
                "Quality coverage repos mismatch: "
                f"expected={sorted(EXPECTED_QUALITY_REPOS)} actual={sorted(repo_names)}.",
            )
        )
    else:
        checks.append(Check("OK", "governance-quality", "Quality coverage repos are listed."))

    register = manifest.get("broad_exclude_register", [])
    missing_fields = [
        f"{record.get('repo', '<unknown>')}:{record.get('path', '<unknown>')}"
        for record in register
        if isinstance(record, dict) and not QUALITY_REGISTER_FIELDS <= set(record)
    ]
    if missing_fields:
        checks.append(
            Check(
                "ERROR",
                "governance-quality",
                "Broad quality exclude records are missing fields: " + "; ".join(missing_fields),
            )
        )
    else:
        checks.extend(_check_quality_exclude_drift(root=root, register=register))

    per_file_register = manifest.get("per_file_ignore_register", [])
    missing_per_file_fields = [
        f"{record.get('repo', '<unknown>')}:{record.get('path', '<unknown>')}"
        for record in per_file_register
        if isinstance(record, dict) and not PER_FILE_IGNORE_REGISTER_FIELDS <= set(record)
    ]
    if missing_per_file_fields:
        checks.append(
            Check(
                "ERROR",
                "governance-quality",
                "Per-file ignore records are missing fields: " + "; ".join(missing_per_file_fields),
            )
        )
    else:
        checks.extend(_check_per_file_ignore_drift(root=root, register=per_file_register))
    checks.extend(
        _check_quality_debt_budget(
            manifest,
            broad_exclude_count=len(register) if isinstance(register, list) else 0,
            per_file_ignore_count=len(per_file_register)
            if isinstance(per_file_register, list)
            else 0,
        )
    )
    return checks
