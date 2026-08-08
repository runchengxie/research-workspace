#!/usr/bin/env bash
set -euo pipefail

SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENT="core"
DESTINATION="$SCRIPT_ROOT"
DEEP_VERIFY=0

usage() {
  printf '%s\n' \
    '用法：./restore_d11_h5_repro.sh [选项]' \
    '' \
    '  --component core    校验并恢复核心复现包，默认值' \
    '  --component all     校验并恢复核心包，同时合并分钟数据包' \
    '  --component minute  向已经恢复的核心目录补装分钟数据包' \
    '  --destination DIR   恢复目录的父目录，默认是脚本所在目录' \
    '  --deep-verify       解压后逐文件复核包内校验清单' \
    '  -h, --help          显示帮助'
}

fail() {
  printf '恢复失败：%s\n' "$1" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --component)
      [[ $# -ge 2 ]] || fail '--component 缺少参数'
      COMPONENT="$2"
      shift 2
      ;;
    --destination)
      [[ $# -ge 2 ]] || fail '--destination 缺少参数'
      DESTINATION="$2"
      shift 2
      ;;
    --deep-verify)
      DEEP_VERIFY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "未知参数：$1"
      ;;
  esac
done

case "$COMPONENT" in
  core|all|minute) ;;
  *) fail "不支持的组件：$COMPONENT" ;;
esac

command -v tar >/dev/null 2>&1 || fail '缺少 tar'
command -v sha256sum >/dev/null 2>&1 || fail '缺少 sha256sum'

shopt -s nullglob
core_candidates=("$SCRIPT_ROOT"/d11-h5-repro-*.tar.zst)
[[ ${#core_candidates[@]} -eq 1 ]] || fail '脚本旁边必须恰好有一个核心复现包'
CORE_ARCHIVE="${core_candidates[0]}"
PACKAGE_NAME="$(basename "$CORE_ARCHIVE" .tar.zst)"
PACKAGE_ROOT="$DESTINATION/$PACKAGE_NAME"
minute_candidates=("$SCRIPT_ROOT"/d11-h5-minute-*-for-"$PACKAGE_NAME".tar.zst)

verify_archive() {
  local archive="$1"
  local checksum="$archive.sha256"
  [[ -f "$checksum" ]] || fail "缺少归档校验文件：$checksum"
  (cd "$(dirname "$archive")" && sha256sum --check "$(basename "$checksum")")
}

minute_archive() {
  [[ ${#minute_candidates[@]} -eq 1 ]] || fail '脚本旁边必须恰好有一个匹配的分钟数据包'
  printf '%s\n' "${minute_candidates[0]}"
}

deep_verify() {
  "$PACKAGE_ROOT/start.sh" verify
  if [[ "$COMPONENT" == "all" || "$COMPONENT" == "minute" ]]; then
    (
      cd "$PACKAGE_ROOT"
      sha256sum --check MINUTE_PACKAGE_FILES.sha256
    )
  fi
}

restore_core() {
  [[ ! -e "$PACKAGE_ROOT" ]] || fail "目标已经存在：$PACKAGE_ROOT"
  mkdir -p "$DESTINATION"
  local staging
  staging="$(mktemp -d "$DESTINATION/.d11-h5-restore.XXXXXX")"
  trap 'rm -rf -- "$staging"' EXIT
  verify_archive "$CORE_ARCHIVE"
  tar --zstd -xf "$CORE_ARCHIVE" -C "$staging"
  if [[ "$COMPONENT" == "all" ]]; then
    local minute
    minute="$(minute_archive)"
    verify_archive "$minute"
    tar --zstd -xf "$minute" -C "$staging"
  fi
  [[ -d "$staging/$PACKAGE_NAME" ]] || fail '归档中的顶层目录与包名不一致'
  mv "$staging/$PACKAGE_NAME" "$PACKAGE_ROOT"
  rmdir "$staging"
  trap - EXIT
}

restore_minute() {
  [[ -d "$PACKAGE_ROOT" ]] || fail "请先恢复核心包：$PACKAGE_ROOT"
  local minute
  minute="$(minute_archive)"
  verify_archive "$minute"
  tar --zstd -xf "$minute" -C "$DESTINATION"
}

if [[ "$COMPONENT" == "minute" ]]; then
  restore_minute
else
  restore_core
fi

"$PACKAGE_ROOT/start.sh" doctor
if [[ "$DEEP_VERIFY" == 1 ]]; then
  deep_verify
fi
printf '恢复完成：%s\n' "$PACKAGE_ROOT"
