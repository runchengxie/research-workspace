#!/usr/bin/env bash
# Count tracked source lines in this repository and all initialized submodules.
set -euo pipefail

usage() {
  cat <<'EOF'
用法: bash scripts/count_loc.sh [--skip-init] [--keep-reports DIR]

统计主仓库和递归 submodule 中被 Git 跟踪的文件，并汇总 cloc 报告。
默认会初始化缺失的 submodule；--skip-init 可跳过这一步。
EOF
}

skip_init=false
reports_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-init)
      skip_init=true
      shift
      ;;
    --keep-reports)
      [[ $# -ge 2 ]] || { echo "--keep-reports 需要目录参数" >&2; exit 2; }
      reports_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

command -v git >/dev/null || { echo "找不到 git" >&2; exit 1; }
cloc_bin="${CLOC_BIN:-cloc}"
command -v "$cloc_bin" >/dev/null || { echo "找不到 cloc: $cloc_bin" >&2; exit 1; }

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ "$skip_init" == false ]] && git submodule status --recursive | awk 'substr($1, 1, 1) == "-" { found=1 } END { exit !found }'; then
  echo "==> 初始化缺失的 submodule"
  git submodule update --init --recursive
fi

temporary_reports=false
if [[ -z "$reports_dir" ]]; then
  reports_dir="$(mktemp -d "${TMPDIR:-/tmp}/research-workspace-cloc.XXXXXX")"
  temporary_reports=true
else
  mkdir -p "$reports_dir"
fi
cleanup() {
  if [[ "$temporary_reports" == true ]]; then
    rm -rf "$reports_dir"
  fi
}
trap cleanup EXIT

declare -a report_files=()
run_cloc() {
  local label="$1"
  local directory="$2"
  local filename
  if [[ "$label" == "." ]]; then
    filename="main.txt"
  else
    filename="${label//\//__}.txt"
  fi
  local report="$reports_dir/$filename"
  local file_list="$reports_dir/${filename%.txt}.files"
  local directory_abs
  directory_abs="$(cd "$directory" && pwd)"

  git -C "$directory" ls-files --stage \
    | awk '$1 != "160000" { $1=""; $2=""; $3=""; sub(/^   /, ""); print }' \
    | sed "s#^#$directory_abs/#" > "$file_list"

  echo "==> $label"
  "$cloc_bin" --report-file="$report" --list-file="$file_list"
  report_files+=("$report")
}

run_cloc "." "."
while IFS= read -r submodule_path; do
  [[ -n "$submodule_path" ]] || continue
  run_cloc "$submodule_path" "$submodule_path"
done < <(git submodule foreach --quiet --recursive 'printf "%s\n" "$displaypath"')

echo "==> 汇总"
"$cloc_bin" --sum-reports "${report_files[@]}"

if [[ "$temporary_reports" == false ]]; then
  echo "报告文件已保存到: $reports_dir"
fi
