from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_submodule_checks.py"
MANIFEST = ROOT / "scripts" / "submodule_checks.json"

spec = importlib.util.spec_from_file_location("run_submodule_checks", SCRIPT)
run_submodule_checks = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = run_submodule_checks
spec.loader.exec_module(run_submodule_checks)


class RunSubmoduleChecksTest(unittest.TestCase):
    def test_default_manifest_profiles_expand(self) -> None:
        configs = run_submodule_checks.load_manifest(MANIFEST)
        self.assertEqual(
            ["full", "lint", "release_typecheck", "smoke", "test", "type"],
            run_submodule_checks.available_profiles(configs),
        )

        planned = run_submodule_checks.plan_commands(
            ROOT,
            configs,
            profile="full",
            submodules=["quant-execution-engine"],
        )
        self.assertEqual(
            [
                ("uv", "run", "--group", "dev", "--extra", "cli", "qexec", "--help"),
                ("uv", "run", "--group", "dev", "ruff", "check", "."),
                ("uv", "run", "--group", "dev", "ruff", "format", "--check", "."),
                ("uv", "run", "--group", "dev", "ty", "check"),
                ("uv", "run", "--group", "dev", "python", "-m", "pytest"),
            ],
            [item.command for item in planned],
        )

    def test_lint_profiles_include_repo_local_governance_gates(self) -> None:
        configs = run_submodule_checks.load_manifest(MANIFEST)

        market_lint = [
            item.command
            for item in run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="lint",
                submodules=["market-data-platform"],
            )
        ]
        strategy_lint = [
            item.command
            for item in run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="lint",
                submodules=["strategy-pipeline"],
            )
        ]

        self.assertIn(
            (
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "scripts/dev/architecture_governance.py",
                "--check",
            ),
            market_lint,
        )
        self.assertIn(("scripts/dev/run_tests.sh", "maintainability"), strategy_lint)

    def test_split_package_profiles_use_repo_local_tools(self) -> None:
        configs = run_submodule_checks.load_manifest(MANIFEST)

        for submodule in ("alpha-research", "portfolio-backtester"):
            tests = run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="test",
                submodules=[submodule],
            )
            self.assertEqual(
                [("uv", "run", "--extra", "dev", "python", "-m", "pytest")],
                [item.command for item in tests],
            )

            smoke = run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="smoke",
                submodules=[submodule],
            )
            command_text = " ".join(smoke[0].command)
            self.assertNotIn("../strategy-pipeline/src", command_text)
            self.assertNotIn("../alpha-research/src", command_text)
            self.assertNotIn("../portfolio-backtester/src", command_text)

    def test_type_profiles_match_current_tooling(self) -> None:
        configs = run_submodule_checks.load_manifest(MANIFEST)

        expected_type = {
            "alpha-research": [("uv", "run", "--extra", "dev", "ty", "check")],
            "market-data-platform": [("uv", "run", "--extra", "dev", "ty", "check")],
            "portfolio-backtester": [("uv", "run", "--extra", "dev", "ty", "check")],
            "quant-execution-engine": [("uv", "run", "--group", "dev", "ty", "check")],
            "strategy-pipeline": [("uv", "run", "--extra", "dev", "ty", "check")],
        }
        expected_release = {
            "alpha-research": [("uv", "run", "--extra", "dev", "basedpyright")],
            "market-data-platform": [("uv", "run", "--extra", "dev", "basedpyright")],
            "portfolio-backtester": [("uv", "run", "--extra", "dev", "basedpyright")],
            "quant-execution-engine": [
                ("uv", "run", "--group", "dev", "python", "-m", "basedpyright")
            ],
            "strategy-pipeline": [("uv", "run", "--extra", "dev", "python", "-m", "basedpyright")],
        }

        for name in sorted(configs):
            type_commands = run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="type",
                submodules=[name],
            )
            release_commands = run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="release_typecheck",
                submodules=[name],
            )
            self.assertEqual(expected_type[name], [item.command for item in type_commands])
            self.assertEqual(expected_release[name], [item.command for item in release_commands])

        manifest_text = MANIFEST.read_text(encoding="utf-8").lower()
        self.assertNotIn("mypy", manifest_text)

    def test_dry_run_does_not_execute_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "example").mkdir()
            planned = [
                run_submodule_checks.PlannedCommand(
                    submodule="example",
                    cwd=root / "example",
                    command=("python", "-c", "raise SystemExit(99)"),
                )
            ]
            results = run_submodule_checks.run_planned_commands(
                planned,
                timeout=1,
                dry_run=True,
                fail_fast=False,
            )

        self.assertEqual("DRY-RUN", results[0].severity)

    def test_manifest_rejects_paths_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "checks.json"
            manifest.write_text(
                json.dumps(
                    {
                        "submodules": {
                            "bad": {
                                "path": "../bad",
                                "profiles": {"smoke": [["true"]]},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(run_submodule_checks.ManifestError):
                run_submodule_checks.load_manifest(manifest)

    def test_profile_cycles_are_rejected(self) -> None:
        config = run_submodule_checks.SubmoduleConfig(
            name="example",
            path=Path("example"),
            profiles={"a": ["@b"], "b": ["@a"]},
        )
        with self.assertRaises(run_submodule_checks.ManifestError):
            run_submodule_checks._expand_profile(config, "a")


if __name__ == "__main__":
    unittest.main()
