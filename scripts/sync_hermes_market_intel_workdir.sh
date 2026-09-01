#!/usr/bin/env bash
set -euo pipefail

HERMES_BIN="${HERMES_BIN:-hermes}"
MARKET_INTEL_CURRENT="${MARKET_INTEL_CURRENT:-/home/richard/code/production/market-intel/current}"

if [[ ! -d "$MARKET_INTEL_CURRENT" ]]; then
  printf 'cannot sync Hermes jobs: market-intel current is missing: %s\n' "$MARKET_INTEL_CURRENT" >&2
  exit 1
fi

if ! command -v "$HERMES_BIN" >/dev/null 2>&1 && [[ ! -x "$HERMES_BIN" ]]; then
  printf 'cannot sync Hermes jobs: Hermes executable not found: %s\n' "$HERMES_BIN" >&2
  exit 1
fi

job_ids="$($HERMES_BIN cron list --all 2>/dev/null | awk '
  /^[[:space:]]*[[:alnum:]]+ \[/ { job_id = $1 }
  /^[[:space:]]+Script:/ {
    script = $2
    if (script == "morning_pipeline.sh" || script == "evening_pipeline.sh" || script == "weekly_recap.sh") {
      print job_id
    }
  }
')"

while IFS= read -r job_id; do
  [[ -n "$job_id" ]] || continue
  "$HERMES_BIN" cron edit "$job_id" --workdir "$MARKET_INTEL_CURRENT"
done <<< "$job_ids"
