#!/usr/bin/env bash
set -euo pipefail

KEEP_RELEASES="${PRODUCTION_KEEP_RELEASES:-5}"
KEEP_VENVS="${PRODUCTION_KEEP_VENVS:-2}"
DRY_RUN=0
BASE=""
SOURCE=""
SHARED_ROOT=""

usage() {
  printf 'usage: %s --base PATH [--keep N] [--keep-venvs N] [--source PATH] [--shared-root PATH] [--dry-run]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; BASE=$1 ;;
    --keep) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; KEEP_RELEASES=$1 ;;
    --keep-venvs) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; KEEP_VENVS=$1 ;;
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
[[ "$KEEP_VENVS" =~ ^[0-9]+$ ]] || { printf 'keep-venvs must be an integer\n' >&2; exit 2; }
(( KEEP_VENVS >= 2 )) || { printf 'keep-venvs must be at least 2\n' >&2; exit 2; }
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

venv_release_paths() {
  local base=$1 release_root current_release release kept=0
  release_root="$base/releases"
  [[ -L "$base/current" ]] || return 0
  current_release=$(basename "$(readlink "$base/current")")
  [[ -d "$release_root/$current_release" ]] || return 0
  printf '%s\n' "$release_root/$current_release"
  (( kept += 1 ))
  while IFS= read -r release; do
    [[ "$release" == "$current_release" ]] && continue
    (( kept < KEEP_VENVS )) || break
    printf '%s\n' "$release_root/$release"
    (( kept += 1 ))
  done < <(BASE="$base" release_order)
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
  local link target env sibling_releases production_root project_root release_path
  local reference_roots=("$BASE/releases")
  production_root=$(dirname "$BASE")
  for sibling_releases in "$production_root"/*/releases; do
    [[ -d "$sibling_releases" ]] || continue
    reference_roots+=("$sibling_releases")
  done
  while IFS= read -r release_path; do
    while IFS= read -r -d '' link; do
      target=$(readlink -f "$link")
      [[ -n "$target" ]] && referenced["$target"]=1
    done < <(find "$release_path" -type l -name .venv -print0)
  done < <(venv_release_paths "$BASE")
  for sibling_releases in "${reference_roots[@]:1}"; do
    while IFS= read -r release_path; do
      while IFS= read -r -d '' link; do
        target=$(readlink -f "$link")
        [[ -n "$target" ]] && referenced["$target"]=1
      done < <(find "$release_path" -type l -name .venv -print0)
    done < <(venv_release_paths "${sibling_releases%/releases}")
  done

  # Current layout is shared/venvs/<project>/<hash>.  Keep supporting the
  # older shared/<project>/<hash> layout, but never treat shared/venvs/<project>
  # itself as an environment.
  for project_root in "$SHARED_ROOT"/*; do
    [[ -d "$project_root" ]] || continue
    if [[ "$(basename "$project_root")" == "venvs" ]]; then
      for env in "$project_root"/*/*; do
        [[ -d "$env" ]] || continue
        [[ -n "${referenced[$(readlink -f "$env")]+x}" ]] && continue
        if (( DRY_RUN )); then
          printf '[prune] would remove unreferenced shared environment %s\n' "$env"
        else
          rm -rf -- "$env"
          printf '[prune] removed unreferenced shared environment %s\n' "$env"
        fi
      done
    else
      for env in "$project_root"/*; do
        [[ -d "$env" ]] || continue
        [[ -n "${referenced[$(readlink -f "$env")]+x}" ]] && continue
        if (( DRY_RUN )); then
          printf '[prune] would remove unreferenced shared environment %s\n' "$env"
        else
          rm -rf -- "$env"
          printf '[prune] removed unreferenced shared environment %s\n' "$env"
        fi
      done
    fi
  done
}

prune_shared_environments
