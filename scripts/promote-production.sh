#!/usr/bin/env bash
set -euo pipefail

PRODUCTION_ROOT="${PRODUCTION_ROOT:-/home/richard/code/production}"
LOCK_FILE="$PRODUCTION_ROOT/.promotion.lock"
DRY_RUN=0
REPO_FILTER=all
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

usage() { printf 'usage: %s [--dry-run] [--repo all|research-workspace|market-intel]\n' "$0" >&2; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --repo) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; REPO_FILTER="$1" ;;
    *) usage; exit 2 ;;
  esac
  shift
done
case "$REPO_FILTER" in all|research-workspace|market-intel) ;; *) usage; exit 2 ;; esac

run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  (( DRY_RUN )) || "$@"
}
die() { printf 'promotion blocked: %s\n' "$1" >&2; exit 1; }

current_commit() {
  local base=$1
  [[ -L "$base/current" ]] || return 0
  basename "$(readlink "$base/current")"
}

assert_clean() {
  local repo=$1
  git -C "$repo" diff --quiet || die "dirty worktree: $repo"
  git -C "$repo" diff --cached --quiet || die "staged changes: $repo"
  [[ -z "$(git -C "$repo" status --porcelain --untracked-files=all)" ]] || die "untracked files: $repo"
}

write_manifest() {
  local name=$1 base=$2 commit=$3 out="$2/manifests/$3.txt"
  if (( DRY_RUN )); then printf '+ manifest %s\n' "$out"; return; fi
  mkdir -p "$base/manifests"
  {
    printf 'repository=%s\ncommit=%s\n' "$name" "$commit"
    git -C "$base/releases/$commit" submodule status --recursive 2>/dev/null || true
  } >"$out"
}

ensure_project_venv() {
  local project=$1 name=$2
  local args=(
    --project "$project"
    --name "$name"
    --shared-root "$PRODUCTION_ROOT/shared/venvs"
  )
  if [[ "$name" == market-data-platform ]]; then
    args+=(--extra dev --extra tushare)
  elif [[ "$name" == strategy-pipeline ]]; then
    args+=(--extra dev)
  fi
  bash "$SCRIPT_DIR/ensure-shared-production-venv.sh" "${args[@]}"
}

ensure_release_venvs() {
  local release=$1
  if [[ -d "$release/market-data-platform" && -f "$release/market-data-platform/pyproject.toml" \
    && ! -x "$release/market-data-platform/.venv/bin/python" ]]; then
    ensure_project_venv "$release/market-data-platform" market-data-platform
  fi
  if [[ -d "$release/strategy-pipeline" && -f "$release/strategy-pipeline/pyproject.toml" \
    && ! -x "$release/strategy-pipeline/.venv/bin/python" ]]; then
    ensure_project_venv "$release/strategy-pipeline" strategy-pipeline
  fi
}

refresh_minute_campaign_units() {
  local release=$1
  local mdp_dir="$release/market-data-platform"
  local renderer="$mdp_dir/scripts/operations/render_tushare_minute_campaign_units.py"
  local manifest="${TUSHARE_MINUTE_CAMPAIGN_MANIFEST:-$HOME/data/market-data-platform/metadata/minute_backfill/tushare_historical_campaign_v1_20260831/manifest.json}"
  local data_root="${MARKET_DATA_PLATFORM_DATA_ROOT:-$HOME/data/market-data-platform}"
  local logs_dir="${TUSHARE_MINUTE_LOGS_DIR:-$HOME/.hermes/logs}"
  local output_dir="${TUSHARE_MINUTE_SYSTEMD_OUTPUT_DIR:-$HOME/.config/systemd/user}"

  if [[ ! -f "$manifest" ]]; then
    printf '[research-workspace] minute campaign manifest unavailable; skipped unit render: %s\n' "$manifest" >&2
    return 0
  fi
  [[ -x "$mdp_dir/.venv/bin/python" ]] || die "shared market-data-platform venv missing: $mdp_dir/.venv/bin/python"
  [[ -f "$renderer" ]] || die "minute campaign renderer missing: $renderer"

  run "$mdp_dir/.venv/bin/python" "$renderer" \
    --home "$HOME" \
    --mdp-dir "$mdp_dir" \
    --data-platform-root "$data_root" \
    --campaign-manifest "$manifest" \
    --logs-dir "$logs_dir" \
    --output-dir "$output_dir"
  run systemctl --user daemon-reload
}

sync_hermes_market_intel_workdir() {
  local current="$PRODUCTION_ROOT/market-intel/current"
  local sync_script="$SCRIPT_DIR/sync_hermes_market_intel_workdir.sh"
  [[ -x "$sync_script" ]] || die "Hermes workdir sync script missing or not executable: $sync_script"
  run env \
    MARKET_INTEL_CURRENT="$current" \
    "$sync_script"
}

prepare_release() {
  local name=$1 source=$2 base=$3 remote=$4 ref=$5
  local commit release current tmp fresh=0
  git -C "$source" fetch "$remote" "$ref"
  commit=$(git -C "$source" rev-parse "$remote/$ref")
  release="$base/releases/$commit"
  current=$(current_commit "$base")
  printf '\n[%s] source=%s target=%s\n' "$name" "$source" "$commit"
  if [[ -n "$(git -C "$source" status --porcelain --untracked-files=all)" ]]; then
    printf '[%s] warning: source has local changes; only %s/%s is promoted\n' "$name" "$remote" "$ref" >&2
  fi
  if [[ "$current" == "$commit" ]]; then
    if [[ ! -f "$base/manifests/$commit.txt" ]]; then
      write_manifest "$name" "$base" "$commit"
    fi
    printf '[%s] current already points to %s\n' "$name" "$commit"
    return
  fi
  [[ ! -e "$base/current" || -L "$base/current" ]] || die "$base/current exists but is not a symlink"
  run mkdir -p "$base/releases"
  if [[ ! -e "$release" ]]; then
    fresh=1
    run git -C "$source" worktree add --detach "$release" "$commit"
    if [[ "$name" == research-workspace ]]; then
      run git -C "$release" submodule sync --recursive
      run git -C "$release" submodule update --init --recursive
      if (( ! DRY_RUN )); then
        for project in market-data-platform strategy-pipeline; do
          if [[ -f "$release/$project/pyproject.toml" ]]; then
            ensure_project_venv "$release/$project" "$project"
          fi
        done
      fi
    elif [[ -f "$release/pyproject.toml" ]] && (( ! DRY_RUN )); then
      ensure_project_venv "$release" "$name"
    fi
  else
    assert_clean "$release"
    if (( ! DRY_RUN )) && [[ "$name" == research-workspace ]]; then
      ensure_release_venvs "$release"
    elif (( ! DRY_RUN )) && [[ -f "$release/pyproject.toml" && ! -x "$release/.venv/bin/python" ]]; then
      ensure_project_venv "$release" "$name"
    fi
  fi
  if (( ! DRY_RUN )); then
    # Generated .venv links are operational release metadata and are allowed
    # after the pre-ensure cleanliness gate for both fresh and existing releases.
    write_manifest "$name" "$base" "$commit"
    tmp="$base/.current.$$"
    rm -f "$tmp"
    ln -s "releases/$commit" "$tmp"
    mv -Tf "$tmp" "$base/current"
    printf '[%s] current -> releases/%s\n' "$name" "$commit"
  fi
}

mkdir -p "$PRODUCTION_ROOT"
exec 9>"$LOCK_FILE"
flock -n 9 || die "another promotion is running"
if [[ "$REPO_FILTER" == all || "$REPO_FILTER" == research-workspace ]]; then
  prepare_release research-workspace /home/richard/code/research-workspace "$PRODUCTION_ROOT/research-workspace" github main
  if (( ! DRY_RUN )); then
    refresh_minute_campaign_units "$PRODUCTION_ROOT/research-workspace/current"
  fi
fi
if [[ "$REPO_FILTER" == all || "$REPO_FILTER" == market-intel ]]; then
  prepare_release market-intel /home/richard/code/market-intel "$PRODUCTION_ROOT/market-intel" origin main
  if (( ! DRY_RUN )); then
    sync_hermes_market_intel_workdir
  fi
fi

printf '\nproduction manifest:\n'
for base in "$PRODUCTION_ROOT/research-workspace" "$PRODUCTION_ROOT/market-intel"; do
  [[ -L "$base/current" ]] && printf '%s -> %s\n' "$base" "$(readlink "$base/current")"
done
