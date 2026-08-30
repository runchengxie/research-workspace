from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "count_loc.sh"


def test_count_loc_discovers_all_initialized_submodules(tmp_path: Path) -> None:
    fake_cloc = tmp_path / "cloc"
    log = tmp_path / "cloc.log"
    fake_cloc.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s\\n\' "$*" >> "$CLOC_TEST_LOG"\n'
        'for arg in "$@"; do\n'
        '  case "$arg" in --report-file=*) report="${arg#--report-file=}";; esac\n'
        "done\n"
        'if [[ -n "${report:-}" ]]; then printf \'fake report\\n\' > "$report"; fi\n',
        encoding="utf-8",
    )
    fake_cloc.chmod(0o755)

    result = subprocess.run(
        [str(SCRIPT), "--skip-init"],
        cwd=ROOT,
        env={**os.environ, "CLOC_BIN": str(fake_cloc), "CLOC_TEST_LOG": str(log)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 10  # 1 main repository + 8 submodules + 1 sum operation
    assert all("--list-file=" in call for call in calls[:-1])
    assert "--sum-reports" in calls[-1]
    assert "strategy-research" in result.stdout
