#!/usr/bin/env python3
"""Measure repository coupling from superproject Git metadata."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
CONTRACT_PARTS = {"contract", "contracts", "schema", "schemas"}
CONTRACT_FILES = {
    "catalog.json",
    "research-run.manifest.json",
    "selection_receipt.json",
    "targets.json",
    "watchlist_20.csv",
}


@dataclass(frozen=True)
class CommitMetadata:
    commit: str
    date: str
    subject: str
    changes: Mapping[str, tuple[str, ...]]
    complete_repositories: frozenset[str]


@dataclass(frozen=True)
class CouplingMetadata:
    repositories: tuple[str, ...]
    period: str
    commits: tuple[CommitMetadata, ...]


@dataclass(frozen=True)
class PairReport:
    repositories: tuple[str, str]
    period: str
    co_change_count: int
    contract_change_count: int
    release_independence_count: int
    recommended_action: str
    recommendation_rationale: str
    evidence: tuple[str, ...]
    independent_evidence: tuple[str, ...]


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _repository_names(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("repositories must contain at least two names")
    names = tuple(_require_string(item, "repository") for item in value)
    if len(set(names)) != len(names):
        raise ValueError("repositories must not contain duplicates")
    return names


def _changed_paths(value: Any, repository: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(path, str) for path in value):
        raise ValueError(f"changes for {repository!r} must be a list of paths")
    return tuple(value)


def _parse_commit(value: Any, repositories: tuple[str, ...]) -> CommitMetadata:
    if not isinstance(value, dict) or not isinstance(value.get("changes"), dict):
        raise ValueError("each commit must contain a changes object")
    unknown = set(value["changes"]) - set(repositories)
    if unknown:
        raise ValueError(f"commit contains unlisted repository: {sorted(unknown)[0]}")
    changes = {
        repository: _changed_paths(paths, repository)
        for repository, paths in value["changes"].items()
    }
    return CommitMetadata(
        commit=_require_string(value.get("commit"), "commit"),
        date=_require_string(value.get("date"), "date"),
        subject=_require_string(value.get("subject"), "subject"),
        changes=changes,
        complete_repositories=frozenset(changes),
    )


def load_metadata(path: Path) -> CouplingMetadata:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read coupling metadata: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("commits"), list):
        raise ValueError("coupling metadata must contain a commits list")
    repositories = _repository_names(value.get("repositories"))
    return CouplingMetadata(
        repositories=repositories,
        period=_require_string(value.get("period"), "period"),
        commits=tuple(_parse_commit(commit, repositories) for commit in value["commits"]),
    )


def _is_contract_path(path: str) -> bool:
    candidate = PurePosixPath(path.lower())
    return (
        bool(CONTRACT_PARTS.intersection(candidate.parts))
        or candidate.name in CONTRACT_FILES
        or candidate.name.endswith(".schema.json")
        or "contract" in candidate.stem
    )


def _joint_classification(commit: CommitMetadata, pair: tuple[str, str]) -> str:
    if not set(pair).issubset(commit.complete_repositories):
        return "unclassified"
    paths = commit.changes[pair[0]] + commit.changes[pair[1]]
    if any(_is_contract_path(path) for path in paths):
        return "contract"
    return "local"


def _recommend(
    *, co_change_count: int, contract_change_count: int, release_independence_count: int
) -> tuple[str, str]:
    if co_change_count and contract_change_count * 2 >= co_change_count:
        return (
            "keep-separate-strengthen-contracts",
            f"{contract_change_count} of {co_change_count} joint updates are contract-related; "
            f"{release_independence_count} independent updates were also observed",
        )
    if release_independence_count > co_change_count:
        return (
            "keep-separate",
            f"{release_independence_count} independent updates outweigh "
            f"{co_change_count} joint updates",
        )
    if co_change_count >= 3:
        return (
            "keep-separate-pending-merge-prerequisites",
            f"{co_change_count} joint updates versus {release_independence_count} independent "
            "updates indicate concentrated coupling, but Git metadata cannot prove atomic PR "
            "changes or matching visibility",
        )
    return (
        "keep-separate",
        f"{co_change_count} joint updates do not establish sustained coupling; "
        f"{release_independence_count} independent updates were observed",
    )


def analyze_metadata(metadata: CouplingMetadata) -> dict[tuple[str, str], PairReport]:
    report: dict[tuple[str, str], PairReport] = {}
    for pair in combinations(metadata.repositories, 2):
        joint = [commit for commit in metadata.commits if set(pair) <= set(commit.changes)]
        independent = [
            commit
            for commit in metadata.commits
            if (pair[0] in commit.changes) != (pair[1] in commit.changes)
        ]
        classifications = tuple(_joint_classification(commit, pair) for commit in joint)
        contract_count = classifications.count("contract")
        evidence = tuple(
            f"{commit.commit[:12]} {commit.date} {classification} {commit.subject}"
            for commit, classification in zip(joint, classifications, strict=True)
        )
        independent_evidence = tuple(
            f"{commit.commit[:12]} {commit.date} independent "
            f"{pair[0] if pair[0] in commit.changes else pair[1]} {commit.subject}"
            for commit in independent
        )
        recommended_action, rationale = _recommend(
            co_change_count=len(joint),
            contract_change_count=contract_count,
            release_independence_count=len(independent),
        )
        report[pair] = PairReport(
            repositories=pair,
            period=metadata.period,
            co_change_count=len(joint),
            contract_change_count=contract_count,
            release_independence_count=len(independent),
            recommended_action=recommended_action,
            recommendation_rationale=rationale,
            evidence=evidence,
            independent_evidence=independent_evidence,
        )
    return report


def analyze_commits(path: Path) -> dict[tuple[str, str], PairReport]:
    return analyze_metadata(load_metadata(path))


def _run_git(repository: Path, arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise RuntimeError(detail)
    return result.stdout


def _validate_gitlinks(root: Path, repositories: tuple[str, ...]) -> None:
    for repository in repositories:
        path = PurePosixPath(repository)
        if path.is_absolute() or ".." in path.parts or str(path) != repository:
            raise ValueError(f"invalid repository path: {repository!r}")
        entry = _run_git(root, ("ls-tree", "HEAD", "--", repository)).strip()
        if not entry.startswith("160000 commit "):
            raise ValueError(f"repository is not a gitlink at HEAD: {repository!r}")


def _commit_header(root: Path, commit: str) -> tuple[str, str, str]:
    fields = _run_git(root, ("show", "-s", "--format=%H%x00%cs%x00%s", commit)).strip()
    parsed = fields.split("\0", 2)
    if len(parsed) != 3:
        raise RuntimeError(f"cannot parse Git metadata for commit {commit}")
    return parsed[0], parsed[1], parsed[2]


def _parent(root: Path, commit: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), "rev-parse", "--verify", f"{commit}^"),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else EMPTY_TREE


def _gitlink_changes(
    root: Path, parent: str, commit: str, repositories: tuple[str, ...]
) -> dict[str, tuple[str, str]]:
    raw = _run_git(root, ("diff-tree", "-r", "--raw", parent, commit, "--", *repositories))
    changes: dict[str, tuple[str, str]] = {}
    for line in raw.splitlines():
        metadata, separator, path = line.partition("\t")
        fields = metadata.split()
        if separator and path in repositories and len(fields) >= 5 and fields[0] == ":160000":
            changes[path] = (fields[2], fields[3])
    return changes


def _nested_paths(root: Path, repository: str, old: str, new: str) -> tuple[str, ...] | None:
    if old == "0" * 40 or new == "0" * 40:
        return None
    result = subprocess.run(
        ("git", "-C", str(root / repository), "diff", "--name-only", old, new),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return tuple(path for path in result.stdout.splitlines() if path)


def _collect_commit(
    root: Path, commit: str, repositories: tuple[str, ...]
) -> CommitMetadata | None:
    gitlinks = _gitlink_changes(root, _parent(root, commit), commit, repositories)
    if not gitlinks:
        return None
    commit_id, date, subject = _commit_header(root, commit)
    changes: dict[str, tuple[str, ...]] = {}
    complete: set[str] = set()
    for repository, (old, new) in gitlinks.items():
        paths = _nested_paths(root, repository, old, new)
        changes[repository] = paths or ()
        if paths is not None:
            complete.add(repository)
    return CommitMetadata(
        commit=commit_id,
        date=date,
        subject=subject,
        changes=changes,
        complete_repositories=frozenset(complete),
    )


def collect_git_metadata(
    root: Path, *, repositories: tuple[str, ...], since: str
) -> CouplingMetadata:
    if len(repositories) < 2 or len(set(repositories)) != len(repositories):
        raise ValueError("at least two unique repositories are required")
    _validate_gitlinks(root, repositories)
    revisions = _run_git(
        root,
        ("rev-list", "--first-parent", f"--since={since}", "HEAD", "--", *repositories),
    ).splitlines()
    commits = tuple(
        item
        for revision in revisions
        if (item := _collect_commit(root, revision, repositories)) is not None
    )
    return CouplingMetadata(
        repositories=repositories,
        period=f"{since}..HEAD",
        commits=commits,
    )


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def render_markdown(report: Mapping[tuple[str, str], PairReport]) -> str:
    rows = []
    for pair in report.values():
        all_evidence = pair.evidence + pair.independent_evidence
        evidence = "<br>".join(all_evidence) if all_evidence else "none"
        rows.append(
            "| "
            + " | ".join(
                (
                    " + ".join(pair.repositories),
                    pair.period,
                    str(pair.co_change_count),
                    str(pair.contract_change_count),
                    str(pair.release_independence_count),
                    pair.recommended_action,
                    pair.recommendation_rationale,
                    _escape_table(evidence),
                )
            )
            + " |"
        )
    merge_recommendations = [
        pair for pair in report.values() if not pair.recommended_action.startswith("keep-separate")
    ]
    conclusion = (
        "存在进入合并试点的仓库对。"
        if merge_recommendations
        else "当前 Git 证据不支持合并，建议保持独立仓库。"
    )
    return "\n".join(
        (
            "# 策略仓库共同变更证据",
            "",
            "## 结论",
            "",
            conclusion,
            "",
            "## 结果",
            "",
            "| repositories | period | co_change_count | contract_change_count | "
            "release_independence_count | recommended_action | recommendation_rationale | "
            "evidence |",
            "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
            *rows,
            "",
            "## 方法与边界",
            "",
            "分析只使用 superproject 与 submodule 的 Git metadata，包括提交标识、日期、主题、"
            "gitlink 变更和变更路径。",
            "共同变更表示同一个 superproject 提交更新一对 gitlink，独立发布表示只更新其中"
            "一个 gitlink。",
            "路径含 contract、schema 或已登记 artifact 文件名时记为契约变更；无法读取 "
            "submodule 对象时记为 unclassified。",
            "Git metadata 不能证明跨仓修改必须位于同一 PR，也不能证明 repository visibility "
            "一致。缺少这两项证据时不建议合并。",
            "分析不读取文件内容、研究数据、运行产物、远端 API、环境变量、凭证或生产配置。",
            "",
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repositories", nargs="+", required=True)
    parser.add_argument("--since", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        metadata = collect_git_metadata(
            args.repository_root,
            repositories=tuple(args.repositories),
            since=args.since,
        )
        markdown = render_markdown(analyze_metadata(metadata))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
