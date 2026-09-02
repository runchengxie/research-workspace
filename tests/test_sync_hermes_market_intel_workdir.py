from __future__ import annotations

import subprocess
from pathlib import Path


def test_syncs_report_jobs_to_current_production_release(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    calls = tmp_path / "calls"
    hermes.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = cron ] && [ "$2" = list ]; then\n'
        "  cat <<'EOF'\n"
        "  morning123456 [active]\n"
        "    Script: morning_pipeline.sh\n"
        "    Workdir: /old/release\n"
        "  evening123456 [active]\n"
        "    Script: evening_pipeline.sh\n"
        "    Workdir: /old/release\n"
        "  weekly123456 [active]\n"
        "    Script: weekly_recap.sh\n"
        "    Workdir: /old/release\n"
        "  unrelated1234 [active]\n"
        "    Script: other.sh\n"
        "    Workdir: /old/release\n"
        "EOF\n"
        'elif [ "$1" = cron ] && [ "$2" = edit ]; then\n'
        '  printf \'%s\n\' "$*" >> "$CALLS"\n'
        "fi\n",
        encoding="utf-8",
    )
    hermes.chmod(0o755)
    current = tmp_path / "production" / "market-intel" / "current"
    current.mkdir(parents=True)

    result = subprocess.run(
        ["bash", "scripts/sync_hermes_market_intel_workdir.sh"],
        env={
            "HERMES_BIN": str(hermes),
            "MARKET_INTEL_CURRENT": str(current),
            "CALLS": str(calls),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == [
        f"cron edit morning123456 --workdir {current}",
        f"cron edit evening123456 --workdir {current}",
        f"cron edit weekly123456 --workdir {current}",
    ]
