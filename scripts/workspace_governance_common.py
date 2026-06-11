"""Shared types for workspace governance checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    severity: str
    code: str
    message: str
