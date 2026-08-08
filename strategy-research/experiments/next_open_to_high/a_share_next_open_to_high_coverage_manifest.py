from __future__ import annotations

from pathlib import Path


def coverage_manifest_for_minute_root(minute_root: Path, *, data_root: Path) -> Path:
    """Pair the canonical alias target with its versioned coverage receipt."""
    version_name = minute_root.expanduser().resolve().name
    return data_root / "metadata/minute_fusion" / f"a_share_{version_name}.coverage.json"
