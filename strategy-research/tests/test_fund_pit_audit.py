from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from experiments.macro_context_shadow.fund_pit_audit import run_audit


def test_audit_requires_the_expected_asset_layout(tmp_path: Path) -> None:
    with pytest.raises(duckdb.IOException):
        run_audit(tmp_path)
