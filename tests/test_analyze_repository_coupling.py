from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_repository_coupling", ROOT / "scripts/analyze_repository_coupling.py"
)
assert SPEC is not None and SPEC.loader is not None
coupling = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = coupling
SPEC.loader.exec_module(coupling)


def fixtures(name: str) -> Path:
    return ROOT / "tests" / "fixtures" / name


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def initialize_repository(path: Path) -> None:
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "Coupling Test")
    git(path, "config", "user.email", "coupling@example.invalid")


def commit_file(repository: Path, relative_path: str, content: str, message: str) -> str:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    git(repository, "add", relative_path)
    git(repository, "commit", "-q", "-m", message)
    return git(repository, "rev-parse", "HEAD")


def test_report_separates_contract_and_local_changes() -> None:
    report = coupling.analyze_commits(fixtures("strategy-commits.json"))

    pair = report[("strategy-research", "strategy-app")]
    assert pair.co_change_count == 3
    assert pair.contract_change_count == 2
    assert pair.release_independence_count == 2


def test_report_counts_independent_releases_for_each_pair() -> None:
    report = coupling.analyze_commits(fixtures("strategy-commits.json"))

    pair = report[("strategy-app", "strategy-pipeline")]
    assert pair.co_change_count == 0
    assert pair.contract_change_count == 0
    assert pair.release_independence_count == 5
    assert pair.recommended_action == "keep-separate"


def test_contract_dominated_pair_strengthens_contracts_instead_of_merging() -> None:
    report = coupling.analyze_commits(fixtures("strategy-commits.json"))

    pair = report[("strategy-research", "strategy-app")]
    assert pair.recommended_action == "keep-separate-strengthen-contracts"
    assert pair.evidence == (
        "1111111 2026-01-10 contract update strategy catalog contract",
        "2222222 2026-02-10 contract align publication schema",
        "3333333 2026-03-10 local refresh local documentation",
    )


def test_partial_path_metadata_is_unclassified_even_when_available_side_is_contract() -> None:
    metadata = coupling.CouplingMetadata(
        repositories=("repository-a", "repository-b"),
        period="12.months..HEAD",
        commits=(
            coupling.CommitMetadata(
                commit="abc123",
                date="2026-09-06",
                subject="joint update with one unavailable object",
                changes={
                    "repository-a": ("contracts/catalog.json",),
                    "repository-b": (),
                },
                complete_repositories=frozenset({"repository-a"}),
            ),
        ),
    )

    pair = coupling.analyze_metadata(metadata)[("repository-a", "repository-b")]

    assert pair.contract_change_count == 0
    assert pair.evidence == (
        "abc123 2026-09-06 unclassified joint update with one unavailable object",
    )


def test_independent_releases_change_recommendation_and_rationale() -> None:
    concentrated = coupling._recommend(
        co_change_count=4,
        contract_change_count=1,
        release_independence_count=0,
    )
    independent = coupling._recommend(
        co_change_count=4,
        contract_change_count=1,
        release_independence_count=5,
    )

    assert concentrated == (
        "keep-separate-pending-merge-prerequisites",
        "4 joint updates versus 0 independent updates indicate concentrated coupling, "
        "but Git metadata cannot prove atomic PR changes or matching visibility",
    )
    assert independent == (
        "keep-separate",
        "5 independent updates outweigh 4 joint updates",
    )


def test_markdown_exposes_required_fields_and_method_limit() -> None:
    report = coupling.analyze_commits(fixtures("strategy-commits.json"))

    markdown = coupling.render_markdown(report)

    for field in (
        "repositories",
        "period",
        "co_change_count",
        "contract_change_count",
        "release_independence_count",
        "recommended_action",
        "evidence",
    ):
        assert field in markdown
    assert "Git metadata" in markdown
    assert "visibility" in markdown
    assert "5 independent updates outweigh 0 joint updates" in markdown
    assert "6666666 2026-06-10 independent strategy-pipeline improve orchestration" in markdown


def test_collect_git_metadata_reads_gitlinks_and_nested_changed_paths(
    tmp_path: Path,
) -> None:
    repository_a = tmp_path / "repository-a"
    repository_b = tmp_path / "repository-b"
    initialize_repository(repository_a)
    initialize_repository(repository_b)
    commit_file(repository_a, "local.py", "a = 1\n", "initial a")
    commit_file(repository_b, "local.py", "b = 1\n", "initial b")

    workspace = tmp_path / "workspace"
    initialize_repository(workspace)
    git(
        workspace,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-q",
        str(repository_a),
        "repository-a",
    )
    git(
        workspace,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-q",
        str(repository_b),
        "repository-b",
    )
    git(workspace, "commit", "-q", "-m", "initial workspace")

    next_a = commit_file(
        repository_a,
        "contracts/catalog.json",
        "{}\n",
        "add catalog contract",
    )
    next_b = commit_file(repository_b, "local.py", "b = 2\n", "change local b")
    git(workspace / "repository-a", "fetch", "-q", "origin")
    git(workspace / "repository-a", "checkout", "-q", next_a)
    git(workspace / "repository-b", "fetch", "-q", "origin")
    git(workspace / "repository-b", "checkout", "-q", next_b)
    git(workspace, "add", "repository-a", "repository-b")
    git(workspace, "commit", "-q", "-m", "joint update")

    final_b = commit_file(repository_b, "local.py", "b = 3\n", "another local b")
    git(workspace / "repository-b", "fetch", "-q", "origin")
    git(workspace / "repository-b", "checkout", "-q", final_b)
    git(workspace, "add", "repository-b")
    git(workspace, "commit", "-q", "-m", "independent b update")

    metadata = coupling.collect_git_metadata(
        workspace,
        repositories=("repository-a", "repository-b"),
        since="12.months",
    )
    report = coupling.analyze_metadata(metadata)

    pair = report[("repository-a", "repository-b")]
    assert pair.co_change_count == 1
    assert pair.contract_change_count == 1
    assert pair.release_independence_count == 1
    assert pair.evidence[0].endswith("contract joint update")


def test_analyze_commits_rejects_unlisted_repository_change(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text(
        '{"period":"2026-01-01..2026-02-01","repositories":["a","b"],'
        '"commits":[{"commit":"abc","date":"2026-01-02","subject":"change",'
        '"changes":{"private-data":["results.csv"]}}]}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unlisted repository"):
        coupling.analyze_commits(fixture)
