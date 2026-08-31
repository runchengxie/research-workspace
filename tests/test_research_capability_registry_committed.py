from pathlib import Path

from scripts.research_capability_registry_check import validate_registry


def test_committed_registry_is_valid_against_pinned_workspace() -> None:
    root = Path(__file__).resolve().parents[1]
    result = validate_registry(
        root / "docs/research-capabilities.yml",
        root=root,
    )
    assert result.ok, result.issues
    assert result.capability_count > 0
