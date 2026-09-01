#!/usr/bin/env bash
set -euo pipefail

KEEP_RELEASES="${PRODUCTION_KEEP_RELEASES:-5}"
DRY_RUN=0
BASE=""
SOURCE=""
SHARED_ROOT=""

usage() {
  printf 'usage: %s --base PATH [--keep N] [--source PATH] [--shared-root PATH] [--dry-run]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; BASE=$1 ;;
    --keep) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; KEEP_RELEASES=$1 ;;
    --source) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; SOURCE=$1 ;;
    --shared-root) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; SHARED_ROOT=$1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) usage; exit 2 ;;
  esac
  shift
done

[[ -n "$BASE" ]] || { usage; exit 2; }
[[ "$KEEP_RELEASES" =~ ^[0-9]+$ ]] || { printf 'keep must be an integer\n' >&2; exit 2; }
(( KEEP_RELEASES >= 2 )) || { printf 'keep must be at least 2\n' >&2; exit 2; }
[[ -d "$BASE/releases" ]] || { printf 'releases directory does not exist: %s\n' "$BASE/releases" >&2; exit 1; }
[[ -L "$BASE/current" ]] || { printf 'current is not a symlink: %s\n' "$BASE/current" >&2; exit 1; }

current_target=$(readlink "$BASE/current")
current_release=$(basename "$current_target")
[[ "$current_target" == "releases/$current_release" ]] || {
  printf 'current must point to a direct child of releases: %s\n' "$current_target" >&2
  exit 1
}
[[ -d "$BASE/releases/$current_release" ]] || {
  printf 'current target does not exist: %s\n' "$BASE/releases/$current_release" >&2
  exit 1
}

release_order() {
  local path release timestamp metadata
  for path in "$BASE/releases"/*; do
    [[ -d "$path" && ! -L "$path" ]] || continue
    release=$(basename "$path")
    metadata="$BASE/manifests/$release.txt"
    if [[ -f "$metadata" ]]; then
      timestamp=$(stat -c '%Y' "$metadata")
    else
      timestamp=$(stat -c '%Y' "$path")
    fi
    printf '%s %s\n' "$timestamp" "$release"
  done | sort -rn | awk '{print $2}'
}

mapfile -t releases < <(release_order)
declare -A keep_set=()
keep_set["$current_release"]=1
kept=1
for release in "${releases[@]}"; do
  [[ "$release" == "$current_release" ]] && continue
  (( kept < KEEP_RELEASES )) || break
  keep_set["$release"]=1
  ((kept += 1))
done

remove_release() {
  local release=$1 path="$BASE/releases/$1"
  if (( DRY_RUN )); then
    printf '[prune] would remove %s\n' "$path"
  elif [[ -n "$SOURCE" ]]; then
    git -C "$SOURCE" worktree remove --force "$path"
    printf '[prune] removed worktree %s\n' "$path"
  else
    rm -rf -- "$path"
    printf '[prune] removed %s\n' "$path"
  fi
}

for release in "${releases[@]}"; do
  [[ -n "${keep_set[$release]+x}" ]] || remove_release "$release"
done

prune_shared_environments() {
  [[ -n "$SHARED_ROOT" && -d "$SHARED_ROOT" ]] || return 0
  declare -A referenced=()
  local link target env sibling_releases production_root
  local reference_roots=("$BASE/releases")
  production_root=$(dirname "$BASE")
  for sibling_releases in "$production_root"/*/releases; do
    [[ -d "$sibling_releases" ]] || continue
    reference_roots+=("$sibling_releases")
  done
  while IFS= read -r -d '' link; do
    target=$(readlink -f "$link")
    [[ -n "$target" ]] && referenced["$target"]=1
  done < <(find "${reference_roots[@]}" -type l -name .venv -print0)

  for env in "$SHARED_ROOT"/*/*; do
    [[ -d "$env" ]] || continue
    [[ -n "${referenced[$(readlink -f "$env")]+x}" ]] && continue
    if (( DRY_RUN )); then
      printf '[prune] would remove unreferenced shared environment %s\n' "$env"
    else
      rm -rf -- "$env"
      printf '[prune] removed unreferenced shared environment %s\n' "$env"
    fi
  done
}

prune_shared_environments
