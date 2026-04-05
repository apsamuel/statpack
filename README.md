# Statpack

Statpack is a data-ingestion toolkit focused on public statistical sources, with a CLI-first workflow for:

- FBI Crime Data Explorer (CDE)
- U.S. Census ACS

![statpack](./docs/assets/stat-main.png)

## Quick Start

### 1) Clone and install dependencies

```bash
git clone https://github.com/apsamuel/statpack.git
cd statpack
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Set required environment variables

`main.py` imports both FBI and Census modules at startup, so all four environment variables are required.

```bash
export GOV_API_BASE_URL="https://api.usa.gov"
export GOV_API_KEY="<your-fbi-api-gov-key>"
export CENSUS_API_BASE_URL="https://api.census.gov/data"
export CENSUS_API_KEY="<your-census-api-key>"
```

### 3) Run CLI help

```bash
python main.py --help
```

## CLI Usage

General form:

```bash
python main.py <source> <command> [command-args] [output-args]
```

`<source>`:

- `fbi`
- `census`

## Common Output Args (all leaf commands)

| Arg | Required | Default | Description |
| --- | --- | --- | --- |
| `--output` | No | `stdout` | Output destination (`stdout` or `file:/path/to/file`) |
| `--format` | No | `csv` | Output format: `json`, `csv`, `tsv`, `html`, `markdown`, `parquet` |

## FBI Commands

Base:

```bash
python main.py fbi <command> ...
```

### `agencies`

Fetch FBI reporting agencies.

```bash
python main.py fbi agencies --format csv --output stdout
```

Args: none (besides common output args).

### `arrests`

Fetch arrests by state.

```bash
python main.py fbi arrests --state NY --offense 11 --start-year 2020 --end-year 2024 --format json
```

| Arg | Required | Type | Description |
| --- | --- | --- | --- |
| `--state` | No | string | State abbreviation or name (defaults to all states at CLI layer) |
| `--offense` | Yes | int | FBI offense code |
| `--start-year` | Yes | int | Starting year |
| `--end-year` | Yes | int | Ending year |
| `--breakdown` | No | string | Demographic breakdown hint (example: `by_race`, `by_age`) |

### `arrests-by-origin`

Fetch arrests by agency ORI code.

```bash
python main.py fbi arrests-by-origin --ori-code AL0430200 --offense 11 --start-year 2020 --end-year 2024 --format csv
```

| Arg | Required | Type | Description |
| --- | --- | --- | --- |
| `--ori-code` | Yes | string | Agency ORI code |
| `--offense` | Yes | int | FBI offense code |
| `--start-year` | Yes | int | Starting year |
| `--end-year` | Yes | int | Ending year |

### `nibrs`

Fetch NIBRS data by state and offense code.

```bash
python main.py fbi nibrs --nibrs-code HOM --start-year 2020 --end-year 2024 --format csv
```

| Arg | Required | Type | Description |
| --- | --- | --- | --- |
| `--state` | No | string | State abbreviation or name (default: all states) |
| `--nibrs-code` | Yes | string | NIBRS offense code (`HOM`, `ASS`, `ROB`, etc.) |
| `--start-year` | Yes | int | Starting year |
| `--end-year` | Yes | int | Ending year |

### `summarized`

Fetch summarized offense trend data by state.

```bash
python main.py fbi summarized --state NY --offense HOM --start-year 2020 --end-year 2024 --format csv
```

| Arg | Required | Type | Description |
| --- | --- | --- | --- |
| `--state` | No | string | State abbreviation (default: all states) |
| `--offense` | No | enum | One of: `V`, `ASS`, `LAR`, `MVT`, `HOM`, `RPE`, `ROB`, `ARS`, `P` |
| `--start-year` | Yes | int | Starting year |
| `--end-year` | Yes | int | Ending year |

## Census Commands

Base:

```bash
python main.py census <command> ...
```

### `acs-variables`

List available ACS variables for a dataset.

```bash
python main.py census acs-variables --year 2024 --dataset acs/acs1 --format markdown
```

| Arg | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `--year` | No | int | `2024` | Survey year |
| `--dataset` | No | string | `acs/acs1` | Census dataset identifier |

### `acs-detailed`

Fetch ACS data at national level.

```bash
python main.py census acs-detailed --variables B01001_001E,B01001_002E --year 2024 --dataset acs/acs1 --format json
```

| Arg | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `--variables` | Yes | string | - | Comma-separated variable codes |
| `--year` | No | int | `2024` | Survey year |
| `--dataset` | No | string | `acs/acs1` | Census dataset identifier |

### `acs-by-state`

Fetch ACS data by state.

```bash
python main.py census acs-by-state --variables B01001_001E --states NY,CA,TX --year 2024 --format json
```

| Arg | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `--variables` | Yes | string | - | Comma-separated variable codes |
| `--states` | Yes | string | - | Comma-separated state abbreviations |
| `--year` | No | int | `2024` | Survey year |
| `--dataset` | No | string | `acs/acs1` | Census dataset identifier |

### `acs-by-state-county`

Fetch ACS data by state and county.

```bash
python main.py census acs-by-state-county --variables B01001_001E --states NY,CA --year 2024 --format csv
```

| Arg | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `--variables` | Yes | string | - | Comma-separated variable codes |
| `--states` | Yes | string | - | Comma-separated state abbreviations |
| `--year` | No | int | `2024` | Survey year |
| `--dataset` | No | string | `acs/acs1` | Census dataset identifier |

## Output Examples

Write to stdout:

```bash
python main.py fbi agencies --output stdout --format markdown
```

Write to file:

```bash
python main.py fbi nibrs --nibrs-code HOM --start-year 2020 --end-year 2024 --output file:out/nibrs.csv --format csv
```

## Making CLI Extension Easy

The CLI is centralized in `main.py`:

- Parser wiring: `setup_fbi_subparsers()` and `setup_census_subparsers()`
- Common output args: `_add_output_args()`
- Command handlers: `FBICommands` and `CensusCommands`

Use this checklist when adding a command/arg:

1. Add a handler method to `FBICommands` or `CensusCommands`.
2. Add a subparser in the corresponding `setup_*_subparsers()` function.
3. Add new command args with `add_argument(...)`.
4. Set handler with `set_defaults(func=...)`.
5. Reuse `_add_output_args(parser)` for standardized output controls.
6. Add one usage example to this README under the correct section.

Minimal template:

```python
@staticmethod
def my_new_command(args) -> pd.DataFrame:
    return some_data_function(
        required_arg=args.required_arg,
        optional_arg=args.optional_arg,
    )

my_cmd = fbi_subparsers.add_parser("my-command", help="Describe the command")
my_cmd.add_argument("--required-arg", required=True)
my_cmd.add_argument("--optional-arg")
my_cmd.set_defaults(func=FBICommands.my_new_command)
_add_output_args(my_cmd)
```

## REPL / Debugging Docs

For Python REPL workflows (direct module usage), see `DEBUG.md`.
