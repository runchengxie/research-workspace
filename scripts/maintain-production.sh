#!/usr/bin/env bash
set -euo pipefail

PRODUCTION_ROOT="${PRODUCTION_ROOT:-/home/richard/code/production}"
KEEP_RELEASES="${PRODUCTION_KEEP_RELEASES:-5}"
MIN_FREE_GB="${PRODUCTION_MIN_FREE_GB:-5}"
SHARED_VENV_ROOT="${PRODUCTION_SHARED_VENV_ROOT:-}"
REPO_FILTER=all
DRY_RUN=0
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

usage() {
  printf 'usage: %s [--production-root PATH] [--repo all|research-workspace|market-intel] [--keep N] [--min-free-gb N] [--dry-run]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --production-root) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; PRODUCTION_ROOT=$1 ;;
    --repo) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; REPO_FILTER=$1 ;;
    --keep) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; KEEP_RELEASES=$1 ;;
    --min-free-gb) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; MIN_FREE_GB=$1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) usage; exit 2 ;;
  esac
  shift
done

[[ "$REPO_FILTER" =~ ^(all|research-workspace|market-intel)$ ]] || { usage; exit 2; }
[[ "$KEEP_RELEASES" =~ ^[0-9]+$ && "$KEEP_RELEASES" -ge 2 ]] || {
  printf 'keep must be an integer of at least 2\n' >&2
  exit 2
}
[[ "$MIN_FREE_GB" =~ ^[0-9]+$ ]] || { printf 'min-free-gb must be a non-negative integer\n' >&2; exit 2; }
[[ -d "$PRODUCTION_ROOT" ]] || { printf 'production root does not exist: %s\n' "$PRODUCTION_ROOT" >&2; exit 1; }
[[ -n "$SHARED_VENV_ROOT" ]] || SHARED_VENV_ROOT="$PRODUCTION_ROOT/shared/venvs"

free_kb=$(df -Pk "$PRODUCTION_ROOT" | awk 'NR == 2 { print $4 }')
threshold_kb=$((MIN_FREE_GB * 1024 * 1024))
if (( free_kb < threshold_kb )); then
  printf 'free space %s KiB is below threshold %s KiB\n' "$free_kb" "$threshold_kb" >&2
  exit 2
fi
printf '[maintenance] free space: %s KiB (threshold: %s KiB)\n' "$free_kb" "$threshold_kb"

exec 9>"$PRODUCTION_ROOT/.promotion.lock"
flock -n 9 || { printf 'maintenance blocked: another promotion or maintenance is running\n' >&2; exit 1; }

prune_repo() {
  local name=$1 base=$2 source=$3
  [[ -d "$base" ]] || return 0
  local args=(--base "$base" --source "$source" --shared-root "$SHARED_VENV_ROOT" --keep "$KEEP_RELEASES")
  if (( DRY_RUN )); then
    args+=(--dry-run)
  fi
  bash "$SCRIPT_DIR/prune-production-releases.sh" "${args[@]}"
}

if [[ "$REPO_FILTER" == all || "$REPO_FILTER" == research-workspace ]]; then
  prune_repo research-workspace \
    "$PRODUCTION_ROOT/research-workspace" \
    "${RESEARCH_WORKSPACE_SOURCE:-/home/richard/code/research-workspace}"
fi
if [[ "$REPO_FILTER" == all || "$REPO_FILTER" == market-intel ]]; then
  prune_repo market-intel \
    "$PRODUCTION_ROOT/market-intel" \
    "${MARKET_INTEL_SOURCE:-/home/richard/code/market-intel}"
fi
