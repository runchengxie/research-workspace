from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "hotsector-ownership-contracts.yml"
OWNERS = {"alpha-research", "portfolio-backtester", "strategy-app", "strategy-pipeline"}


def _manifest() -> dict[str, object]:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_hotsector_ownership_manifest_has_explicit_owner_roles() -> None:
    payload = _manifest()

    assert payload["schema_version"] == "hotsector_ownership_contracts.v1"
    assert set(payload["owner_roles"]) == OWNERS
    assert payload["status"] == "active"


def test_every_hotsector_module_has_an_explicit_state_and_valid_owners() -> None:
    modules = _manifest()["modules"]
    assert isinstance(modules, dict)
    assert modules

    for module, raw_contract in modules.items():
        assert isinstance(module, str) and module
        assert isinstance(raw_contract, dict)
        assert isinstance(raw_contract.get("state"), str) and raw_contract["state"]
        kernel_owner = raw_contract.get("kernel_owner")
        if kernel_owner is not None:
            assert kernel_owner in OWNERS
        split = raw_contract.get("split")
        if split is not None:
            assert isinstance(split, dict) and split
            assert set(split).issubset(OWNERS)


def test_strong_cluster_contract_keeps_lineage_core_in_app() -> None:
    modules = _manifest()["modules"]
    three_arm = modules["hotsector_three_arm_shadow_core"]
    session = modules["hotsector_session_challenger"]

    assert three_arm["kernel_owner"] == "strategy-app"
    assert three_arm["state"] == "retain_in_app"
    assert "strategy-app" in session["split"]
    assert session["state"] == "retain_app_until_reusable_kernel_exists"


def test_migration_rules_require_owner_tests_and_no_app_backedge() -> None:
    rules = _manifest()["migration_rules"]
    ids = {rule["id"] for rule in rules}

    assert "no-app-backedge" in ids
    assert "owner-tests-first" in ids
    assert "contract-before-code" in ids
    assert "gitlink-last" in ids
