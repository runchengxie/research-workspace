#!/usr/bin/env bash
set -euo pipefail

PRODUCTION_ROOT="${PRODUCTION_ROOT:-/home/richard/code/production}"

check_repo() {
  local name=$1 source=$2 base=$3 remote=$4 ref=$5 current target
  git -C "$source" fetch "$remote" "$ref" >/dev/null
  target=$(git -C "$source" rev-parse "$remote/$ref")
  current=missing
  [[ -L "$base/current" ]] && current=$(basename "$(readlink "$base/current")")
  if [[ "$current" == "$target" ]]; then
    printf '[up-to-date] %s %s\n' "$name" "$target"
  else
    printf '[update-available] %s current=%s target=%s\n' "$name" "$current" "$target"
  fi
}

check_repo research-workspace /home/richard/code/research-workspace "$PRODUCTION_ROOT/research-workspace" github main
check_repo market-intel /home/richard/code/market-intel "$PRODUCTION_ROOT/market-intel" origin main
