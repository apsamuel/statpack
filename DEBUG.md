# DEBUG.md

This guide documents direct module usage in a Python REPL.

If you are debugging endpoint behavior, response shape, or DataFrame transforms, this is usually faster than running through the CLI.

## 1) Start a REPL with environment variables

From repo root:

```bash
cd /Users/aaronsamuel/devops/software/statpack
source .venv/bin/activate
export GOV_API_BASE_URL="https://api.usa.gov"
export GOV_API_KEY="<your-fbi-api-gov-key>"
export CENSUS_API_BASE_URL="https://api.census.gov/data"
export CENSUS_API_KEY="<your-census-api-key>"
python
```

## 2) FBI examples

```python
import pandas as pd
from pkg.data.sources.fbi.main import (
    get_cde_reporting_agencies,
    get_cde_summarized_by_state,
    get_cde_arrest_totals_by_state,
    get_cde_arrest_counts_by_state,
    get_cde_arrest_totals_by_origin,
    get_cde_arrest_counts_by_origin,
    get_cde_nibrs_totals_by_state,
)
```

### Reporting agencies

```python
df = get_cde_reporting_agencies()
print(df.shape)
df.head()
```

### Summarized (wide monthly shape)

```python
df = get_cde_summarized_by_state(
    start_date="01-2020",
    end_date="12-2024",
    state_abbr="NY",
    offense_code="HOM",
)
print(df.shape)
df.filter(regex=r"^(date|requested\.|offenses\.)").head()
```

### Arrest totals by state

```python
df = get_cde_arrest_totals_by_state(
    start_date="01-2020",
    end_date="12-2024",
    state_abbr="NY",
    offense_code=11,
)
print(df.shape)
df.head()
```

### Arrest counts by state

```python
df = get_cde_arrest_counts_by_state(
    start_date="01-2020",
    end_date="12-2024",
    state_abbr="NY",
    offense_code=11,
)
print(df.shape)
df.head()
```

### Arrest totals/counts by ORI

```python
df_totals = get_cde_arrest_totals_by_origin(
    start_date="01-2020",
    end_date="12-2024",
    origin_code="AL0430200",
    offense_code=11,
)

df_counts = get_cde_arrest_counts_by_origin(
    start_date="01-2020",
    end_date="12-2024",
    origin_code="AL0430200",
    offense_code=11,
)

print(df_totals.shape, df_counts.shape)
```

### NIBRS totals by state

```python
df = get_cde_nibrs_totals_by_state(
    start_date="01-2020",
    end_date="12-2024",
    state_abbr="NY",
    nibrs_code="HOM",
)
print(df.shape)
df.head()
```

## 3) Census examples

```python
from pkg.data.sources.census.main import (
    get_census_acs_variables,
    get_census_acs_detailed,
    get_census_acs_detailed_by_state,
    get_census_acs_detailed_by_state_county,
)
```

### List ACS variables

```python
df = get_census_acs_variables(year=2024, dataset="acs/acs1")
print(df.shape)
df.head()
```

### ACS national

```python
df = get_census_acs_detailed(year=2024)
print(df.shape)
df.head()
```

### ACS by state (FIPS)

```python
# NY FIPS = 36
df = get_census_acs_detailed_by_state(year=2024, state_fips="36")
print(df.shape)
df.head()
```

### ACS by state/county (FIPS)

```python
# New York County (Manhattan): state=36, county=061
df = get_census_acs_detailed_by_state_county(year=2024, state_fips="36", county_fips="061")
print(df.shape)
df.head()
```

## 4) Quick debug patterns

### Inspect return schema

```python
print(df.columns.tolist())
print(df.dtypes)
```

### Save intermediate debug output

```python
df.to_csv("debug_output.csv", index=False)
```

### Catch and inspect API errors

```python
import traceback

try:
    df = get_cde_summarized_by_state(state_abbr="XX", offense_code="HOM")
except Exception as exc:
    print(type(exc).__name__, exc)
    traceback.print_exc()
```

## 5) REPL vs CLI

- Use `main.py` when you want standardized output and reproducible command lines.
- Use REPL when you need iterative inspection, schema checks, and quick experimentation.
- Keep function signatures here aligned with source in `pkg/data/sources/fbi/main.py` and `pkg/data/sources/census/main.py`.
