#!/usr/bin/env python3
"""No-write contract smoke checks for the workspace layer."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_MANIFEST = ROOT / "docs" / "artifact-contracts.yml"
CONTRACT_DOC = ROOT / "docs" / "contracts.md"


@dataclass(frozen=True)
class SmokeResult:
    severity: str
    name: str
    message: str


def _public_command_candidates(root: Path, submodule_path: str, command: str) -> list[Path]:
    repo = root / submodule_path
    return [
        repo / ".venv" / "bin" / command,
        repo / ".venv" / "Scripts" / f"{command}.exe",
    ]


def _has_valid_shebang(path: Path) -> bool:
    try:
        first_line = path.read_bytes().splitlines()[0].decode("utf-8", errors="ignore")
    except (IndexError, OSError):
        return False
    if not first_line.startswith("#!"):
        return True
    interpreter = first_line[2:].strip().split(" ", 1)[0]
    if interpreter == "/usr/bin/env":
        return True
    if interpreter.startswith("/"):
        return Path(interpreter).exists()
    return True


def _resolve_public_command(root: Path, submodule_path: str, command: str) -> str | None:
    for candidate in _public_command_candidates(root, submodule_path, command):
        if candidate.is_file() and os.access(candidate, os.X_OK) and _has_valid_shebang(candidate):
            return str(candidate)
    return shutil.which(command)


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
    resolved = _resolve_public_command(root, submodule, executable)
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


def _artifact_contract_manifest_check(root: Path) -> SmokeResult:
    contracts_src = ROOT / "src"
    if str(contracts_src) not in sys.path:
        sys.path.insert(0, str(contracts_src))
    from research_contracts import validate_artifact_contract_manifest

    result = validate_artifact_contract_manifest(
        root=root,
        manifest_path=root / CONTRACT_MANIFEST.relative_to(ROOT),
        docs_path=root / CONTRACT_DOC.relative_to(ROOT),
    )
    if not result.ok:
        return SmokeResult("ERROR", "artifact contract manifest", "; ".join(result.issues))
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
