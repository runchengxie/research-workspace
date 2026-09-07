"""Fail-closed orchestration for one cashflow shadow signal."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class CashflowShadowConfig:
    evidence_bundle: Path
    readiness: Path
    trade_calendar: Path
    features: Path
    pit_audit: Path
    output_root: Path
    publication_root: Path
    rollout_ledger: Path
    delivery_receipt: Path
    chat_ids: tuple[str, ...]
    as_of_date: str
    send: bool = False
    features_receipt: Path | None = None
    send_confirmation: str | None = None
    status_chat_ids: tuple[str, ...] = ()
    status_receipt: Path | None = None
    allow_reconstructed_pit: bool = False


def _json_stdout(process: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    for line in reversed((process.stdout or "").splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def _environment(*, extra_paths: tuple[Path, ...] = ()) -> dict[str, str]:
    current = os.environ.copy()
    paths = [Path(__file__).resolve().parents[1] / "src", *extra_paths]
    current["PYTHONPATH"] = os.pathsep.join(str(path) for path in paths)
    return current


def _run_stage(
    command: list[str],
    *,
    runner: CommandRunner,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return runner(command, cwd=str(cwd), env=env, capture_output=True, text=True, check=False)


def _project_python(project: Path) -> list[str]:
    """Run each repository in its own locked dependency environment."""
    return ["uv", "run", "--project", str(project), "python"]


def _root_path(root: Path, value: Path) -> Path:
    """Resolve operator paths before changing stage working directories."""
    return value if value.is_absolute() else (root / value).resolve()


def _write_status_input(output_root: Path, *, stage: str, payload: dict[str, Any]) -> Path:
    status_dir = output_root / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    date_key = payload.get("signal_date") or payload.get("source_date") or "unknown"
    path = status_dir / f"{date_key}-{stage}.json"
    status = {
        "schema_version": "cashflow_status_input.v1",
        "strategy_id": "cashflow_quality_top50_v1",
        "policy_id": "cashflow_quality_top50_v1.quarterly_fcf_cap10.v1",
        "status": "blocked",
        "stage": stage,
        "source_date": str(payload.get("source_date") or "unknown"),
        "signal_date": str(payload.get("signal_date") or "unknown"),
        "reason": str(payload.get("reason") or payload.get("decision") or "cashflow stage blocked"),
        "detail": str(payload.get("detail") or ""),
        "no_target_artifact": True,
    }
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    return path


def _notify_status(
    *,
    config: CashflowShadowConfig,
    output_root: Path,
    stage: str,
    payload: dict[str, Any],
    market_intel: Path,
    root: Path,
    run_command: CommandRunner,
) -> dict[str, Any] | None:
    if not config.status_chat_ids:
        return None
    status_input = _write_status_input(output_root, stage=stage, payload=payload)
    receipt = _root_path(
        root,
        config.status_receipt or (output_root / "status" / "cashflow-status-receipt.json"),
    )
    command = [
        *_project_python(market_intel),
        "-m",
        "a_share_daily.cli",
        "cashflow-status-notify",
        "--status-json",
        str(status_input),
        "--receipt",
        str(receipt),
    ]
    for chat_id in config.status_chat_ids:
        command.extend(("--chat-id", chat_id))
    if config.send:
        command.extend(("--send", "--send-confirmation", str(config.send_confirmation)))
    else:
        # The status channel is intentionally dry-run by default.
        pass
    process = _run_stage(
        command,
        runner=run_command,
        cwd=market_intel,
        env=_environment(extra_paths=(market_intel / "src",)),
    )
    return _json_stdout(process)


def orchestrate_cashflow_shadow(
    config: CashflowShadowConfig,
    *,
    run_command: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    """Run readiness, scheduler, publication and delivery in fail-closed order."""
    if config.send and config.send_confirmation != "I_UNDERSTAND_TEST_GROUP_ONLY":
        return {
            "status": "blocked",
            "stage": "delivery",
            "reason": "send requires explicit test-group confirmation",
        }
    root = Path(__file__).resolve().parents[1]
    strategy_app = root / "strategy-app"
    strategy_pipeline = root / "strategy-pipeline"
    market_intel = root.parent / "market-intel"
    evidence_bundle = _root_path(root, config.evidence_bundle)
    readiness = _root_path(root, config.readiness)
    trade_calendar = _root_path(root, config.trade_calendar)
    features = _root_path(root, config.features)
    pit_audit = _root_path(root, config.pit_audit)
    output_root = _root_path(root, config.output_root)
    publication_root = _root_path(root, config.publication_root)
    rollout_ledger = _root_path(root, config.rollout_ledger)
    delivery_receipt = _root_path(root, config.delivery_receipt)
    features_receipt = (
        _root_path(root, config.features_receipt) if config.features_receipt else None
    )
    scheduler_command = [
        *_project_python(strategy_app),
        "-m",
        "strategy_app.cashflow.scheduler",
        "--trade-calendar",
        str(trade_calendar),
        "--features",
        str(features),
        "--readiness",
        str(readiness),
        "--pit-audit",
        str(pit_audit),
        "--rollout-ledger",
        str(rollout_ledger),
        "--output-root",
        str(output_root),
        "--as-of-date",
        config.as_of_date,
        "--features-receipt",
        str(features_receipt or features.with_name(f"{features.name}.receipt.json")),
    ]
    if config.allow_reconstructed_pit:
        scheduler_command.append("--allow-reconstructed-pit")
    scheduler_env = _environment(extra_paths=(strategy_app / "src",))

    readiness_process = _run_stage(
        [
            *_project_python(strategy_app),
            "-m",
            "research_contracts.cashflow_readiness",
            "--evidence-bundle",
            str(evidence_bundle),
            "--root",
            str(root),
            "--pit-audit",
            str(pit_audit),
            "--output",
            str(readiness),
        ],
        runner=run_command,
        cwd=root,
        env=_environment(),
    )
    readiness_output = _json_stdout(readiness_process)
    if (
        (readiness_process.returncode != 0 or not readiness_output.get("eligible_for_gray_push"))
        and not config.allow_reconstructed_pit
    ):
        observation_process = _run_stage(
            scheduler_command,
            runner=run_command,
            cwd=strategy_app,
            env=scheduler_env,
        )
        result = {
            "status": "blocked",
            "stage": "readiness",
            "reason": readiness_output.get("decision") or "cashflow readiness blocked",
            "readiness": readiness_output,
            "observation": _json_stdout(observation_process),
        }
        result["status_notification"] = _notify_status(
            config=config,
            output_root=output_root,
            stage="readiness",
            payload={**readiness_output, "reason": readiness_output.get("decision")},
            market_intel=market_intel,
            root=root,
            run_command=run_command,
        )
        return result
    scheduler_process = _run_stage(
        scheduler_command,
        runner=run_command,
        cwd=strategy_app,
        env=scheduler_env,
    )
    scheduler_output = _json_stdout(scheduler_process)
    if scheduler_process.returncode != 0 or scheduler_output.get("status") != "passed":
        result = {
            "status": "blocked",
            "stage": "scheduler",
            "reason": scheduler_output.get("reason") or "cashflow scheduler blocked",
            "readiness": readiness_output,
            "scheduler": scheduler_output,
        }
        result["status_notification"] = _notify_status(
            config=config,
            output_root=output_root,
            stage="scheduler",
            payload=scheduler_output,
            market_intel=market_intel,
            root=root,
            run_command=run_command,
        )
        return result

    selection_path = scheduler_output.get("selection_path")
    if not isinstance(selection_path, str) or not selection_path:
        result = {"status": "blocked", "stage": "publication", "reason": "selection path missing"}
        result["status_notification"] = _notify_status(
            config=config,
            output_root=output_root,
            stage="publication",
            payload=result,
            market_intel=market_intel,
            root=root,
            run_command=run_command,
        )
        return result
    publication_process = _run_stage(
        [
            *_project_python(strategy_pipeline),
            "-m",
            "strategy_pipeline.cli",
            "cashflow-publish-shadow",
            "--selection",
            selection_path,
            "--readiness",
            str(readiness),
            "--output-root",
            str(publication_root),
            *( ["--allow-reconstructed-pit"] if config.allow_reconstructed_pit else [] ),
        ],
        runner=run_command,
        cwd=strategy_pipeline,
        env=_environment(extra_paths=(strategy_pipeline / "src",)),
    )
    publication_output = _json_stdout(publication_process)
    if publication_process.returncode != 0:
        result = {
            "status": "blocked",
            "stage": "publication",
            "reason": publication_output.get("reason") or "cashflow publication failed",
            "publication": publication_output,
        }
        result["status_notification"] = _notify_status(
            config=config,
            output_root=output_root,
            stage="publication",
            payload=publication_output,
            market_intel=market_intel,
            root=root,
            run_command=run_command,
        )
        return result
    if not config.chat_ids:
        result = {"status": "blocked", "stage": "delivery", "reason": "explicit chat ID required"}
        result["status_notification"] = _notify_status(
            config=config,
            output_root=output_root,
            stage="delivery",
            payload=result,
            market_intel=market_intel,
            root=root,
            run_command=run_command,
        )
        return result

    published_selection = publication_output.get("targets") or selection_path
    delivery_command = [
        *_project_python(market_intel),
        "-m",
        "a_share_daily.cli",
        "cashflow-delivery",
        "--selection",
        str(published_selection),
        "--source-date",
        str(scheduler_output.get("source_date") or ""),
        "--signal-date",
        str(scheduler_output.get("signal_date") or ""),
        "--publication-receipt",
        str(publication_output.get("receipt") or ""),
        "--receipt",
        str(delivery_receipt),
    ]
    for chat_id in config.chat_ids:
        delivery_command.extend(("--chat-id", chat_id))
    if not config.send:
        delivery_command.append("--dry-run")
    delivery_process = _run_stage(
        delivery_command,
        runner=run_command,
        cwd=market_intel,
        env=_environment(extra_paths=(market_intel / "src",)),
    )
    delivery_output = _json_stdout(delivery_process)
    return {
        "status": (
            "sent"
            if config.send and delivery_process.returncode == 0
            else "dry_run"
            if delivery_process.returncode == 0
            else "blocked"
        ),
        "stage": "delivery",
        "readiness": readiness_output,
        "scheduler": scheduler_output,
        "publication": publication_output,
        "delivery": delivery_output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_cashflow_shadow")
    for name in (
        "evidence_bundle",
        "readiness",
        "trade_calendar",
        "features",
        "pit_audit",
        "output_root",
        "publication_root",
        "rollout_ledger",
        "delivery_receipt",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--chat-id", action="append", default=[])
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--features-receipt", type=Path, required=True)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--send-confirmation")
    parser.add_argument("--status-chat-id", action="append", default=[])
    parser.add_argument("--status-receipt", type=Path)
    parser.add_argument(
        "--allow-reconstructed-pit",
        action="store_true",
        help="Research-only portfolio snapshot using reconstructed PIT data",
    )
    args = parser.parse_args(argv)
    result = orchestrate_cashflow_shadow(
        CashflowShadowConfig(
            evidence_bundle=args.evidence_bundle,
            readiness=args.readiness,
            trade_calendar=args.trade_calendar,
            features=args.features,
            pit_audit=args.pit_audit,
            output_root=args.output_root,
            publication_root=args.publication_root,
            rollout_ledger=args.rollout_ledger,
            delivery_receipt=args.delivery_receipt,
            chat_ids=tuple(args.chat_id),
            as_of_date=args.as_of_date,
            send=args.send,
            features_receipt=args.features_receipt,
            send_confirmation=args.send_confirmation,
            status_chat_ids=tuple(args.status_chat_id),
            status_receipt=args.status_receipt,
            allow_reconstructed_pit=args.allow_reconstructed_pit,
        )
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"sent", "dry_run"} else 20


if __name__ == "__main__":
    raise SystemExit(main())
