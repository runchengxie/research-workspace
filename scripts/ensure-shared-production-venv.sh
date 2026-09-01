#!/usr/bin/env bash
set -euo pipefail

PROJECT=""
NAME=""
SHARED_ROOT=""
UV_BIN=uv
EXTRAS=()
MIGRATE_EXISTING=0

usage() {
  printf 'usage: %s --project PATH --name NAME --shared-root PATH [--uv PATH] [--extra NAME ...] [--migrate-existing]\n' "$0" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; PROJECT=$1 ;;
    --name) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; NAME=$1 ;;
    --shared-root) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; SHARED_ROOT=$1 ;;
    --uv) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; UV_BIN=$1 ;;
    --extra) shift; [[ $# -gt 0 ]] || { usage; exit 2; }; EXTRAS+=("$1") ;;
    --migrate-existing) MIGRATE_EXISTING=1 ;;
    *) usage; exit 2 ;;
  esac
  shift
done

[[ -d "$PROJECT" ]] || { printf 'project directory does not exist: %s\n' "$PROJECT" >&2; exit 1; }
[[ -f "$PROJECT/pyproject.toml" ]] || { printf 'missing pyproject.toml: %s\n' "$PROJECT" >&2; exit 1; }
[[ -f "$PROJECT/uv.lock" ]] || { printf 'missing uv.lock: %s\n' "$PROJECT" >&2; exit 1; }
[[ -n "$NAME" && -n "$SHARED_ROOT" ]] || { usage; exit 2; }

venv_link="$PROJECT/.venv"
if [[ -e "$venv_link" && ! -L "$venv_link" ]]; then
  (( MIGRATE_EXISTING )) || {
    printf 'refusing to replace real project venv: %s\n' "$venv_link" >&2
    exit 1
  }
fi

fingerprint=$(sha256sum "$PROJECT/pyproject.toml" "$PROJECT/uv.lock" | sha256sum | cut -d' ' -f1)
env_dir="$SHARED_ROOT/$NAME/$fingerprint"
mkdir -p "$SHARED_ROOT/$NAME"

if [[ -e "$venv_link" && ! -L "$venv_link" ]]; then
  migration_backup="$venv_link.migration-backup.$$"
  [[ ! -e "$migration_backup" ]] || {
    printf 'migration backup already exists: %s\n' "$migration_backup" >&2
    exit 1
  }
  if [[ -e "$env_dir" ]]; then
    [[ -x "$env_dir/bin/python" ]] || {
      printf 'shared environment exists but is not usable: %s\n' "$env_dir" >&2
      exit 1
    }
    mv "$venv_link" "$migration_backup"
    ln -s "$env_dir" "$venv_link"
    if [[ ! -x "$venv_link/bin/python" ]]; then
      rm "$venv_link"
      mv "$migration_backup" "$venv_link"
      printf 'shared environment verification failed: %s\n' "$env_dir" >&2
      exit 1
    fi
    rm -rf -- "$migration_backup"
  else
    mv "$venv_link" "$env_dir"
    ln -s "$env_dir" "$venv_link"
    if [[ ! -x "$venv_link/bin/python" ]]; then
      rm "$venv_link"
      mv "$env_dir" "$venv_link"
      printf 'shared environment verification failed: %s\n' "$env_dir" >&2
      exit 1
    fi
  fi
  printf '[venv] migrated %s/.venv -> %s\n' "$PROJECT" "$env_dir"
  exit 0
fi

if [[ ! -x "$env_dir/bin/python" ]]; then
  mkdir -p "$env_dir"
  printf '[venv] syncing %s into %s\n' "$NAME" "$env_dir"
  uv_args=(sync --locked)
  for extra in "${EXTRAS[@]}"; do
    uv_args+=(--extra "$extra")
  done
  (
    cd "$PROJECT"
    UV_PROJECT_ENVIRONMENT="$env_dir" "$UV_BIN" "${uv_args[@]}"
  )
fi

[[ -x "$env_dir/bin/python" ]] || {
  printf 'uv sync did not create a usable environment: %s\n' "$env_dir" >&2
  exit 1
}

if [[ -L "$venv_link" ]]; then
  rm "$venv_link"
fi
ln -s "$env_dir" "$venv_link"
printf '[venv] %s/.venv -> %s\n' "$PROJECT" "$env_dir"
