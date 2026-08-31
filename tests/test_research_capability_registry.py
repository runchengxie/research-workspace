from __future__ import annotations

from pathlib import Path

import yaml

from src.research_contracts.research_capability_registry import validate_registry


def _capability(
    capability_id: str = "alpha.example",
    *,
    owner: str = "alpha-research",
    source_path: str = "src/alpha_research/example.py",
    evidence_refs: list[str] | None = None,
    requires: list[str] | None = None,
    maturity: str = "verified",
) -> dict:
    return {
        "capability_id": capability_id,
        "summary": "用于测试 capability registry 的真实 owner 能力。",
        "owner_repository": owner,
        "stage": "validation",
        "kind": "validation",
        "maturity": maturity,
        "canonical_entrypoint": {
            "type": "python",
            "value": "alpha_research.example.run",
            "source_path": source_path,
        },
        "inputs": ["input"],
        "outputs": ["output"],
        "requires": requires or [],
        "method_refs": [],
        "evidence_refs": evidence_refs or ["tests/test_example.py"],
    }


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    owner = root / "alpha-research"
    (owner / "src/alpha_research").mkdir(parents=True)
    (owner / "tests").mkdir(parents=True)
    (owner / "src/alpha_research/example.py").write_text("def run(): return 1\n")
    (owner / "tests/test_example.py").write_text("def test_example(): assert True\n")
    return root


def _write_registry(root: Path, capabilities: list[dict]) -> Path:
    path = root / "registry.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "research_capability_registry.v1",
                "capabilities": capabilities,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_valid_registry_passes(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = validate_registry(_write_registry(root, [_capability()]), root=root)
    assert result.ok, result.issues


def test_duplicate_capability_id_is_rejected(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    capability = _capability()
    result = validate_registry(
        _write_registry(root, [capability, dict(capability)]),
        root=root,
    )
    assert any("duplicate capability_id" in issue for issue in result.issues)


def test_unknown_owner_is_rejected(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = validate_registry(
        _write_registry(root, [_capability(owner="imaginary-owner")]),
        root=root,
    )
    assert any("owner_repository" in issue for issue in result.issues)


def test_missing_dependency_is_rejected(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = validate_registry(
        _write_registry(root, [_capability(requires=["alpha.missing"])]),
        root=root,
    )
    assert any("requires" in issue and "alpha.missing" in issue for issue in result.issues)


def test_dependency_cycle_is_rejected(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    first = _capability("alpha.first", requires=["alpha.second"])
    second = _capability("alpha.second", requires=["alpha.first"])
    result = validate_registry(_write_registry(root, [first, second]), root=root)
    assert any("cycle" in issue.lower() for issue in result.issues)


def test_missing_source_path_is_rejected_for_runnable_capability(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = validate_registry(
        _write_registry(root, [_capability(source_path="src/alpha_research/missing.py")]),
        root=root,
    )
    assert any("source_path" in issue for issue in result.issues)


def test_verified_capability_requires_existing_test_evidence(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = validate_registry(
        _write_registry(root, [_capability(evidence_refs=["docs/example.md"])]),
        root=root,
    )
    assert any("verified" in issue and "test" in issue for issue in result.issues)


def test_private_source_path_is_rejected(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    private = root / "alpha-research/src/alpha_research/_private.py"
    private.write_text("def run(): return 1\n")
    capability = _capability(source_path="src/alpha_research/_private.py")
    capability["canonical_entrypoint"]["value"] = "alpha_research._private.run"
    result = validate_registry(_write_registry(root, [capability]), root=root)
    assert any("private" in issue.lower() for issue in result.issues)


def test_owner_path_cannot_escape_owner_repository(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    escaped = _capability(source_path="../outside.py")
    result = validate_registry(_write_registry(root, [escaped]), root=root)
    assert any("escape" in issue.lower() for issue in result.issues)
