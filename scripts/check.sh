#!/usr/bin/env bash
# 一键本地门禁：不依赖 core.hooksPath 钩子，任何克隆者直接运行即可。
# 等价于推送顶层仓库时本地 pre-push 会跑的检查集合（不含 push-ref 校验）。
set -uo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root" || exit 1

profile="${1:-standard}"
case "$profile" in
  standard)
    # 日常等价检查：硬质量门禁 + 工作区状态 + 契约冒烟 + 顶层测试
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
    # 含子模块委托的完整检查（先验证 lockfile，再跑各仓登记门禁）
    echo "==> 子模块委托 smoke"
    python scripts/run_submodule_checks.py --profile smoke

    echo "==> 子模块委托 full (dry-run 预览)"
    python scripts/run_submodule_checks.py --profile full --dry-run

    echo "==> 顶层标准检查"
    bash "$0" standard
    ;;
  *)
    echo "用法: bash scripts/check.sh [standard|full]" >&2
    echo "  standard  硬质量门禁 + doctor + 契约 smoke + 顶层测试（默认）" >&2
    echo "  full      在 standard 基础上加子模块委托检查" >&2
    exit 2
    ;;
esac
