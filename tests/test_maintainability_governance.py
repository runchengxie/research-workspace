from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SCRIPT = ROOT / "scripts" / "maintainability_baseline.py"
BASELINE_RELATIVE = "docs/evidence/maintainability/baseline-20260617.json"
BASELINE_PATH = ROOT / BASELINE_RELATIVE
QUALITY_GOVERNANCE_SCRIPT = ROOT / "scripts" / "workspace_governance_quality.py"
WORKSPACE_GOVERNANCE_SCRIPT = ROOT / "scripts" / "workspace_governance.py"
REPOS = {
    "research-workspace",
    "alpha-research",
    "market-data-platform",
    "portfolio-backtester",
    "cross-sectional-trees",
    "quant-execution-engine",
}
REQUIRED_ROADMAP_PATHS = {
    "market-data-platform/src/market_data_platform/providers/tushare_a_share.py",
    "market-data-platform/src/market_data_platform/tushare_cli.py",
    "cross-sectional-trees/src/cstree/pipeline/eval.py",
    "cross-sectional-trees/src/cstree/pipeline/train_eval_stage.py",
    "cross-sectional-trees/src/cstree/research/summarize_runs.py",
    "cross-sectional-trees/src/cstree/exposure.py",
    "cross-sectional-trees/src/cstree/commands/tune.py",
    "quant-execution-engine/src/quant_execution_engine/cli.py",
    "quant-execution-engine/src/quant_execution_engine/broker/longport.py",
    "quant-execution-engine/project_tools/smoke_operator_harness.py",
}
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
DEPRECATION_BUDGET_FIELDS = {"pending_follow_up_max", "policy"}


def _load_json_doc(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _load_pyproject(repo: str) -> dict[str, Any]:
    return tomllib.loads((ROOT / repo / "pyproject.toml").read_text(encoding="utf-8"))


def _load_baseline_module() -> Any:
    spec = importlib.util.spec_from_file_location("maintainability_baseline", BASELINE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_quality_governance_module() -> Any:
    scripts_dir = str(QUALITY_GOVERNANCE_SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(
        "workspace_governance_quality",
        QUALITY_GOVERNANCE_SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_workspace_governance_module() -> Any:
    scripts_dir = str(WORKSPACE_GOVERNANCE_SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(
        "workspace_governance", WORKSPACE_GOVERNANCE_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _script_paths_to_classify() -> set[str]:
    roots = [
        ROOT / "scripts",
        ROOT / "alpha-research" / "scripts",
        ROOT / "cross-sectional-trees" / "scripts" / "internal",
        ROOT / "market-data-platform" / "scripts" / "internal",
        ROOT / "portfolio-backtester" / "scripts",
        ROOT / "quant-execution-engine" / "project_tools",
    ]
    paths: set[str] = set()
    for root in roots:
        for path in root.rglob("*"):
            if "__pycache__" in path.parts or path.suffix not in {".py", ".sh"}:
                continue
            paths.add(path.relative_to(ROOT).as_posix())
    return paths


def _deprecation_removal_issues(manifest: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for record in manifest["records"]:
        if record.get("status") != "removal_ready":
            continue
        consumer_audit = str(record.get("consumer_audit", "")).lower()
        if consumer_audit in {"", "pending", "manual_review_required"}:
            issues.append(f"{record['id']}: consumer_audit")
        if not record.get("replacement_docs"):
            issues.append(f"{record['id']}: replacement_docs")
        if not record.get("rollback_path"):
            issues.append(f"{record['id']}: rollback_path")
        if not record.get("focused_tests"):
            issues.append(f"{record['id']}: focused_tests")
        if record.get("restore_evidence_required") and not record.get("restore_evidence"):
            issues.append(f"{record['id']}: restore_evidence")
    return issues


def test_maintainability_baseline_schema_and_generator() -> None:
    baseline = _load_json_doc(BASELINE_RELATIVE)

    assert baseline["schema_version"] == "maintainability_baseline.v1"
    assert baseline["thresholds"] == {
        "large_file_loc": 500,
        "long_function_lines": 80,
        "complexity": 15,
    }
    assert {repo["repo"] for repo in baseline["repos"]} == REPOS
    for repo in baseline["repos"]:
        assert {
            "large_files",
            "long_functions",
            "complexity_hotspots",
            "quality_config",
            "script_inventory",
        } <= set(repo)
        assert isinstance(repo["python_file_count"], int)
        assert isinstance(repo["python_loc"], int)
        assert isinstance(repo["hk_related_file_count"], int)

    module = _load_baseline_module()
    current = module.build_baseline(module.DEFAULT_REPOS, thresholds=module.DEFAULT_THRESHOLDS)
    assert baseline == current

    root_only = module.build_baseline(["research-workspace"], thresholds=module.DEFAULT_THRESHOLDS)

    assert root_only["schema_version"] == "maintainability_baseline.v1"
    assert root_only["repos"][0]["repo"] == "research-workspace"
    assert "scripts/maintainability_baseline.py" in root_only["repos"][0]["script_inventory"]


def test_deprecation_register_has_required_fields_and_removal_gate() -> None:
    manifest = _load_json_doc("docs/deprecations.yml")
    required_fields = {
        "id",
        "owner_repo",
        "entrypoint",
        "replacement",
        "current_consumers",
        "target_milestone",
        "removal_condition",
        "rollback_path",
        "restore_evidence_required",
        "focused_tests",
        "consumer_audit",
        "replacement_docs",
        "status",
    }

    assert manifest["schema_version"] == "deprecation_register.v1"
    record_ids = [record["id"] for record in manifest["records"]]
    pending_count = sum(
        1
        for record in manifest["records"]
        if record["status"] in {"blocked_pending_audit", "follow_up_required"}
    )
    assert DEPRECATION_BUDGET_FIELDS <= set(manifest["deprecation_budget"])
    assert manifest["deprecation_budget"]["pending_follow_up_max"] == pending_count
    assert len(record_ids) == len(set(record_ids))
    assert _deprecation_removal_issues(manifest) == []
    for record in manifest["records"]:
        assert required_fields <= set(record)
        assert record["focused_tests"]

    mutated = copy.deepcopy(manifest)
    mutated["records"][0]["status"] = "removal_ready"
    mutated["records"][0]["consumer_audit"] = "pending"
    mutated["records"][0]["replacement_docs"] = ""
    mutated["records"][0]["rollback_path"] = ""
    mutated["records"][0]["focused_tests"] = []

    assert _deprecation_removal_issues(mutated)


def test_deprecation_budget_blocks_new_pending_surfaces() -> None:
    manifest = _load_json_doc("docs/deprecations.yml")
    module = _load_workspace_governance_module()
    mutated = copy.deepcopy(manifest)
    extra_record = copy.deepcopy(mutated["records"][0])
    extra_record["id"] = "new-legacy-surface"
    extra_record["status"] = "blocked_pending_audit"
    mutated["records"].append(extra_record)

    checks = module._check_deprecations(mutated)

    assert any(
        check.severity == "ERROR"
        and check.code == "governance-deprecations"
        and "pending deprecated surface count" in check.message
        for check in checks
    )


def test_script_lifecycle_manifest_classifies_all_tracked_scripts() -> None:
    manifest = _load_json_doc("docs/script-lifecycle.yml")
    required_fields = {
        "path",
        "owner",
        "purpose",
        "lifecycle",
        "safe_to_run_locally",
        "writes_files",
        "external_dependencies",
        "removal_condition",
    }

    assert manifest["schema_version"] == "script_lifecycle.v1"
    assert set(manifest["valid_lifecycles"]) == {"dev", "ci", "release", "migration", "archive"}
    records = {record["path"]: record for record in manifest["records"]}
    assert set(records) == _script_paths_to_classify()
    for record in records.values():
        assert required_fields <= set(record)
        assert record["lifecycle"] in manifest["valid_lifecycles"]
        assert isinstance(record["safe_to_run_locally"], bool)


def test_quality_coverage_governance_matches_submodule_configs() -> None:
    manifest = _load_json_doc("docs/quality-coverage-governance.yml")
    repos = {record["repo"]: record for record in manifest["repos"]}
    alpha_config = _load_pyproject("alpha-research")
    cross_config = _load_pyproject("cross-sectional-trees")
    market_config = _load_pyproject("market-data-platform")
    portfolio_config = _load_pyproject("portfolio-backtester")
    execution_config = _load_pyproject("quant-execution-engine")

    assert manifest["schema_version"] == "quality_coverage_governance.v1"
    assert QUALITY_DEBT_BUDGET_FIELDS <= set(manifest["debt_budget"])
    assert manifest["debt_budget"]["broad_exclude_register_max"] == len(
        manifest["broad_exclude_register"]
    )
    assert manifest["debt_budget"]["per_file_ignore_register_max"] == len(
        manifest["per_file_ignore_register"]
    )
    assert set(repos) == {
        "alpha-research",
        "cross-sectional-trees",
        "market-data-platform",
        "portfolio-backtester",
        "quant-execution-engine",
    }
    assert set(repos["alpha-research"]["basedpyright"]["include_targets"]) == set(
        alpha_config["tool"]["basedpyright"]["include"]
    )
    assert "extraPaths" not in alpha_config["tool"]["basedpyright"]
    assert set(repos["alpha-research"]["ty"]["include_targets"]) == set(
        alpha_config["tool"]["ty"]["src"]["include"]
    )
    cross_staged_select = cross_config["tool"]["maintainability"]["quality_targets"][
        "ruff_staged_select"
    ]
    assert set(cross_staged_select) == set(repos["cross-sectional-trees"]["ruff"]["staged_select"])
    assert set(repos["cross-sectional-trees"]["basedpyright"]["next_include_targets"]) <= set(
        cross_config["tool"]["basedpyright"]["include"]
    )
    assert set(repos["cross-sectional-trees"]["ty"]["include_targets"]) == set(
        cross_config["tool"]["ty"]["src"]["include"]
    )

    assert "maintainability" not in market_config["tool"]
    assert set(repos["market-data-platform"]["basedpyright"]["include_targets"]) == set(
        market_config["tool"]["basedpyright"]["include"]
    )
    assert set(repos["market-data-platform"]["ty"]["include_targets"]) == set(
        market_config["tool"]["ty"]["src"]["include"]
    )
    assert set(repos["portfolio-backtester"]["basedpyright"]["include_targets"]) == set(
        portfolio_config["tool"]["basedpyright"]["include"]
    )
    assert "extraPaths" not in portfolio_config["tool"]["basedpyright"]
    assert set(repos["portfolio-backtester"]["ty"]["include_targets"]) == set(
        portfolio_config["tool"]["ty"]["src"]["include"]
    )

    assert set(repos["quant-execution-engine"]["pyright"]["strict_targets"]) == set(
        execution_config["tool"]["maintainability"]["quality_targets"]["pyright_strict_targets"]
    )
    assert set(repos["quant-execution-engine"]["ty"]["include_targets"]) == set(
        execution_config["tool"]["ty"]["src"]["include"]
    )
    for record in manifest["broad_exclude_register"]:
        assert QUALITY_REGISTER_FIELDS <= set(record)
        assert record["coverage_patterns"]
    per_file_records = {
        (record["repo"], record["path"]): set(record["rules"])
        for record in manifest["per_file_ignore_register"]
    }
    cross_ignores = cross_config["tool"]["ruff"]["lint"].get("per-file-ignores", {})
    assert per_file_records == {
        ("cross-sectional-trees", path): set(rules) for path, rules in cross_ignores.items()
    }
    for record in manifest["per_file_ignore_register"]:
        assert PER_FILE_IGNORE_REGISTER_FIELDS <= set(record)
        assert record["tool"] == "ruff"


def test_quality_debt_budget_blocks_registered_increases() -> None:
    manifest = _load_json_doc("docs/quality-coverage-governance.yml")
    module = _load_quality_governance_module()
    mutated = copy.deepcopy(manifest)
    extra_record = copy.deepcopy(mutated["broad_exclude_register"][0])
    extra_record["path"] = "new broad quality exclude"
    mutated["broad_exclude_register"].append(extra_record)

    checks = module.check_quality_coverage(ROOT, mutated)

    assert any(
        check.severity == "ERROR"
        and check.code == "governance-quality"
        and "broad_exclude_register count" in check.message
        for check in checks
    )


def test_refactor_roadmap_covers_priority_and_baseline_large_files() -> None:
    roadmap = _load_json_doc("docs/maintainability-refactor-roadmap.yml")
    baseline = _load_json_doc(BASELINE_RELATIVE)
    planned = {record["path"] for record in roadmap["records"]}
    accepted = {record["path"] for record in roadmap["accepted_hotspots"]}

    assert roadmap["schema_version"] == "maintainability_refactor_roadmap.v1"
    assert REQUIRED_ROADMAP_PATHS <= planned
    for record in roadmap["records"]:
        assert {
            "path",
            "owner_repo",
            "risk",
            "first_safe_extraction",
            "target_layout",
            "focused_tests",
            "non_goals",
        } <= set(record)
    for record in roadmap["accepted_hotspots"]:
        assert {"path", "owner_repo", "reason", "next_action"} <= set(record)

    missing: list[str] = []
    for repo in baseline["repos"]:
        for file_record in repo["large_files"]:
            repo_path = file_record["path"]
            path = (
                repo_path if repo["repo"] == "research-workspace" else f"{repo['repo']}/{repo_path}"
            )
            if path not in planned and path not in accepted:
                missing.append(path)

    assert missing == []


def test_collaboration_docs_cover_maintainability_topics() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    pr_template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    owners = (ROOT / "CODEOWNERS").read_text(encoding="utf-8")
    combined = "\n".join([contributing, architecture, pr_template])

    assert "/market-data-platform/" in owners
    assert "/alpha-research/" in owners
    assert "/portfolio-backtester/" in owners
    assert "/cross-sectional-trees/" in owners
    assert "/quant-execution-engine/" in owners
    for phrase in (
        "deprecated surface",
        "one-off script",
        "Ruff",
        "Pyright",
        "mypy",
        "targets.json",
        "provider",
        "broker",
        "migration note",
        "focused",
    ):
        assert phrase in combined
    assert "Data platform" in pr_template
    assert "Strategy research" in pr_template
    assert "Trading execution" in pr_template
