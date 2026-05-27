from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workspace_doctor.py"

spec = importlib.util.spec_from_file_location("workspace_doctor", SCRIPT)
workspace_doctor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = workspace_doctor
spec.loader.exec_module(workspace_doctor)


class WorkspaceDoctorTest(unittest.TestCase):
    def test_parse_gitmodules(self) -> None:
        submodules = workspace_doctor.parse_gitmodules(ROOT)
        self.assertEqual(
            {
                "cross-sectional-trees": "cross-sectional-trees",
                "market-data-platform": "market-data-platform",
                "rqdata-hk-depth-snapshots": "rqdata-hk-depth-snapshots",
                "quant-execution-engine": "quant-execution-engine",
            },
            submodules,
        )

    def test_current_checkout_has_no_doctor_errors(self) -> None:
        checks = workspace_doctor.run_checks(ROOT)
        errors = [check for check in checks if check.severity == "ERROR"]
        self.assertEqual([], errors)

    def test_missing_submodule_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitmodules").write_text(
                textwrap.dedent(
                    """
                    [submodule "market-data-platform"]
                    \tpath = market-data-platform
                    \turl = https://example.invalid/market-data-platform.git
                    """
                ).strip(),
                encoding="utf-8",
            )
            (root / "README.md").write_text("market-data-platform\n", encoding="utf-8")
            checks = workspace_doctor.run_checks(root)
        errors = [check.message for check in checks if check.severity == "ERROR"]
        self.assertTrue(any("Missing expected submodule paths" in message for message in errors))
        self.assertTrue(any("market-data-platform is missing" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
