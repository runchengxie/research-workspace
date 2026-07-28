"""Shared types for workspace governance checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeGuard


@dataclass(frozen=True)
class Check:
    severity: str
    code: str
    message: str


def valid_budget_limit(value: Any) -> TypeGuard[int]:
    """预算上限必须是非负整数（排除布尔值）。"""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
