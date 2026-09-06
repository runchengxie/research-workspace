#!/usr/bin/env python3
"""Build a reproducible language inventory for tracked Markdown documents."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path

EXCLUDED_PARTS = {".git", ".pytest_cache", ".venv", "build", "dist"}
ENTRY_NAMES = {"README.md", "AGENTS.md"}


def tracked_markdown(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--", "*.md"],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for value in result.stdout.splitlines():
        path = Path(value)
        if path.suffix != ".md" or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


def classify(path: Path) -> str:
    parts = path.parts
    if path.name in ENTRY_NAMES and len(parts) <= 1:
        return "entry"
    if path.name == "README.md":
        return "index"
    if "archive" in parts:
        return "archive"
    if "evidence" in parts or "reports" in parts:
        return "evidence"
    if "plans" in parts:
        return "plan"
    if "specs" in parts:
        return "spec"
    return "active"


def count_characters(text: str) -> tuple[int, int, int]:
    latin = sum(character.isascii() and character.isalpha() for character in text)
    han = sum("\u3400" <= character <= "\u9fff" for character in text)
    code_lines = 0
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines += 1
    return latin, han, code_lines


def language_class(latin: int, han: int, code_lines: int) -> str:
    if latin >= 300 and han == 0 and code_lines == 0:
        return "english-primary"
    if latin >= 300 and han == 0:
        return "code-heavy"
    if latin >= 300 and han < 100:
        return "mixed"
    return "chinese-primary"


def inventory(root: Path, paths: Iterable[Path] | None = None) -> dict[str, object]:
    selected = list(paths) if paths is not None else tracked_markdown(root)
    documents: list[dict[str, object]] = []
    for relative in selected:
        text = (root / relative).read_text(encoding="utf-8")
        latin, han, code_lines = count_characters(text)
        documents.append(
            {
                "path": relative.as_posix(),
                "category": classify(relative),
                "latin_characters": latin,
                "han_characters": han,
                "code_lines": code_lines,
                "language": language_class(latin, han, code_lines),
            }
        )
    return {
        "schema_version": 1,
        "root": str(root),
        "document_count": len(documents),
        "documents": documents,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", dest="json_path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = inventory(args.root.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
