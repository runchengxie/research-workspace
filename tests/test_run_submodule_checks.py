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
            ["full", "lint", "mypy_advisory", "smoke", "test", "type"],
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
                ("uv", "run", "--group", "dev", "pytest"),
                ("uv", "run", "--group", "dev", "pyright"),
            ],
            [item.command for item in planned],
        )
        advisory = run_submodule_checks.plan_commands(
            ROOT,
            configs,
            profile="mypy_advisory",
            submodules=["quant-execution-engine"],
        )
        self.assertEqual(
            [("uv", "run", "--group", "dev", "mypy", "src")],
            [item.command for item in advisory],
        )

    def test_manifest_type_profiles_use_pyright_with_qexec_mypy_advisory_separate(self) -> None:
        configs = run_submodule_checks.load_manifest(MANIFEST)

        type_commands = {}
        for name in sorted(configs):
            planned = run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="type",
                submodules=[name],
            )
            type_commands[name] = [item.command for item in planned]

        self.assertEqual(
            {
                "cross-sectional-trees": [("uv", "run", "--extra", "dev", "pyright")],
                "market-data-platform": [("uv", "run", "--extra", "dev", "pyright")],
                "quant-execution-engine": [("uv", "run", "--group", "dev", "pyright")],
            },
            type_commands,
        )

        qexec_full = [
            item.command
            for item in run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="full",
                submodules=["quant-execution-engine"],
            )
        ]
        self.assertIn(("uv", "run", "--group", "dev", "pyright"), qexec_full)
        self.assertNotIn(("uv", "run", "--group", "dev", "mypy", "src"), qexec_full)

        qexec_advisory = [
            item.command
            for item in run_submodule_checks.plan_commands(
                ROOT,
                configs,
                profile="mypy_advisory",
                submodules=["quant-execution-engine"],
            )
        ]
        self.assertEqual([("uv", "run", "--group", "dev", "mypy", "src")], qexec_advisory)

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
