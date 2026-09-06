from __future__ import annotations

import json
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_documentation_language.py"
SPEC = importlib.util.spec_from_file_location("audit_documentation_language", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

classify = MODULE.classify
count_characters = MODULE.count_characters
inventory = MODULE.inventory
language_class = MODULE.language_class


def test_classify_document_categories() -> None:
    assert classify(Path("README.md")) == "entry"
    assert classify(Path("docs/README.md")) == "index"
    assert classify(Path("docs/archive/old.md")) == "archive"
    assert classify(Path("docs/evidence/result.md")) == "evidence"
    assert classify(Path("docs/superpowers/plans/plan.md")) == "plan"
    assert classify(Path("docs/superpowers/specs/design.md")) == "spec"
    assert classify(Path("docs/concepts/model.md")) == "active"


def test_count_characters_ignores_code_for_language_classification() -> None:
    latin, han, code_lines = count_characters(
        "中文说明。\n\n```python\nprint('long executable example')\n```\n"
    )
    assert latin > 0
    assert han > 0
    assert code_lines == 1
    assert language_class(latin, han, code_lines) == "chinese-primary"


def test_inventory_has_stable_machine_readable_fields(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    document = tmp_path / "README.md"
    document.write_text("中文入口说明。\n", encoding="utf-8")

    result = inventory(tmp_path, [Path("README.md")])

    assert result["schema_version"] == 1
    assert result["document_count"] == 1
    record = result["documents"][0]
    assert record["path"] == "README.md"
    assert record["category"] == "entry"
    assert record["language"] == "chinese-primary"
    json.dumps(result, ensure_ascii=False)
