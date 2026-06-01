from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scan_workspace_secrets.py"

spec = importlib.util.spec_from_file_location("scan_workspace_secrets", SCRIPT)
scan_workspace_secrets = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = scan_workspace_secrets
spec.loader.exec_module(scan_workspace_secrets)


def test_secret_scan_rejects_root_owned_credential_assignment(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "leak.md").write_text(
        "API_" + "KEY=abcdefghijklmnop\n",
        encoding="utf-8",
    )

    result = scan_workspace_secrets.scan_superproject(tmp_path)

    assert result["status"] == "failed"
    assert result["issues"] == [
        {"path": "docs/leak.md", "check": "credential_assignment"},
    ]
