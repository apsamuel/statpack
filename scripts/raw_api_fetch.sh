#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Raw API fetch helper for Statpack modules.

Usage:
  scripts/raw_api_fetch.sh <module> <operation> [options]

Modules:
  fbi

FBI operations (mapped from pkg/data/sources/fbi/main.py get_* functions):
  reporting-agencies           -> get_cde_reporting_agencies
  arrest-totals-state          -> get_cde_arrest_totals_by_state
  arrest-counts-state          -> get_cde_arrest_counts_by_state
  arrest-totals-origin         -> get_cde_arrest_totals_by_origin
  arrest-counts-origin         -> get_cde_arrest_counts_by_origin
  nibrs-totals-state           -> get_cde_nibrs_totals_by_state
  summarized-state             -> get_cde_summarized_by_state
  expanded-homicide-state      -> get_cde_expanded_homicide_counts_by_state

Auth (required):
  Uses GOV_API_BASE_URL and GOV_API_KEY from environment by default.
  You can override with --base-url and --api-key.

Options:
  --base-url <url>       Override GOV_API_BASE_URL
  --api-key <key>        Override GOV_API_KEY
  --state <abbr>         State abbreviation (default: NY)
  --offense <code>       FBI offense code for arrest endpoints (default: all)
  --nibrs-code <code>    NIBRS offense code (default: 13A)
  --origin-code <code>   ORI code (default: AL0430200)
  --start-date <MM-YYYY> Start date (default: 01-2020)
  --end-date <MM-YYYY>   End date (default: 12-2020)
  --output <file>        Write raw response body to file
  --dry-run              Print the curl command/url instead of executing
  -h, --help             Show this help

Examples:
  scripts/raw_api_fetch.sh fbi reporting-agencies --state NY
  scripts/raw_api_fetch.sh fbi arrest-totals-state --state CA --offense 11 --start-date 01-2024 --end-date 12-2024
  scripts/raw_api_fetch.sh fbi nibrs-totals-state --state NY --nibrs-code 13A --output examples/nibrs_13a_ny.json
  scripts/raw_api_fetch.sh fbi summarized-state --state TX --offense V --dry-run
EOF
}

require_value() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "$value" ]] || [[ "$value" == --* ]]; then
    echo "Missing value for $flag" >&2
    exit 2
  fi
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" || $# -lt 2 ]]; then
  usage
  exit 0
fi

MODULE="$1"
OPERATION="$2"
shift 2

BASE_URL="${GOV_API_BASE_URL:-}"
API_KEY="${GOV_API_KEY:-}"
STATE="NY"
OFFENSE="all"
NIBRS_CODE="13A"
ORIGIN_CODE="AL0430200"
START_DATE="01-2020"
END_DATE="12-2020"
OUTPUT_FILE=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      require_value "$1" "${2:-}"
      BASE_URL="$2"
      shift 2
      ;;
    --api-key)
      require_value "$1" "${2:-}"
      API_KEY="$2"
      shift 2
      ;;
    --state)
      require_value "$1" "${2:-}"
      STATE="$2"
      shift 2
      ;;
    --offense)
      require_value "$1" "${2:-}"
      OFFENSE="$2"
      shift 2
      ;;
    --nibrs-code)
      require_value "$1" "${2:-}"
      NIBRS_CODE="$2"
      shift 2
      ;;
    --origin-code|--ori-code)
      require_value "$1" "${2:-}"
      ORIGIN_CODE="$2"
      shift 2
      ;;
    --start-date)
      require_value "$1" "${2:-}"
      START_DATE="$2"
      shift 2
      ;;
    --end-date)
      require_value "$1" "${2:-}"
      END_DATE="$2"
      shift 2
      ;;
    --output)
      require_value "$1" "${2:-}"
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "$MODULE" != "fbi" ]]; then
  echo "Unsupported module: $MODULE (currently supported: fbi)" >&2
  exit 2
fi

if [[ -z "$BASE_URL" ]]; then
  echo "Missing GOV_API_BASE_URL. Export it or pass --base-url." >&2
  exit 2
fi

if [[ -z "$API_KEY" ]]; then
  echo "Missing GOV_API_KEY. Export it or pass --api-key." >&2
  exit 2
fi

BASE_URL="${BASE_URL%/}"

build_fbi_url() {
  case "$OPERATION" in
    reporting-agencies)
      echo "$BASE_URL/crime/fbi/cde/agency/byStateAbbr/$STATE?API_KEY=$API_KEY"
      ;;
    arrest-totals-state)
      echo "$BASE_URL/crime/fbi/cde/arrest/state/$STATE/$OFFENSE?type=totals&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
      ;;
    arrest-counts-state)
      echo "$BASE_URL/crime/fbi/cde/arrest/state/$STATE/$OFFENSE?type=counts&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
      ;;
    arrest-totals-origin)
      echo "$BASE_URL/crime/fbi/cde/arrest/agency/$ORIGIN_CODE/$OFFENSE?type=totals&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
      ;;
    arrest-counts-origin)
      echo "$BASE_URL/crime/fbi/cde/arrest/agency/$ORIGIN_CODE/$OFFENSE?type=counts&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
      ;;
    nibrs-totals-state)
      echo "$BASE_URL/crime/fbi/cde/nibrs/state/$STATE/$NIBRS_CODE?from=$START_DATE&to=$END_DATE&type=totals&API_KEY=$API_KEY"
      ;;
    summarized-state)
      echo "$BASE_URL/crime/fbi/cde/summarized/state/$STATE/$OFFENSE?from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
      ;;
    expanded-homicide-state)
      echo "$BASE_URL/crime/fbi/cde/shr/state/$STATE?type=totals&from=$START_DATE&to=$END_DATE"
      ;;
    *)
      echo "Unsupported FBI operation: $OPERATION" >&2
      exit 2
      ;;
  esac
}

URL="$(build_fbi_url)"

CURL_ARGS=(
  --silent
  --show-error
  --location
  --request GET
  --header "X-API-KEY: $API_KEY"
  --header "User-Agent: StatPack/1.0"
  --header "Accept: application/json"
  "$URL"
)

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'curl'
  for arg in "${CURL_ARGS[@]}"; do
    printf ' %q' "$arg"
  done
  printf '\n'
  exit 0
fi

if [[ -n "$OUTPUT_FILE" ]]; then
  mkdir -p "$(dirname "$OUTPUT_FILE")"
  curl "${CURL_ARGS[@]}" > "$OUTPUT_FILE"
  echo "Wrote raw response to $OUTPUT_FILE" >&2
else
  curl "${CURL_ARGS[@]}"
fi
