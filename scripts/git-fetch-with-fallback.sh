#!/usr/bin/env bash
set -u

if [[ $# -ne 3 ]]; then
  printf 'usage: %s REPOSITORY REMOTE REF\n' "$0" >&2
  exit 2
fi

REPOSITORY=$1
REMOTE=$2
REF=$3
errors=()

fetch_ref() {
  local label=$1 url=$2 auth_header=${3:-}
  local output status
  if [[ -n "$auth_header" ]]; then
    output=$(GIT_FETCH_AUTHORIZATION="$auth_header" git -C "$REPOSITORY" \
      --config-env=http.extraheader=GIT_FETCH_AUTHORIZATION \
      fetch "$url" "+$REF:refs/remotes/$REMOTE/$REF" 2>&1)
  else
    output=$(git -C "$REPOSITORY" fetch "$url" "+$REF:refs/remotes/$REMOTE/$REF" 2>&1)
  fi
  status=$?
  if (( status == 0 )); then
    printf '[fetch] %s\n' "$label"
    return 0
  fi
  errors+=("$label: ${output//$'\n'/ }")
  return "$status"
}

if fetch_ref "configured remote $REMOTE" "$REMOTE"; then
  exit 0
fi

remote_url=$(git -C "$REPOSITORY" remote get-url "$REMOTE" 2>/dev/null || true)
github_path=
case "$remote_url" in
  https://github.com/*|http://github.com/*)
    github_path=${remote_url#*github.com/}
    ;;
  git@github.com:*|ssh://git@github.com/*)
    github_path=${remote_url#*github.com:}
    github_path=${github_path#*github.com/}
    ;;
esac
github_path=${github_path%.git}

if [[ -n "$github_path" ]] && command -v gh >/dev/null 2>&1; then
  token=$(gh auth token 2>/dev/null || true)
  if [[ -n "$token" ]]; then
    if fetch_ref "github cli (authenticated HTTPS)" "https://github.com/$github_path.git" "AUTHORIZATION: bearer $token"; then
      exit 0
    fi
  else
    errors+=("github cli: no authenticated token")
  fi
elif [[ -n "$github_path" ]]; then
  errors+=("github cli: command not found")
fi

if [[ -n "$github_path" ]]; then
  if fetch_ref "ssh" "git@github.com:$github_path.git"; then
    exit 0
  fi
  if fetch_ref "https" "https://github.com/$github_path.git"; then
    exit 0
  fi
fi

printf 'all fetch methods failed for %s %s %s:\n' "$REPOSITORY" "$REMOTE" "$REF" >&2
for error in "${errors[@]}"; do
  printf '  %s\n' "$error" >&2
done
exit 1
