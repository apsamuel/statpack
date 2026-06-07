#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Raw API fetch helper for Statpack modules.

Usage:
  scripts/raw_api_fetch.sh <module> <operation> [options]

Modules:
  fbi
  cdc

FBI operations (mapped from pkg/data/sources/fbi/main.py get_* functions):
  get-reporting-agencies              -> get_reporting_agencies
  get-arrest-totals-by-state          -> get_arrest_totals_by_state
  get-arrest-counts-by-state          -> get_arrest_counts_by_state
  get-arrest-totals-by-origin         -> get_arrest_totals_by_origin
  get-arrest-counts-by-origin         -> get_arrest_counts_by_origin
  get-nibrs-totals-by-state           -> get_nibrs_totals_by_state
  get-summarized-by-state             -> get_summarized_by_state
  expanded-homicide-state             -> get_expanded_homicide_counts_by_state

CDC WONDER operations:
  get-mortality       POST to D76 (Underlying Cause of Death ICD-10, 1999-2020).
                      Mirrors get_mortality() in pkg/data/sources/cdc/client.py.
  dump-xml            Print the XML request body that would be sent, then exit.
                      Use this to inspect the exact payload before sending.

FBI auth (required for FBI only):
  Uses GOV_API_BASE_URL and GOV_API_KEY from environment by default.
  You can override with --base-url and --api-key.

Options (shared):
  --base-url <url>       Override GOV_API_BASE_URL (FBI only)
  --api-key <key>        Override GOV_API_KEY (FBI only)
  --output <file>        Write raw response body to file
  --dry-run              Print the curl command instead of executing
  --verbose              Show HTTP response headers (-v)
  -h, --help             Show this help

Options (FBI):
  --state <abbr>         State abbreviation (default: NY)
  --offense <code>       FBI offense code (default: ASS)
  --nibrs-code <code>    NIBRS offense code (default: 13A)
  --origin-code <code>   ORI code (default: AL0430200)
  --start-date <MM-YYYY> Start date (default: 01-2020)
  --end-date <MM-YYYY>   End date (default: 12-2020)

Options (CDC):
  --dataset <id>         CDC WONDER dataset ID (default: D76)
  --group-by <dim>       Group results by dimension (default: year).
                         API-supported values: year, month, gender, race, hispanic,
                         age_10yr, age_infant, icd10_chapter, icd10_subchapter, cause_113,
                         autopsy, place_of_death, injury_intent, injury_mechanism,
                         weekday, substance.
                         NOT supported via API (browser-only): state, county,
                         census_region, census_division, hhs_region,
                         urbanization_2006, urbanization_2013.
  --year-start <yyyy>    Limit to years >= yyyy (expands V_D76.V1 to individual year values)
  --year-end <yyyy>      Limit to years <= yyyy (expands V_D76.V1 to individual year values)

Examples:
  scripts/raw_api_fetch.sh cdc dump-xml
  scripts/raw_api_fetch.sh cdc get-mortality
  scripts/raw_api_fetch.sh cdc get-mortality --group-by year --output /tmp/cdc_mortality.xml
  scripts/raw_api_fetch.sh cdc get-mortality --year-start 2015 --year-end 2020 --verbose
  scripts/raw_api_fetch.sh cdc get-mortality --group-by state --dry-run
  scripts/raw_api_fetch.sh fbi get-reporting-agencies --state NY
  scripts/raw_api_fetch.sh fbi get-arrest-totals-by-state --state CA --offense 11 --start-date 01-2024 --end-date 12-2024
  scripts/raw_api_fetch.sh fbi get-nibrs-totals-by-state --state NY --nibrs-code 13A --output examples/nibrs_13a_ny.json
  scripts/raw_api_fetch.sh fbi get-summarized-by-state --state TX --offense V --dry-run
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
OFFENSE="ASS"
NIBRS_CODE="13A"
ORIGIN_CODE="AL0430200"
START_DATE="01-2020"
END_DATE="12-2020"
OUTPUT_FILE=""
DRY_RUN=0
VERBOSE=0
# CDC-specific defaults
CDC_DATASET="D76"
CDC_GROUP_BY="year"
YEAR_START=""
YEAR_END=""

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
    --verbose)
      VERBOSE=1
      shift
      ;;
    --dataset)
      require_value "$1" "${2:-}"
      CDC_DATASET="$2"
      shift 2
      ;;
    --group-by)
      require_value "$1" "${2:-}"
      CDC_GROUP_BY="$2"
      shift 2
      ;;
    --year-start)
      require_value "$1" "${2:-}"
      YEAR_START="$2"
      shift 2
      ;;
    --year-end)
      require_value "$1" "${2:-}"
      YEAR_END="$2"
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

# ── FBI ──────────────────────────────────────────────────────────────────────
if [[ "$MODULE" == "fbi" ]]; then

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
      get-reporting-agencies)
        echo "$BASE_URL/crime/fbi/cde/agency/byStateAbbr/$STATE?API_KEY=$API_KEY"
        ;;
      get-arrest-totals-by-state)
        echo "$BASE_URL/crime/fbi/cde/arrest/state/$STATE/$OFFENSE?type=totals&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
        ;;
      get-arrest-counts-by-state)
        echo "$BASE_URL/crime/fbi/cde/arrest/state/$STATE/$OFFENSE?type=counts&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
        ;;
      get-arrest-totals-by-origin)
        echo "$BASE_URL/crime/fbi/cde/arrest/agency/$ORIGIN_CODE/$OFFENSE?type=totals&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
        ;;
      get-arrest-counts-by-origin)
        echo "$BASE_URL/crime/fbi/cde/arrest/agency/$ORIGIN_CODE/$OFFENSE?type=counts&from=$START_DATE&to=$END_DATE&API_KEY=$API_KEY"
        ;;
      get-nibrs-totals-by-state)
        echo "$BASE_URL/crime/fbi/cde/nibrs/state/$STATE/$NIBRS_CODE?from=$START_DATE&to=$END_DATE&type=totals&API_KEY=$API_KEY"
        ;;
      get-summarized-by-state)
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
  [[ "$VERBOSE" -eq 1 ]] && CURL_ARGS+=(--verbose)

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

# ── CDC WONDER ────────────────────────────────────────────────────────────────
elif [[ "$MODULE" == "cdc" ]]; then

  # Map friendly group-by names to CDC WONDER parameter values (D76 dataset).
  # These correspond to _D76_GROUP_BY in pkg/data/sources/cdc/client.py.
  resolve_group_by() {
    case "$1" in
      # ── Geographic dimensions ──────────────────────────────────────────────
      # The CDC WONDER web service API only returns national data.
      # State, county, region, division, and urbanization group-by dimensions
      # require the browser interface and return HTTP 500 via the API.
      state|county|census_region|census_division|hhs_region|urbanization_2006|urbanization_2013)
        echo "CDC WONDER web service error: group-by '$1' is not supported via the API." >&2
        echo "Only national data are available via /controller/datarequest/." >&2
        echo "State/county/region/division/urbanization grouping requires the browser interface." >&2
        exit 2
        ;;
      year)              echo "D76.V1-level1" ;;
      month)             echo "D76.V1-level2" ;;
      gender)            echo "D76.V7" ;;
      race)              echo "D76.V8" ;;
      hispanic)          echo "D76.V17" ;;
      age_10yr)          echo "D76.V5" ;;
      age_infant)        echo "D76.V6" ;;
      cause_113)         echo "D76.V2" ;;
      icd10_chapter)     echo "D76.V2-level1" ;;
      icd10_subchapter)  echo "D76.V2-level2" ;;
      autopsy)           echo "D76.V20" ;;
      place_of_death)    echo "D76.V21" ;;
      injury_intent)     echo "D76.V22" ;;
      injury_mechanism)  echo "D76.V23" ;;
      substance)         echo "D76.V25" ;;
      weekday)           echo "D76.V24" ;;
      *)
        echo "Unknown group-by dimension: $1" >&2
        echo "Valid (API-supported): year month gender race hispanic age_10yr age_infant" >&2
        echo "       cause_113 icd10_chapter icd10_subchapter autopsy place_of_death" >&2
        echo "       injury_intent injury_mechanism substance weekday" >&2
        echo "Unsupported via API (browser-only): state county census_region census_division" >&2
        echo "       hhs_region urbanization_2006 urbanization_2013" >&2
        exit 2
        ;;
    esac
  }

  GROUP_BY_VAL="$(resolve_group_by "$CDC_GROUP_BY")"

  # Build V_D76.V1 XML value block and matching I_D76.V1 label.
  # CDC WONDER requires either <value>*All*</value> or individual <value>YYYY</value>
  # entries — a single range string like "2015/2020" is not a valid selector.
  if [[ -n "$YEAR_START" || -n "$YEAR_END" ]]; then
    _ys="${YEAR_START:-1999}"
    _ye="${YEAR_END:-2020}"
    YEAR_V_VALUES=""
    for _y in $(seq "$_ys" "$_ye"); do
      YEAR_V_VALUES+="<value>${_y}</value>"
    done
    if [[ -n "$YEAR_START" && -n "$YEAR_END" ]]; then
      YEAR_I_LABEL="${YEAR_START}-${YEAR_END}"
    elif [[ -n "$YEAR_START" ]]; then
      YEAR_I_LABEL="${YEAR_START}-2020"
    else
      YEAR_I_LABEL="1999-${YEAR_END}"
    fi
  else
    YEAR_V_VALUES="<value>*All*</value>"
    YEAR_I_LABEL="*All* (All Dates)"
  fi

  # Validate: year filter + month grouping is a parent/child conflict in CDC WONDER.
  # D76.V1 year selections (level-1) cannot coexist with month grouping (level-2).
  if [[ "$CDC_GROUP_BY" == "month" && ( -n "$YEAR_START" || -n "$YEAR_END" ) ]]; then
    echo "CDC WONDER error: cannot apply --year-start/--year-end when --group-by month." >&2
    echo "Selecting a year (D76.V1 level-1) together with month grouping (D76.V1 level-2)" >&2
    echo "is a parent/child conflict that CDC WONDER rejects with HTTP 500." >&2
    echo "Omit year filters to retrieve all years grouped by month, or supply month-level" >&2
    echo "codes (YYYY/MM) directly via the Python client's filters= parameter." >&2
    exit 2
  fi

  CDC_URL="https://wonder.cdc.gov/controller/datarequest/${CDC_DATASET}"

  # Build XML matching get_mortality() parameter structure in client.py.
  build_cdc_xml() {
    cat <<XMLEOF
<request-parameters>
<parameter><name>B_1</name><value>${GROUP_BY_VAL}</value></parameter>
<parameter><name>B_2</name><value>*None*</value></parameter>
<parameter><name>B_3</name><value>*None*</value></parameter>
<parameter><name>B_4</name><value>*None*</value></parameter>
<parameter><name>B_5</name><value>*None*</value></parameter>
<parameter><name>M_1</name><value>D76.M1</value></parameter>
<parameter><name>M_2</name><value>D76.M2</value></parameter>
<parameter><name>M_3</name><value>D76.M3</value></parameter>
<parameter><name>F_D76.V1</name><value></value></parameter>
<parameter><name>F_D76.V2</name><value></value></parameter>
<parameter><name>F_D76.V4</name><value></value></parameter>
<parameter><name>F_D76.V8</name><value></value></parameter>
<parameter><name>F_D76.V7</name><value></value></parameter>
<parameter><name>F_D76.V17</name><value></value></parameter>
<parameter><name>F_D76.V9</name><value></value></parameter>
<parameter><name>V_D76.V1</name>${YEAR_V_VALUES}</parameter>
<parameter><name>V_D76.V9</name><value>*All*</value></parameter>
<parameter><name>V_D76.V17</name><value>*All*</value></parameter>
<parameter><name>V_D76.V6</name><value></value></parameter>
<parameter><name>V_D76.V5</name><value>*All*</value></parameter>
<parameter><name>V_D76.V7</name><value>*All*</value></parameter>
<parameter><name>V_D76.V8</name><value>*All*</value></parameter>
<parameter><name>V_D76.V19</name><value>*All*</value></parameter>
<parameter><name>V_D76.V20</name><value>*All*</value></parameter>
<parameter><name>V_D76.V21</name><value>*All*</value></parameter>
<parameter><name>V_D76.V22</name><value>*All*</value></parameter>
<parameter><name>V_D76.V23</name><value>*All*</value></parameter>
<parameter><name>V_D76.V25</name><value>*All*</value></parameter>
<parameter><name>V_D76.V27</name><value>*All*</value></parameter>
<parameter><name>I_D76.V1</name><value>${YEAR_I_LABEL}</value></parameter>
<parameter><name>I_D76.V2</name><value>*All* (All Causes of Death)</value></parameter>
<parameter><name>I_D76.V4</name><value>*All* (All Causes of Death)</value></parameter>
<parameter><name>I_D76.V5</name><value>*All* (All Ages)</value></parameter>
<parameter><name>I_D76.V6</name><value>*All* (Ages under 1)</value></parameter>
<parameter><name>I_D76.V7</name><value>*All* (All Genders)</value></parameter>
<parameter><name>I_D76.V8</name><value>*All* (All Races)</value></parameter>
<parameter><name>I_D76.V17</name><value>*All* (All Origins)</value></parameter>
<parameter><name>I_D76.V9</name><value>*All* (All States and DC)</value></parameter>
<parameter><name>I_D76.V19</name><value>*All* (All Urbanization Levels)</value></parameter>
<parameter><name>I_D76.V20</name><value>*All* (All Autopsies)</value></parameter>
<parameter><name>I_D76.V21</name><value>*All* (All Places of Death)</value></parameter>
<parameter><name>I_D76.V22</name><value>*All* (All Intents)</value></parameter>
<parameter><name>I_D76.V23</name><value>*All* (All Mechanisms and All Other Causes)</value></parameter>
<parameter><name>I_D76.V25</name><value>*All* (All Drug/Alcohol Induced Causes)</value></parameter>
<parameter><name>I_D76.V27</name><value>*All* (All HHS Regions)</value></parameter>
<parameter><name>O_bmi</name><value>bmival</value></parameter>
<parameter><name>O_age</name><value>D76.V5</value></parameter>
<parameter><name>O_death_nohr</name><value>0</value></parameter>
<parameter><name>O_location</name><value>D76.V9</value></parameter>
<parameter><name>O_rate_per</name><value>100000</value></parameter>
<parameter><name>O_precision</name><value>1</value></parameter>
<parameter><name>O_title</name><value></value></parameter>
<parameter><name>O_show_totals</name><value>false</value></parameter>
<parameter><name>O_show_zeros</name><value>false</value></parameter>
<parameter><name>O_show_suppressed</name><value>false</value></parameter>
<parameter><name>O_aar</name><value>aar_none</value></parameter>
<parameter><name>O_aar_pop</name><value>0000</value></parameter>
<parameter><name>O_ucd_icd10_103cause</name><value>D76.V27</value></parameter>
<parameter><name>VM_aar_pop</name><value></value></parameter>
<parameter><name>action-Send</name><value>Send</value></parameter>
<parameter><name>finder-stage-D76.V1</name><value>codeset</value></parameter>
<parameter><name>finder-stage-D76.V2</name><value>codeset</value></parameter>
<parameter><name>finder-stage-D76.V8</name><value>codeset</value></parameter>
<parameter><name>finder-stage-D76.V7</name><value>codeset</value></parameter>
<parameter><name>finder-stage-D76.V17</name><value>codeset</value></parameter>
<parameter><name>finder-stage-D76.V9</name><value>codeset</value></parameter>
<parameter><name>stage</name><value>request</value></parameter>
</request-parameters>
XMLEOF
  }

  if [[ "$OPERATION" != "get-mortality" && "$OPERATION" != "dump-xml" ]]; then
    echo "Unsupported CDC operation: $OPERATION (supported: get-mortality, dump-xml)" >&2
    exit 2
  fi

  REQUEST_XML="$(build_cdc_xml)"

  # dump-xml: print the request body without sending it
  if [[ "$OPERATION" == "dump-xml" ]]; then
    echo "=== CDC WONDER XML request (dataset: ${CDC_DATASET}, group-by: ${CDC_GROUP_BY}) ==="
    echo "$REQUEST_XML"
    exit 0
  fi

  CURL_ARGS=(
    --silent
    --show-error
    --location
    --request POST
    --header "User-Agent: StatPack/1.0"
    --header "Accept: application/xml, text/xml, text/html"
    --data "accept_datause_restrictions=true"
    --data-urlencode "request_xml=${REQUEST_XML}"
    "$CDC_URL"
  )
  [[ "$VERBOSE" -eq 1 ]] && CURL_ARGS+=(--verbose)

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "=== XML that will be sent ==="
    echo "$REQUEST_XML"
    echo ""
    echo "=== curl command ==="
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

else
  echo "Unsupported module: $MODULE (supported: fbi, cdc)" >&2
  exit 2
fi
