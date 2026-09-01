#!/usr/bin/env bash
set -euo pipefail

PRODUCTION_ROOT="${PRODUCTION_ROOT:-/home/richard/code/production}"
MAX_MIGRATIONS="${PRODUCTION_VENV_MIGRATE_MAX:-2}"
REPO_FILTER=all
DRY_RUN=0
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

usage() {
  printf 'usage: %s [--production-root PATH] [--repo all|research-workspace|market-intel] [--max N] [--dry-run]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --production-root) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; PRODUCTION_ROOT=$1 ;;
    --repo) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; REPO_FILTER=$1 ;;
    --max) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; MAX_MIGRATIONS=$1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) usage; exit 2 ;;
  esac
  shift
done

[[ "$REPO_FILTER" =~ ^(all|research-workspace|market-intel)$ ]] || { usage; exit 2; }
[[ "$MAX_MIGRATIONS" =~ ^[0-9]+$ && "$MAX_MIGRATIONS" -ge 1 ]] || {
  printf 'max must be a positive integer\n' >&2
  exit 2
}

shared_root="$PRODUCTION_ROOT/shared/venvs"
migrated=0

release_order() {
  local base=$1 path release timestamp metadata
  for path in "$base/releases"/*; do
    [[ -d "$path" && ! -L "$path" ]] || continue
    release=$(basename "$path")
    metadata="$base/manifests/$release.txt"
    if [[ -f "$metadata" ]]; then
      timestamp=$(stat -c '%Y' "$metadata")
    else
      timestamp=$(stat -c '%Y' "$path")
    fi
    printf '%s %s\n' "$timestamp" "$release"
  done | sort -rn | awk '{print $2}'
}

migrate_project() {
  local release_path=$1 project_path=$2 name=$3
  local venv="$project_path/.venv"
  [[ -d "$venv" && ! -L "$venv" ]] || return 0
  (( migrated < MAX_MIGRATIONS )) || return 0
  if (( DRY_RUN )); then
    printf '[migrate] would migrate %s/.venv\n' "$project_path"
  else
    bash "$SCRIPT_DIR/ensure-shared-production-venv.sh" \
      --project "$project_path" \
      --name "$name" \
      --shared-root "$shared_root" \
      --migrate-existing
  fi
  (( migrated += 1 ))
}

migrate_repo() {
  local name=$1 base=$2 current release release_path project
  [[ -d "$base/releases" && -L "$base/current" ]] || return 0
  current=$(basename "$(readlink "$base/current")")
  while IFS= read -r release; do
    (( migrated < MAX_MIGRATIONS )) || break
    [[ "$release" == "$current" ]] && continue
    release_path="$base/releases/$release"
    if [[ "$name" == market-intel ]]; then
      migrate_project "$release_path" "$release_path" "$name"
    else
      for project in market-data-platform strategy-pipeline strategy-research; do
        [[ -d "$release_path/$project" ]] || continue
        migrate_project "$release_path" "$release_path/$project" "$project"
        (( migrated < MAX_MIGRATIONS )) || break
      done
    fi
  done < <(release_order "$base")
}

if [[ "$REPO_FILTER" == all || "$REPO_FILTER" == research-workspace ]]; then
  migrate_repo research-workspace "$PRODUCTION_ROOT/research-workspace"
fi
if [[ "$REPO_FILTER" == all || "$REPO_FILTER" == market-intel ]]; then
  migrate_repo market-intel "$PRODUCTION_ROOT/market-intel"
fi

printf '[migrate] processed %s environment(s)\n' "$migrated"
