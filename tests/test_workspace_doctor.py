from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workspace_doctor.py"
GOVERNANCE_SCRIPT = ROOT / "scripts" / "workspace_governance.py"
sys.path.insert(0, str(SCRIPT.parent))

spec = importlib.util.spec_from_file_location("workspace_doctor", SCRIPT)
workspace_doctor = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = workspace_doctor
spec.loader.exec_module(workspace_doctor)

governance_spec = importlib.util.spec_from_file_location("workspace_governance", GOVERNANCE_SCRIPT)
workspace_governance = importlib.util.module_from_spec(governance_spec)
assert governance_spec.loader is not None
sys.modules[governance_spec.name] = workspace_governance
governance_spec.loader.exec_module(workspace_governance)


class WorkspaceDoctorTest(unittest.TestCase):
    def test_parse_gitmodules(self) -> None:
        submodules = workspace_doctor.parse_gitmodules(ROOT)
        self.assertEqual(
            {
                "cross-sectional-trees": "cross-sectional-trees",
                "market-data-platform": "market-data-platform",
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

    def test_top_level_script_importing_submodule_package_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "bad.py").write_text(
                "from cstree.internal.foo import Bar\n",
                encoding="utf-8",
            )
            checks = workspace_doctor.check_script_import_boundaries(root)
        self.assertEqual("ERROR", checks[0].severity)
        self.assertIn("scripts/bad.py imports cstree.internal.foo", checks[0].message)

    def test_data_platform_contract_check_uses_a_share_current_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp)
            current_root = artifact_root / "metadata" / "current_assets"
            current_root.mkdir(parents=True)
            (current_root / "hk_current.json").write_text("{}", encoding="utf-8")
            (current_root / "a_share_current.json").write_text("{}", encoding="utf-8")
            (artifact_root / "metadata" / "dataset_registry.csv").write_text(
                "dataset_name,market\n",
                encoding="utf-8",
            )

            with mock.patch.dict(
                workspace_doctor.os.environ,
                {"DATA_PLATFORM_ROOT": str(artifact_root)},
                clear=False,
            ):
                checks = workspace_doctor.check_data_platform_root()

        messages = [check.message for check in checks]
        self.assertTrue(any("a_share_current.json" in message for message in messages))
        self.assertFalse(any("cn_current.json" in message for message in messages))

    def test_data_platform_contract_check_suggests_existing_candidate_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp)
            with (
                mock.patch.dict(workspace_doctor.os.environ, {}, clear=True),
                mock.patch.object(
                    workspace_doctor,
                    "DATA_PLATFORM_ROOT_CANDIDATES",
                    (artifact_root,),
                ),
            ):
                checks = workspace_doctor.check_data_platform_root()

        self.assertEqual("WARN", checks[0].severity)
        self.assertIn(f"export DATA_PLATFORM_ROOT={artifact_root}", checks[0].message)

    def test_data_platform_contract_check_reads_top_level_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_root = root / "data-root"
            current_root = artifact_root / "metadata" / "current_assets"
            current_root.mkdir(parents=True)
            (current_root / "a_share_current.json").write_text("{}", encoding="utf-8")
            (artifact_root / "metadata" / "dataset_registry.csv").write_text(
                "dataset_name,market\n",
                encoding="utf-8",
            )
            (root / ".env").write_text(
                f"DATA_PLATFORM_ROOT={artifact_root}\n",
                encoding="utf-8",
            )

            with mock.patch.dict(workspace_doctor.os.environ, {}, clear=True):
                checks = workspace_doctor.check_data_platform_root(root)

        self.assertEqual("OK", checks[0].severity)
        self.assertIn("(.env)", checks[0].message)

    def test_data_platform_contract_check_warns_on_legacy_cn_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp)
            current_root = artifact_root / "metadata" / "current_assets"
            current_root.mkdir(parents=True)
            (current_root / "hk_current.json").write_text("{}", encoding="utf-8")
            (current_root / "a_share_current.json").write_text("{}", encoding="utf-8")
            (current_root / "cn_current.json").write_text("{}", encoding="utf-8")

            with mock.patch.dict(
                workspace_doctor.os.environ,
                {"DATA_PLATFORM_ROOT": str(artifact_root)},
                clear=False,
            ):
                checks = workspace_doctor.check_data_platform_root()

        warnings = [check for check in checks if check.severity == "WARN"]
        self.assertTrue(any(check.code == "current-contract-alias" for check in warnings))

    def test_data_platform_contract_check_reports_dataset_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp)
            current_root = artifact_root / "metadata" / "current_assets"
            current_root.mkdir(parents=True)
            (current_root / "hk_current.json").write_text("{}", encoding="utf-8")
            (current_root / "a_share_current.json").write_text("{}", encoding="utf-8")

            with mock.patch.dict(
                workspace_doctor.os.environ,
                {"DATA_PLATFORM_ROOT": str(artifact_root)},
                clear=False,
            ):
                missing_checks = workspace_doctor.check_data_platform_root()

            (artifact_root / "metadata" / "dataset_registry.csv").write_text(
                "dataset_name,market\n",
                encoding="utf-8",
            )
            with mock.patch.dict(
                workspace_doctor.os.environ,
                {"DATA_PLATFORM_ROOT": str(artifact_root)},
                clear=False,
            ):
                found_checks = workspace_doctor.check_data_platform_root()

        self.assertTrue(
            any(
                check.code == "dataset-registry" and check.severity == "WARN"
                for check in missing_checks
            )
        )
        self.assertTrue(
            any(
                check.code == "dataset-registry" and check.severity == "OK"
                for check in found_checks
            )
        )

    def test_data_platform_contract_check_accepts_frozen_hk_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "active"
            cold_snapshot = Path(tmp) / "cold" / "hk-freeze-20260526"
            cold_snapshot.mkdir(parents=True)
            current_root = artifact_root / "metadata" / "current_assets"
            current_root.mkdir(parents=True)
            (current_root / "a_share_current.json").write_text("{}", encoding="utf-8")
            marker = artifact_root / "metadata" / "frozen_markets" / "hk.json"
            marker.parent.mkdir(parents=True)
            marker.write_text(
                json.dumps({"cold_snapshot": str(cold_snapshot)}),
                encoding="utf-8",
            )

            with mock.patch.dict(
                workspace_doctor.os.environ,
                {"DATA_PLATFORM_ROOT": str(artifact_root)},
                clear=False,
            ):
                checks = workspace_doctor.check_data_platform_root()

        self.assertTrue(
            any(check.code == "frozen-market" and check.severity == "OK" for check in checks)
        )
        self.assertFalse(
            any(
                check.code == "current-contract"
                and check.severity == "WARN"
                and "hk_current.json" in check.message
                for check in checks
            )
        )

    def test_data_platform_contract_check_accepts_remote_restore_only_hk_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_root = Path(tmp) / "active"
            current_root = artifact_root / "metadata" / "current_assets"
            current_root.mkdir(parents=True)
            (current_root / "a_share_current.json").write_text("{}", encoding="utf-8")
            marker = artifact_root / "metadata" / "frozen_markets" / "hk.json"
            marker.parent.mkdir(parents=True)
            marker.write_text(
                json.dumps(
                    {
                        "cold_snapshot": str(Path(tmp) / "missing-cold-snapshot"),
                        "local_snapshot_available": False,
                        "release_url": "https://example.invalid/releases/hk-freeze",
                        "status": "frozen",
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(
                workspace_doctor.os.environ,
                {"DATA_PLATFORM_ROOT": str(artifact_root)},
                clear=False,
            ):
                checks = workspace_doctor.check_data_platform_root()

        self.assertTrue(
            any(check.code == "frozen-market" and check.severity == "OK" for check in checks)
        )
        self.assertFalse(
            any(check.code == "frozen-market" and check.severity == "WARN" for check in checks)
        )

    def test_top_level_env_allows_only_workspace_path_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "DATA_PLATFORM_ROOT=/tmp/market-data-platform\n",
                encoding="utf-8",
            )

            checks = workspace_doctor.check_top_level_outputs(root)

        self.assertFalse(any(check.severity == "ERROR" for check in checks))

    def test_top_level_env_rejects_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "DATA_PLATFORM_ROOT=/tmp/market-data-platform\nTUSHARE_TOKEN=secret\n",
                encoding="utf-8",
            )

            checks = workspace_doctor.check_top_level_outputs(root)

        self.assertEqual("ERROR", checks[0].severity)
        self.assertIn("TUSHARE_TOKEN is not allowlisted", checks[0].message)

    def test_private_archive_governance_stays_outside_active_graph(self) -> None:
        checks = workspace_doctor.check_hk_private_archive_governance(ROOT)

        self.assertEqual(["OK"], [check.severity for check in checks])
        self.assertIn("outside the submodule graph", checks[0].message)

    def test_submodule_governance_gates_are_visible_to_doctor(self) -> None:
        checks = workspace_governance.check_submodule_governance_gates(ROOT)

        self.assertEqual(["OK"], [check.severity for check in checks])
        self.assertIn("repo-local governance gates", checks[0].message)

    def test_submodule_governance_gates_require_lint_and_full_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "submodule_checks.json").write_text(
                json.dumps(
                    {
                        "submodules": {
                            "market-data-platform": {
                                "profiles": {
                                    "lint": [],
                                    "full": ["@smoke", "@test", "@type"],
                                }
                            },
                            "cross-sectional-trees": {
                                "profiles": {
                                    "lint": [["scripts/dev/run_tests.sh", "maintainability"]],
                                    "full": ["@smoke", "@lint", "@test", "@type"],
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            checks = workspace_governance.check_submodule_governance_gates(root)

        self.assertEqual(["ERROR"], [check.severity for check in checks])
        self.assertIn("market-data-platform:lint", checks[0].message)
        self.assertIn("market-data-platform:full does not include @lint", checks[0].message)

    def test_maintainability_governance_is_visible_to_doctor(self) -> None:
        checks = workspace_doctor.check_maintainability_governance(ROOT)

        errors = [check.message for check in checks if check.severity == "ERROR"]
        codes = {check.code for check in checks}

        self.assertEqual([], errors)
        self.assertIn("governance-docs", codes)
        self.assertIn("governance-deprecations", codes)
        self.assertIn("governance-script-lifecycle", codes)
        self.assertIn("governance-quality", codes)
        self.assertIn("governance-refactor-roadmap", codes)
        self.assertIn("governance-hk-public-split", codes)
        self.assertTrue(
            any(
                check.severity == "OK"
                and check.code == "governance-deprecations"
                and "pending_follow_up=0/0" in check.message
                for check in checks
            )
        )

    def test_maintainability_governance_reports_missing_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            checks = workspace_doctor.check_maintainability_governance(Path(tmp))

        errors = [check for check in checks if check.severity == "ERROR"]
        self.assertTrue(errors)
        self.assertTrue(any("Missing docs/deprecations.yml" in check.message for check in errors))


if __name__ == "__main__":
    unittest.main()
