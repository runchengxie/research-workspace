#!/usr/bin/env bash
# 一键本地门禁：不依赖 core.hooksPath 钩子，任何克隆者直接运行即可。
# standard 运行顶层核心检查，full 额外执行全部子模块登记的完整门禁。
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root" || exit 1

profile="${1:-standard}"
case "$profile" in
  standard)
    echo "==> 硬质量门禁 (run_quality_checks --profile hard)"
    python scripts/run_quality_checks.py --profile hard

    echo "==> 工作区状态 (workspace_doctor)"
    python scripts/workspace_doctor.py

    echo "==> 契约冒烟 (smoke_contracts)"
    python src/research_contracts/smoke_contracts.py

    echo "==> 顶层测试"
    uv run --project strategy-pipeline --extra dev \
      --with 'matplotlib>=3.8' --with 'tabulate>=0.9' \
      python -m pytest tests -q
    ;;
  full)
    echo "==> 子模块委托 full"
    python scripts/run_submodule_checks.py --profile full

    echo "==> 顶层标准检查"
    bash "$0" standard
    ;;
  *)
    echo "用法: bash scripts/check.sh [standard|full]" >&2
    echo "  standard  硬质量门禁 + doctor + 契约 smoke + 顶层测试（默认）" >&2
    echo "  full      在 standard 基础上执行全部子模块完整门禁" >&2
    exit 2
    ;;
esac
