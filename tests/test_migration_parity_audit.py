from pathlib import Path

from migration_parity_audit import build_inventory, collect_python_symbols, compare_inventories


def test_inventory_excludes_generated_directories_and_counts_loc(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "src" / "sample.py").write_text("class Example:\n\n    def run(self):\n        return 1\n", encoding="utf-8")
    (tmp_path / "src" / "guide.md").write_text("# Guide\n\nText\n", encoding="utf-8")
    (tmp_path / ".venv" / "ignored.py").write_text("ignored = True\n", encoding="utf-8")

    inventory = build_inventory(tmp_path)

    assert inventory["summary"] == {
        "files": 2,
        "python_files": 1,
        "python_loc": 4,
        "python_nonblank_loc": 3,
        "markdown_files": 1,
        "markdown_loc": 3,
        "markdown_nonblank_loc": 2,
    }


def test_ast_inventory_extracts_nested_symbols(tmp_path: Path):
    path = tmp_path / "sample.py"
    path.write_text(
        "async def top():\n    class Inner:\n        def method(self):\n            pass\n",
        encoding="utf-8",
    )

    assert collect_python_symbols(path) == [
        {"kind": "function", "name": "top", "line": 1},
        {"kind": "class", "name": "top.Inner", "line": 2},
        {"kind": "function", "name": "top.Inner.method", "line": 3},
    ]


def test_compare_reports_paths_and_heuristic_basename_candidates(tmp_path: Path):
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    (old_root / "old_name.py").write_text("def same():\n    return 1\n", encoding="utf-8")
    (new_root / "old_name.py").write_text("def same():\n    return 1\n", encoding="utf-8")
    (old_root / "missing.md").write_text("missing\n", encoding="utf-8")

    old = build_inventory(old_root)
    new = build_inventory(new_root)
    comparison = compare_inventories(old, [new])

    assert comparison["exact_path_matches"] == ["old_name.py"]
    assert comparison["exact_hash_matches"] == ["old_name.py"]
    assert comparison["old_paths_absent"] == ["missing.md"]
    assert comparison["basename_candidates"] == ["old_name.py"]
    assert comparison["old_symbol_names_absent_globally"] == []
