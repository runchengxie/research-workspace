#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    *) printf 'usage: %s [--dry-run]\n' "$0" >&2; exit 2 ;;
  esac
  shift
done

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SYSTEMD_USER_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE="$SYSTEMD_USER_DIR/production-maintenance.service"
TIMER="$SYSTEMD_USER_DIR/production-maintenance.timer"

printf '[install] systemd user directory: %s\n' "$SYSTEMD_USER_DIR"
printf '+ mkdir -p %q\n' "$SYSTEMD_USER_DIR"
printf '+ cp %q %q\n' "$SCRIPT_DIR/systemd/production-maintenance.service" "$SERVICE"
printf '+ cp %q %q\n' "$SCRIPT_DIR/systemd/production-maintenance.timer" "$TIMER"
printf '+ systemctl --user daemon-reload\n'
printf '+ systemctl --user enable --now production-maintenance.timer\n'

(( DRY_RUN )) && exit 0
mkdir -p "$SYSTEMD_USER_DIR"
cp "$SCRIPT_DIR/systemd/production-maintenance.service" "$SERVICE"
cp "$SCRIPT_DIR/systemd/production-maintenance.timer" "$TIMER"
systemctl --user daemon-reload
systemctl --user enable --now production-maintenance.timer
