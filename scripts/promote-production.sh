#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${RESEARCH_WORKSPACE_ROOT:-/home/richard/code/production/research-workspace}"
REMOTE="${RESEARCH_WORKSPACE_REMOTE:-github}"
REF="${RESEARCH_WORKSPACE_REF:-main}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ $# -gt 0 ]]; then
  printf 'usage: %s [--dry-run]\n' "$0" >&2
  exit 2
fi

die() { printf 'promotion blocked: %s\n' "$1" >&2; exit 1; }
run() {
  printf '+ %q' "$1"
  shift
  printf ' %q' "$@"
  printf '\n'
  (( DRY_RUN )) || "$@"
}

[[ -d "$ROOT_DIR/.git" || -f "$ROOT_DIR/.git" ]] || die "production checkout not found: $ROOT_DIR"
git -C "$ROOT_DIR" diff --quiet || die "production checkout has unstaged changes"
git -C "$ROOT_DIR" diff --cached --quiet || die "production checkout has staged changes"
[[ -z "$(git -C "$ROOT_DIR" status --porcelain --untracked-files=all)" ]] || die "production checkout has untracked files"

run git -C "$ROOT_DIR" fetch "$REMOTE" "$REF"
run git -C "$ROOT_DIR" checkout --detach "$REMOTE/$REF"
run git -C "$ROOT_DIR" submodule sync --recursive
run git -C "$ROOT_DIR" submodule update --init --recursive

if (( ! DRY_RUN )); then
  git -C "$ROOT_DIR" diff --quiet || die "submodule update left parent changes"
  [[ -z "$(git -C "$ROOT_DIR" status --porcelain --untracked-files=all)" ]] || die "submodule update left untracked files"
fi

printf '\nproduction revision manifest (%s):\n' "$ROOT_DIR"
git -C "$ROOT_DIR" rev-parse HEAD
git -C "$ROOT_DIR" submodule status --recursive
