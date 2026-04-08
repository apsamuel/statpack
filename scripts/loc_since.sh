#!/usr/bin/env bash

set -euo pipefail

###############################################################################
# loc_since.sh — Count lines of code written since a given point in time
#
# Supported --since formats:
#   Relative  :  "midnight"  "1 hour ago"  "2 days ago"  "yesterday"
#   ISO 8601  :  "2026-04-06"  "2026-04-06T09:00:00"  "2026-04-06T09:00:00Z"
#   RFC 2822  :  "Mon, 06 Apr 2026 00:00:00 -0500"
#   Git native:  any string accepted by git log --since
###############################################################################

PROG="$(basename "$0")"

usage() {
  cat <<EOF
Count lines of code written since a given point in time.

Usage:
  scripts/${PROG} [options]

Options:
  --since <time>       Point in time to count from (required).
                       Accepted formats:
                         Relative  : "midnight", "1 hour ago", "2 days ago"
                         ISO 8601  : "2026-04-06", "2026-04-06T09:00:00"
                         ISO+TZ    : "2026-04-06T09:00:00Z"
                         RFC 2822  : "Mon, 06 Apr 2026 00:00:00 -0500"
  --author <name>      Limit to a specific author name or email pattern.
                       Defaults to the current git user (git config user.name).
  --all-authors        Count commits from all authors (overrides --author).
  --branch <ref>       Branch or ref to inspect (default: current branch).
  --repo <path>        Path to the git repository (default: current directory).
  --include <glob>     Only count files matching this glob (e.g. "*.py").
                       Can be specified multiple times.
  --exclude <glob>     Exclude files matching this glob (e.g. "*.json").
                       Can be specified multiple times.
  --breakdown          Show per-file breakdown in addition to the summary.
  --json               Emit results as JSON.
  --no-color           Disable colored output.
  -h, --help           Show this help.

Examples:
  # Lines written today (current user)
  scripts/${PROG} --since midnight

  # Lines written in the last 4 hours across all authors
  scripts/${PROG} --since "4 hours ago" --all-authors

  # Python-only changes since a specific ISO timestamp
  scripts/${PROG} --since "2026-04-06T09:00:00" --include "*.py"

  # Full per-file breakdown as JSON
  scripts/${PROG} --since yesterday --breakdown --json
EOF
}

###############################################################################
# Helpers
###############################################################################

require_value() {
  local flag="$1" value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "error: missing value for $flag" >&2
    exit 2
  fi
}

die() { echo "error: $*" >&2; exit 1; }

# Portable colour codes — suppressed when NO_COLOR or --no-color is set
init_colors() {
  if [[ "${NO_COLOR:-}" || "${USE_COLOR:-1}" == "0" ]]; then
    C_BOLD="" C_DIM="" C_GREEN="" C_CYAN="" C_YELLOW="" C_RED="" C_RESET=""
  else
    C_BOLD="\033[1m" C_DIM="\033[2m" C_GREEN="\033[32m"
    C_CYAN="\033[36m" C_YELLOW="\033[33m" C_RED="\033[31m" C_RESET="\033[0m"
  fi
}

###############################################################################
# Defaults
###############################################################################

SINCE=""
AUTHOR=""
ALL_AUTHORS=0
BRANCH=""
REPO="."
INCLUDE_GLOBS=()
EXCLUDE_GLOBS=()
BREAKDOWN=0
JSON_OUTPUT=0
USE_COLOR=1

###############################################################################
# Argument parsing
###############################################################################

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)
      require_value "$1" "${2:-}"
      SINCE="$2"; shift 2 ;;
    --author)
      require_value "$1" "${2:-}"
      AUTHOR="$2"; shift 2 ;;
    --all-authors)
      ALL_AUTHORS=1; shift ;;
    --branch)
      require_value "$1" "${2:-}"
      BRANCH="$2"; shift 2 ;;
    --repo)
      require_value "$1" "${2:-}"
      REPO="$2"; shift 2 ;;
    --include)
      require_value "$1" "${2:-}"
      INCLUDE_GLOBS+=("$2"); shift 2 ;;
    --exclude)
      require_value "$1" "${2:-}"
      EXCLUDE_GLOBS+=("$2"); shift 2 ;;
    --breakdown)
      BREAKDOWN=1; shift ;;
    --json)
      JSON_OUTPUT=1; shift ;;
    --no-color)
      USE_COLOR=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "error: unknown option: $1" >&2
      usage; exit 2 ;;
  esac
done

init_colors

###############################################################################
# Validation
###############################################################################

[[ -z "$SINCE" ]] && { echo "error: --since is required" >&2; usage; exit 2; }

if [[ ! -d "$REPO/.git" ]] && ! git -C "$REPO" rev-parse --git-dir &>/dev/null; then
  die "'$REPO' is not a git repository"
fi

###############################################################################
# Build git log arguments
###############################################################################

GIT_LOG_ARGS=(
  -C "$REPO"
  log
  --since="$SINCE"
  --no-merges
  --numstat
  --format="COMMIT:%H"
)

if [[ -n "$BRANCH" ]]; then
  GIT_LOG_ARGS+=("$BRANCH")
fi

if [[ "$ALL_AUTHORS" -eq 0 ]]; then
  if [[ -z "$AUTHOR" ]]; then
    AUTHOR="$(git -C "$REPO" config user.name 2>/dev/null || true)"
    [[ -z "$AUTHOR" ]] && die "Could not determine git user. Set git config user.name or pass --author."
  fi
  GIT_LOG_ARGS+=(--author="$AUTHOR")
fi

# Path filters (must come after --)
PATH_FILTERS=()
for glob in "${INCLUDE_GLOBS[@]+"${INCLUDE_GLOBS[@]}"}"; do
  PATH_FILTERS+=("$glob")
done

if [[ "${#PATH_FILTERS[@]}" -gt 0 ]]; then
  GIT_LOG_ARGS+=("--" "${PATH_FILTERS[@]}")
fi

###############################################################################
# Parse numstat output
###############################################################################

declare -A FILE_ADD FILE_DEL

total_additions=0
total_deletions=0
commit_count=0

while IFS= read -r line; do
  if [[ "$line" == COMMIT:* ]]; then
    (( commit_count++ )) || true
    continue
  fi

  # numstat lines: <added>\t<deleted>\t<path>  (binary files use "-")
  if [[ "$line" =~ ^([0-9]+)[[:space:]]+([0-9]+)[[:space:]]+(.+)$ ]]; then
    added="${BASH_REMATCH[1]}"
    deleted="${BASH_REMATCH[2]}"
    filepath="${BASH_REMATCH[3]}"

    # Apply exclude globs
    skip=0
    for glob in "${EXCLUDE_GLOBS[@]+"${EXCLUDE_GLOBS[@]}"}"; do
      # shellcheck disable=SC2254
      case "$filepath" in
        $glob) skip=1; break ;;
      esac
    done
    [[ "$skip" -eq 1 ]] && continue

    FILE_ADD["$filepath"]=$(( ${FILE_ADD["$filepath"]:-0} + added ))
    FILE_DEL["$filepath"]=$(( ${FILE_DEL["$filepath"]:-0} + deleted ))
    (( total_additions += added )) || true
    (( total_deletions += deleted )) || true
  fi
done < <(git "${GIT_LOG_ARGS[@]}" 2>/dev/null)

net_lines=$(( total_additions - total_deletions ))

###############################################################################
# Output
###############################################################################

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  # Build file breakdown JSON array
  files_json="[]"
  if [[ "$BREAKDOWN" -eq 1 ]]; then
    files_json="["
    first=1
    for f in $(printf '%s\n' "${!FILE_ADD[@]}" | sort); do
      add="${FILE_ADD[$f]}"
      del="${FILE_DEL[$f]:-0}"
      net=$(( add - del ))
      [[ "$first" -eq 0 ]] && files_json+=","
      files_json+="{\"file\":$(printf '%s' "\"$f\""),\"additions\":$add,\"deletions\":$del,\"net\":$net}"
      first=0
    done
    files_json+="]"
  fi

  cat <<EOF
{
  "since": "$SINCE",
  "author": "${AUTHOR:-all}",
  "commits": $commit_count,
  "additions": $total_additions,
  "deletions": $total_deletions,
  "net": $net_lines,
  "files": $files_json
}
EOF
  exit 0
fi

# Human-readable output
printf "${C_BOLD}Lines of code since:${C_RESET} ${C_CYAN}%s${C_RESET}\n" "$SINCE"
printf "${C_BOLD}Author:${C_RESET}             %s\n" "${AUTHOR:-all}"
printf "${C_BOLD}Commits:${C_RESET}            %s\n" "$commit_count"
printf "${C_BOLD}Additions:${C_RESET}          ${C_GREEN}+%d${C_RESET}\n" "$total_additions"
printf "${C_BOLD}Deletions:${C_RESET}          ${C_RED}-%d${C_RESET}\n" "$total_deletions"
printf "${C_BOLD}Net lines:${C_RESET}          ${C_YELLOW}%+d${C_RESET}\n" "$net_lines"

if [[ "$BREAKDOWN" -eq 1 && "${#FILE_ADD[@]}" -gt 0 ]]; then
  printf "\n${C_BOLD}%-60s  %8s  %8s  %8s${C_RESET}\n" "File" "+Added" "-Deleted" "Net"
  printf '%s\n' "$(printf '─%.0s' {1..90})"
  for f in $(printf '%s\n' "${!FILE_ADD[@]}" | sort); do
    add="${FILE_ADD[$f]}"
    del="${FILE_DEL[$f]:-0}"
    net=$(( add - del ))
    printf "${C_DIM}%-60s${C_RESET}  ${C_GREEN}%+8d${C_RESET}  ${C_RED}%+8d${C_RESET}  ${C_YELLOW}%+8d${C_RESET}\n" \
      "$f" "$add" "$(( -del ))" "$net"
  done
fi
