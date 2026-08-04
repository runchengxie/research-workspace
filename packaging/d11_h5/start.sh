#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_ROOT="$PACKAGE_ROOT/code/research-workspace"
DATA_ROOT="$PACKAGE_ROOT/data/market-data-platform"
ARTIFACT_ROOT="$PACKAGE_ROOT/research-artifacts/strategy-pipeline/trailing_weekly_strategy_20260803"
RUNTIME_ROOT="$PACKAGE_ROOT/.runtime"
VENV_ROOT="$RUNTIME_ROOT/venv"
OUTPUT_ROOT="$PACKAGE_ROOT/outputs/d11_h5_shadow"

usage() {
  printf '%s\n' \
    '用法：./start.sh doctor|verify|setup|demo|run [D11-H5 参数]' \
    '' \
    '  doctor  检查包结构和可选分钟数据' \
    '  verify  校验包内全部静态文件' \
    '  setup   创建 Python 环境和可移植数据合同' \
    '  demo    复现 20260803 收盘至 20260804 开盘目标' \
    '  run     传入 --source-date 和 --signal-date 运行'
}

write_runtime_contract() {
  python3 - "$PACKAGE_ROOT" <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

root = Path(os.sys.argv[1]).resolve()
manifest = json.loads((root / "package_manifest.json").read_text(encoding="utf-8"))
data_root = root / "data" / "market-data-platform"
daily = root / manifest["assets"]["daily_clean"]["path"]
instruments = root / manifest["assets"]["instruments"]["path"]
trade_cal = root / manifest["assets"]["trade_cal"]["path"]

metadata = data_root / "metadata" / "current_assets"
metadata.mkdir(parents=True, exist_ok=True)
contract = {
    "schema_version": "market_data_platform.current_assets.v1",
    "assets": {
        "daily_clean": {"resolved_path": str(daily), "as_of": manifest["data_as_of"]},
        "instruments": {"resolved_path": str(instruments)},
        "trade_cal": {"resolved_path": str(trade_cal), "as_of": "20261231"},
    },
}
(metadata / "a_share_current.json").write_text(
    json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

derived = data_root / "assets" / "derived" / "a_share"
placeholder = derived / "minute_1m_package_placeholder"
placeholder.mkdir(parents=True, exist_ok=True)
legacy_alias = derived / "minute_1m"
if legacy_alias.is_symlink() or not legacy_alias.exists():
    legacy_alias.unlink(missing_ok=True)
    legacy_alias.symlink_to(placeholder.name, target_is_directory=True)

minute_versions = sorted(derived.glob("minute_1m_tushare_v*"))
if minute_versions:
    minute = minute_versions[-1].resolve()
    receipt = {
        "schema_version": "a_share.minute_tushare_operational_version.v1",
        "status": "published_operational_version",
        "provider": "tushare",
        "output_dir": str(minute),
        "legacy_canonical_mutated": False,
        "package_portable_receipt": True,
    }
    (minute / "_operational_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tushare_alias = derived / "minute_1m_tushare"
    if tushare_alias.is_symlink() or not tushare_alias.exists():
        tushare_alias.unlink(missing_ok=True)
        tushare_alias.symlink_to(minute.name, target_is_directory=True)
PY
}

doctor() {
  python3 - "$PACKAGE_ROOT" <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

root = Path(os.sys.argv[1]).resolve()
manifest_path = root / "package_manifest.json"
if not manifest_path.is_file():
    raise SystemExit("缺少 package_manifest.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = [
    root / "code" / "research-workspace" / "strategy-pipeline" / "pyproject.toml",
    root / manifest["assets"]["daily_clean"]["path"],
    root / manifest["assets"]["instruments"]["path"],
    root / manifest["assets"]["trade_cal"]["path"],
    root / "research-artifacts" / "strategy-pipeline" / "trailing_weekly_strategy_20260803",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("包结构不完整：\n" + "\n".join(missing))
minute = list((root / "data" / "market-data-platform" / "assets" / "derived" / "a_share").glob("minute_1m_tushare_v*"))
print(f"完整复现包：通过，数据截至 {manifest['data_as_of']}")
print("TuShare 一分钟快照：" + ("已安装" if minute else "未安装，可选"))
print(f"代码版本：{manifest['git']['research-workspace']['commit'][:12]}")
PY
}

verify() {
  (cd "$PACKAGE_ROOT" && sha256sum --check PACKAGE_FILES.sha256)
}

setup_env() {
  write_runtime_contract
  if [[ -x "$VENV_ROOT/bin/strategy" ]]; then
    return
  fi
  mkdir -p "$RUNTIME_ROOT"
  python3 -m venv "$VENV_ROOT"
  "$VENV_ROOT/bin/python" -m pip install --upgrade pip
  "$VENV_ROOT/bin/python" -m pip install -e "$CODE_ROOT/strategy-pipeline"
  for repo in market-data-platform alpha-research portfolio-backtester research-apps quant-execution-engine; do
    "$VENV_ROOT/bin/python" -m pip install --no-deps -e "$CODE_ROOT/$repo"
  done
}

run_strategy() {
  setup_env
  export DATA_PLATFORM_ROOT="$DATA_ROOT"
  export D11_H5_SHADOW_BOOTSTRAP_ROOT="$ARTIFACT_ROOT"
  export D11_H5_SHADOW_OUTPUT_ROOT="$OUTPUT_ROOT"
  exec "$VENV_ROOT/bin/strategy" d11-h5-shadow "$@"
}

command="${1:-doctor}"
if [[ $# -gt 0 ]]; then
  shift
fi
case "$command" in
  doctor) doctor ;;
  verify) verify ;;
  setup) setup_env; doctor ;;
  demo) run_strategy --source-date 20260803 --signal-date 20260804 "$@" ;;
  run) run_strategy "$@" ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
