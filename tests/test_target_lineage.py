from pathlib import Path

from research_contracts import (
    LineageInput,
    lineage_inputs,
    lineage_payload,
    targets_envelope_v2,
)


def test_target_lineage_collects_run_inputs(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text('{"backtest": {}}', encoding="utf-8")
    (tmp_path / "config.used.yml").write_text("strategy: {}\n", encoding="utf-8")

    inputs = lineage_inputs(run_dir=tmp_path, holdings_payload={})

    assert [item.artifact_id for item in inputs] == [
        "strategy-pipeline.run:summary.json",
        "strategy-pipeline.run:config.used.yml",
    ]


def test_target_lineage_payload_keeps_selection_and_strategy_metadata(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(
        '{"positions": {"strategy": {"name": "example"}}}', encoding="utf-8"
    )
    payload = lineage_payload(
        holdings_payload={"as_of": "t-1", "entry_date": "2026-01-02"},
        targets_path=tmp_path / "targets.json",
        target_source="positions_file",
        target_gross_exposure=1.0,
        weight_sum=1.0,
        target_count=2,
        markets="CN",
        run_dir=tmp_path,
        fail_on_quality=None,
        target_pruning={},
    )

    assert payload["selection"]["target_count"] == 2
    assert payload["strategy"] == {"name": "example"}


def test_target_envelope_accepts_lineage_inputs(tmp_path: Path) -> None:
    targets = tmp_path / "targets.json"
    targets.write_text('{"targets": []}', encoding="utf-8")

    envelope = targets_envelope_v2(
        run_id="run-1",
        targets_path=targets,
        configuration={},
        lineage=[LineageInput(artifact_id="run", sha256="a" * 64)],
    )

    assert envelope.artifact_type == "targets.json"
