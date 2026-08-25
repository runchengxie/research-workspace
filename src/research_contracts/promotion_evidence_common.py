"""Shared primitives for canonical strategy promotion evidence."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def date_token(value: object) -> str | None:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits[:8] if len(digits) >= 8 else None


def safe_relative(root: Path, value: object) -> tuple[Path | None, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, None
    relative = Path(text)
    if relative.is_absolute():
        return None, None
    base = root.expanduser().resolve()
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return None, None
    return resolved, relative.as_posix()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def hash_matches(entry: object, *, root: Path) -> bool:
    payload = mapping(entry)
    path, _relative = safe_relative(root, payload.get("path"))
    expected = str(payload.get("sha256") or "").strip()
    return bool(
        path is not None
        and SHA256.fullmatch(expected)
        and sha256_file(path) == expected
    )


def append_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def finite_number(
    value: object,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    if not math.isfinite(number):
        return False
    if positive:
        return number > 0
    if nonnegative:
        return number >= 0
    return True
