#!/usr/bin/env python3
"""No-write contract smoke checks for the workspace layer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workspace_doctor import resolve_public_command

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_MANIFEST = ROOT / "docs" / "artifact-contracts.yml"
CONTRACT_DOC = ROOT / "docs" / "contracts.md"
REQUIRED_CORE_ARTIFACTS = {
    "signals.parquet",
    "signals.meta.json",
    "positions_by_rebalance.csv",
    "targets.json",
}
KNOWN_REPOS = {
    "alpha-research",
    "market-data-platform",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
}


@dataclass(frozen=True)
class SmokeResult:
    severity: str
    name: str
    message: str


def _module_command(root: Path, submodule: str, module: str) -> tuple[list[str], dict[str, str]]:
    repo = root / submodule
    python_candidates = [
        repo / ".venv" / "bin" / "python",
        repo / ".venv" / "Scripts" / "python.exe",
    ]
    python = next((candidate for candidate in python_candidates if candidate.is_file()), None)
    if python is None:
        raise FileNotFoundError(f"No virtualenv Python found for {submodule}")
    command = [str(python), "-m", module]
    env = dict(os.environ)
    source_root = repo / "src"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{source_root}{os.pathsep}{existing}" if existing else str(source_root)
    return command, env


def _command_for(
    root: Path,
    submodule: str,
    executable: str,
    module: str,
) -> tuple[list[str], dict[str, str]] | None:
    resolved = resolve_public_command(root, submodule, executable)
    if resolved:
        return [resolved], dict(os.environ)
    source_root = root / submodule / "src"
    if source_root.is_dir():
        try:
            return _module_command(root, submodule, module)
        except FileNotFoundError:
            return None
    return None


def _run(
    name: str,
    command: list[str],
    *,
    env: dict[str, str],
    timeout: int,
) -> SmokeResult:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            env=env,
            timeout=timeout,
        )
    except (FileNotFoundError, PermissionError) as exc:
        return SmokeResult("ERROR", name, str(exc))
    if completed.returncode == 0:
        return SmokeResult("OK", name, "passed")
    detail = (completed.stderr or completed.stdout).strip().splitlines()
    message = detail[-1] if detail else f"exit code {completed.returncode}"
    return SmokeResult("ERROR", name, message)


def _skip(name: str, message: str) -> SmokeResult:
    return SmokeResult("WARN", name, message)


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value.strip()]


def _docs_sync_issues(record: dict[str, Any], docs_text: str) -> list[str]:
    issues: list[str] = []
    artifact = str(record.get("artifact", "")).strip()
    contract = str(record.get("contract", "")).strip()
    owner = str(record.get("owner", "")).strip()
    expected_tokens = [
        (artifact, f"{artifact}: missing from docs/contracts.md"),
        (contract, f"{artifact}: contract {contract!r} missing from docs/contracts.md"),
        (owner, f"{artifact}: owner {owner!r} missing from docs/contracts.md"),
    ]
    for token, message in expected_tokens:
        if token and token not in docs_text:
            issues.append(message)
    for file_name in _strings(record.get("canonical_files")):
        if file_name not in docs_text:
            issues.append(f"{artifact}: canonical file {file_name!r} missing from docs")
    return issues


def _entrypoint_issues(root: Path, artifact: str, entrypoints: object) -> list[str]:
    if not isinstance(entrypoints, list) or not entrypoints:
        return [f"{artifact}: entrypoints must be non-empty"]

    issues: list[str] = []
    for entrypoint in entrypoints:
        if not isinstance(entrypoint, dict):
            issues.append(f"{artifact}: entrypoint must be an object")
            continue
        repo = str(entrypoint.get("repo", "")).strip()
        path = str(entrypoint.get("path", "")).strip()
        if repo not in KNOWN_REPOS:
            issues.append(f"{artifact}: unknown entrypoint repo {repo!r}")
        if not path:
            issues.append(f"{artifact}: entrypoint path is required")
        elif repo in KNOWN_REPOS and not (root / repo / path).is_file():
            issues.append(f"{artifact}: missing entrypoint path {repo}/{path}")
    return issues


def _artifact_record_issues(
    root: Path,
    record: object,
    docs_text: str,
    seen: set[str],
) -> list[str]:
    if not isinstance(record, dict):
        return ["artifact record must be an object"]

    artifact = str(record.get("artifact", "")).strip()
    contract = str(record.get("contract", "")).strip()
    owner = str(record.get("owner", "")).strip()
    if not artifact:
        return ["artifact is required"]

    issues: list[str] = []
    if artifact in seen:
        issues.append(f"{artifact}: duplicate artifact")
    seen.add(artifact)
    if not contract:
        issues.append(f"{artifact}: contract is required")
    if owner not in KNOWN_REPOS:
        issues.append(f"{artifact}: unknown owner {owner!r}")
    if not _strings(record.get("required_fields")):
        issues.append(f"{artifact}: required_fields must be non-empty")
    issues.extend(_docs_sync_issues(record, docs_text))
    issues.extend(_entrypoint_issues(root, artifact, record.get("entrypoints")))
    return issues


def _artifact_contract_manifest_check(root: Path) -> SmokeResult:
    manifest_path = root / CONTRACT_MANIFEST.relative_to(ROOT)
    contract_doc = root / CONTRACT_DOC.relative_to(ROOT)
    try:
        manifest = _load_manifest(manifest_path)
        docs_text = contract_doc.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return SmokeResult("ERROR", "artifact contract manifest", str(exc))

    if manifest.get("schema_version") != "artifact_contracts.v1":
        return SmokeResult("ERROR", "artifact contract manifest", "unexpected schema_version")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return SmokeResult("ERROR", "artifact contract manifest", "artifacts must be non-empty")

    seen: set[str] = set()
    issues: list[str] = []
    for record in artifacts:
        issues.extend(_artifact_record_issues(root, record, docs_text, seen))
    missing = sorted(REQUIRED_CORE_ARTIFACTS - seen)
    if missing:
        issues.append("missing core artifacts: " + ", ".join(missing))
    if issues:
        return SmokeResult("ERROR", "artifact contract manifest", "; ".join(issues))
    return SmokeResult("OK", "artifact contract manifest", "passed")


def run_smoke(root: Path, timeout: int) -> list[SmokeResult]:
    root = root.resolve()
    results: list[SmokeResult] = [_artifact_contract_manifest_check(root)]

    marketdata = _command_for(
        root,
        "market-data-platform",
        "marketdata",
        "market_data_platform.cli",
    )
    if marketdata is None:
        results.append(_skip("marketdata", "marketdata CLI is unavailable"))
    else:
        base, env = marketdata
        results.append(
            _run(
                "marketdata migration freeze-hk help",
                [*base, "migration", "freeze-hk", "--help"],
                env=env,
                timeout=timeout,
            )
        )
        results.append(
            _run(
                "marketdata migration hydrate-hk help",
                [*base, "migration", "hydrate-hk", "--help"],
                env=env,
                timeout=timeout,
            )
        )
        results.append(
            _run(
                "marketdata paths a-share",
                [*base, "paths", "--market", "a_share", "--json"],
                env=env,
                timeout=timeout,
            )
        )
        with tempfile.TemporaryDirectory(prefix="rw-contract-smoke-") as tmp:
            results.append(
                _run(
                    "marketdata contract dry-run",
                    [
                        *base,
                        "contract",
                        "build",
                        "--market",
                        "a_share",
                        "--artifacts-root",
                        tmp,
                        "--dry-run",
                        "--no-registry",
                    ],
                    env=env,
                    timeout=timeout,
                )
            )

    cstree = _command_for(root, "strategy-pipeline", "cstree", "cstree")
    if cstree is None:
        results.append(_skip("cstree export-targets help", "cstree CLI is unavailable"))
    else:
        base, env = cstree
        results.append(
            _run(
                "cstree export-targets help",
                [*base, "export-targets", "--help"],
                env=env,
                timeout=timeout,
            )
        )

    qexec = _command_for(root, "quant-execution-engine", "qexec", "quant_execution_engine")
    if qexec is None:
        results.append(_skip("qexec rebalance help", "qexec CLI is unavailable"))
    else:
        base, env = qexec
        results.append(
            _run(
                "qexec rebalance help",
                [*base, "rebalance", "--help"],
                env=env,
                timeout=timeout,
            )
        )

    return results


def render_results(results: list[SmokeResult]) -> str:
    lines = [f"[{result.severity}] {result.name}: {result.message}" for result in results]
    errors = sum(1 for result in results if result.severity == "ERROR")
    warnings = sum(1 for result in results if result.severity == "WARN")
    lines.append(f"Summary: errors={errors} warnings={warnings}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run no-write workspace contract smoke checks.")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat skipped unavailable CLIs as failures.",
    )
    args = parser.parse_args(argv)

    results = run_smoke(Path(args.root), timeout=args.timeout)
    print(render_results(results))
    has_errors = any(result.severity == "ERROR" for result in results)
    has_warnings = any(result.severity == "WARN" for result in results)
    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
