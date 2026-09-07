from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.run_cashflow_shadow import (
    CashflowShadowConfig,
    orchestrate_cashflow_shadow,
)


def _completed(payload: dict[str, object], returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, json.dumps(payload), "")


def _config(tmp_path: Path) -> CashflowShadowConfig:
    return CashflowShadowConfig(
        evidence_bundle=tmp_path / "evidence.json",
        readiness=tmp_path / "readiness.json",
        trade_calendar=tmp_path / "calendar.parquet",
        features=tmp_path / "features.parquet",
        pit_audit=tmp_path / "pit.json",
        output_root=tmp_path / "outputs",
        publication_root=tmp_path / "publications",
        rollout_ledger=tmp_path / "rollout.json",
        delivery_receipt=tmp_path / "delivery.json",
        chat_ids=("oc_test",),
        as_of_date="20260905",
        send=False,
    )


def test_orchestration_stops_before_publication_when_scheduler_blocks(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if any("cashflow.scheduler" in part for part in command):
            return _completed({"status": "blocked", "reason": "pit_audit_failed"}, 20)
        return _completed({"status": "passed", "eligible_for_gray_push": True})

    result = orchestrate_cashflow_shadow(_config(tmp_path), run_command=fake_run)

    assert result["status"] == "blocked"
    assert len(calls) == 2
    assert not any("cashflow-publish-shadow" in call for call in calls)


def test_orchestration_can_notify_blocked_status_to_explicit_status_chat(
    tmp_path: Path,
) -> None:
    config = CashflowShadowConfig(
        **{
            **_config(tmp_path).__dict__,
            "status_chat_ids": ("oc_status_test",),
            "status_receipt": tmp_path / "status-receipt.json",
        }
    )
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if any("cashflow.scheduler" in part for part in command):
            return _completed({"status": "blocked", "reason": "pit_audit_failed"}, 20)
        if "cashflow-status-notify" in command:
            return _completed({"success": True, "status": "dry_run"})
        return _completed({"status": "passed", "eligible_for_gray_push": True})

    result = orchestrate_cashflow_shadow(config, run_command=fake_run)

    assert result["status"] == "blocked"
    assert result["status_notification"] == {"success": True, "status": "dry_run"}
    status_call = next(call for call in calls if "cashflow-status-notify" in call)
    assert status_call[status_call.index("--chat-id") + 1] == "oc_status_test"
    status_input = Path(status_call[status_call.index("--status-json") + 1])
    payload = json.loads(status_input.read_text(encoding="utf-8"))
    assert payload["no_target_artifact"] is True
    assert "targets" not in payload


def test_orchestration_requires_explicit_chat_before_delivery(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config = CashflowShadowConfig(**{**config.__dict__, "chat_ids": ()})
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if any("cashflow.scheduler" in part for part in command):
            return _completed({"status": "passed", "selection_path": "selection.json"})
        return _completed(
            {"status": "passed", "receipt": "receipt.json", "eligible_for_gray_push": True}
        )

    result = orchestrate_cashflow_shadow(config, run_command=fake_run)

    assert result["status"] == "blocked"
    assert "chat" in result["reason"]
    assert not any("cashflow-delivery" in call for call in calls)


def test_orchestration_passes_published_receipt_and_resolved_dates_to_delivery(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if any("cashflow.scheduler" in part for part in command):
            return _completed(
                {
                    "status": "passed",
                    "selection_path": "selection.json",
                    "source_date": "20260904",
                    "signal_date": "20260907",
                }
            )
        if "cashflow-publish-shadow" in command:
            return _completed({"targets": "published-targets.json", "receipt": "publication.json"})
        if "cashflow-delivery" in command:
            return _completed({"success": True})
        return _completed({"status": "passed", "eligible_for_gray_push": True})

    result = orchestrate_cashflow_shadow(config, run_command=fake_run)

    assert result["status"] == "dry_run"
    scheduler = next(
        call for call in calls if any("strategy_app.cashflow.scheduler" in part for part in call)
    )
    workspace = Path(__file__).resolve().parents[1]
    assert scheduler[:5] == [
        "uv",
        "run",
        "--project",
        str(workspace / "strategy-app"),
        "python",
    ]
    delivery = next(call for call in calls if "cashflow-delivery" in call)
    assert delivery[delivery.index("--source-date") + 1] == "20260904"
    assert delivery[delivery.index("--signal-date") + 1] == "20260907"
    assert delivery[delivery.index("--publication-receipt") + 1] == "publication.json"


def test_orchestration_stops_at_readiness_failure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return _completed(
            {
                "decision": "continue_shadow",
                "eligible_for_gray_push": False,
                "failed_gates": ["pit"],
            },
            20,
        )

    result = orchestrate_cashflow_shadow(config, run_command=fake_run)

    assert result["status"] == "blocked"
    assert result["stage"] == "readiness"
    assert len(calls) == 2
    assert calls[0][calls[0].index("--pit-audit") + 1] == str(tmp_path / "pit.json")
    assert any("strategy_app.cashflow.scheduler" in part for part in calls[1])
    assert result["observation"] == {
        "decision": "continue_shadow",
        "eligible_for_gray_push": False,
        "failed_gates": ["pit"],
    }


def test_orchestration_can_continue_with_reconstructed_pit_research_flag(tmp_path: Path) -> None:
    config = CashflowShadowConfig(**{**_config(tmp_path).__dict__, "allow_reconstructed_pit": True})
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if any("cashflow.scheduler" in part for part in command):
            return _completed(
                {
                    "status": "passed",
                    "selection_path": "selection.json",
                    "source_date": "20260904",
                    "signal_date": "20260907",
                }
            )
        if "cashflow-publish-shadow" in command:
            return _completed({"targets": "published.json", "receipt": "publication.json"})
        if "cashflow-delivery" in command:
            return _completed({"success": True})
        return _completed(
            {
                "decision": "continue_shadow",
                "eligible_for_gray_push": False,
                "failed_gates": ["pit"],
            },
            20,
        )

    result = orchestrate_cashflow_shadow(config, run_command=fake_run)

    assert result["status"] == "dry_run"
    scheduler = next(call for call in calls if any("cashflow.scheduler" in part for part in call))
    assert "--allow-reconstructed-pit" in scheduler


def test_orchestration_requires_test_group_confirmation_for_send(tmp_path: Path) -> None:
    config = CashflowShadowConfig(**{**_config(tmp_path).__dict__, "send": True})

    result = orchestrate_cashflow_shadow(config, run_command=lambda *_args, **_kwargs: None)

    assert result == {
        "status": "blocked",
        "stage": "delivery",
        "reason": "send requires explicit test-group confirmation",
    }
