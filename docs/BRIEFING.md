# Statpack Briefing

## Overview

**Statpack** is an open-source Python library designed to simplify the process of gathering, cleaning, and analyzing statistical data from various government and public data sources. It provides modular, extensible interfaces to multiple data APIs with built-in caching, error handling, and data transformation capabilities.

## Purpose

Statpack addresses the need for a reliable, maintainable solution for accessing and working with complex statistical datasets. It abstracts away the complexity of API authentication, data parsing, and format inconsistencies, allowing you to focus on data analysis rather than data plumbing.

## Architecture

The library is organized into modular data sources located in `pkg/data/sources/`:

- **`fbi/`**: FBI Crime Data Explorer (CDE) and NIBRS (National Incident-Based Reporting System) data
- **`census/`**: U.S. Census Bureau American Community Survey (ACS) data
- **`gov/`**: Generic government API utilities (in development)

Each source module contains:

- `__init__.py`: Configuration and API credentials
- `main.py`: Primary functions for fetching data
- `data.py`: Pydantic models, mappings, and data utilities
- `client.py`: HTTP client utilities (where applicable)

## Using Statpack in the Python REPL

### Import Structure

```python
import pkg.data.sources.fbi as fbi_source
import pkg.data.sources.census as census_source
```

Or import specific functions:

```python
from pkg.data.sources.fbi import (
    get_cde_reporting_agencies,
    get_cde_arrest_counts_by_state,
    get_cde_nibrs_totals_by_state
)
from pkg.data.sources.census import (
    get_census_acs_variables,
    get_census_acs_detailed_by_state
)
```

---

## FBI Module (`pkg.data.sources.fbi`)

The FBI module provides access to crime statistics from the FBI's Crime Data Explorer API. Data is returned as pandas DataFrames with MultiIndex for flexible querying.

### Core Functions

#### 1. **`get_cde_reporting_agencies()`**

Retrieves a crosswalk of FBI reporting agencies by state.

```python
agencies = fbi_source.get_cde_reporting_agencies()
# Returns: DataFrame with agency names, ORI codes, and state information
```

#### 2. **`get_cde_arrest_totals_by_state(state, offense_code, start_year, end_year)`**

Fetches total arrest counts by state for a specific offense.

**Parameters:**

- `state`: State abbreviation (e.g., "NY", "CA") or full name
- `offense_code`: FBI offense code (e.g., 11 for "Murder")
- `start_year`: Starting year for the query
- `end_year`: Ending year for the query

**Example:**

```python
# Get murder arrests in New York from 2020-2024
arrests = fbi_source.get_cde_arrest_totals_by_state(
    state="NY",
    offense_code=11,
    start_year=2020,
    end_year=2024
)
```

#### 3. **`get_cde_arrest_counts_by_state(state, offense_code, start_year, end_year, breakdown=None)`**

Fetches arrest counts with demographic breakdowns (by age, race, sex, etc.).

**Parameters:**

- `state`: State abbreviation or name
- `offense_code`: FBI offense code
- `start_year`: Starting year
- `end_year`: Ending year
- `breakdown`: Optional breakdown dimension (e.g., "by_race", "by_age")

**Example:**

```python
# Get arrest counts by race for drug violations in California
arrests = fbi_source.get_cde_arrest_counts_by_state(
    state="CA",
    offense_code=35,
    start_year=2022,
    end_year=2024,
    breakdown="by_race"
)
# Returns: MultiIndex DataFrame (Date, State) with arrest counts
```

#### 4. **`get_cde_arrest_totals_by_origin(ori_code, offense_code, start_year, end_year)`**

Fetches arrests for a specific agency (identified by ORI code).

**Parameters:**

- `ori_code`: Agency ORI identifier
- `offense_code`: FBI offense code
- `start_year`: Starting year
- `end_year`: Ending year

**Example:**

```python
# Get arrests for a specific agency
arrests = fbi_source.get_cde_arrest_totals_by_origin(
    ori_code="NY0010100",
    offense_code=11,
    start_year=2020,
    end_year=2024
)
```

#### 5. **`get_cde_arrest_counts_by_origin(ori_code, offense_code, start_year, end_year)`**

Similar to `get_cde_arrest_totals_by_origin` but with demographic breakdowns.

#### 6. **`get_cde_nibrs_totals_by_state(state, nibrs_code, start_year, end_year)`**

Fetches NIBRS (National Incident-Based Reporting System) data by state.

**Parameters:**

- `state`: State abbreviation or name
- `nibrs_code`: NIBRS offense code (e.g., "ASS" for Aggravated Assault)
- `start_year`: Starting year
- `end_year`: Ending year

**Example:**

```python
# Get NIBRS homicide data for Texas
homicides = fbi_source.get_cde_nibrs_totals_by_state(
    state="TX",
    nibrs_code="HOM",
    start_year=2020,
    end_year=2024
)
```

### Data Utilities

#### Offense Code Mappings

The FBI module provides utilities for working with offense codes:

```python
from pkg.data.sources.fbi.data import (
    us_offense_mapping,      # Maps legacy codes to offense details
    nibrs_offense_mapping,   # Maps NIBRS codes to offense details
    get_code_from_offense,   # Function to look up code by name
    get_offense_from_code,   # Function to look up name by code
)

# Example: Look up offense name
offense_name = get_offense_from_code(11)  # Returns "Murder and Nonnegligent Manslaughter"

# Example: Examine offense mapping
print(us_offense_mapping[11])
# {'name': 'Murder and Nonnegligent Manslaughter', 'category': 'Violent Crime', 'short_name': 'Murder'}
```

#### State Mappings

```python
from pkg.data.sources.fbi.data import (
    us_territory_mapping,    # Maps state abbreviations to state names
    get_state_from_abbr,     # Get full state name from abbreviation
    get_abbr_from_state,     # Get abbreviation from state name
)

# Example
abbr = get_abbr_from_state("New York")  # Returns "NY"
state = get_state_from_abbr("NY")       # Returns "New York"
```

---

## Census Module (`pkg.data.sources.census`)

The Census module provides access to demographic and economic data from the U.S. Census Bureau's American Community Survey (ACS).

### Core Functions

#### 1. **`get_census_acs_variables(year, dataset)`**

Retrieves available variables for a given ACS dataset and year.

**Parameters:**

- `year`: Survey year (e.g., 2024)
- `dataset`: Dataset identifier (default: "acs/acs1" for 1-year estimates)

**Example:**

```python
variables = census_source.get_census_acs_variables(year=2024, dataset="acs/acs1")
# Returns: DataFrame with variable names, descriptions, and metadata
```

#### 2. **`get_census_acs_detailed(variables, year, dataset)`**

Fetches detailed ACS data for specified variables (national-level).

**Parameters:**

- `variables`: List of variable codes (e.g., ["B01001_001E", "B19013_001E"])
- `year`: Survey year
- `dataset`: Dataset identifier

**Example:**

```python
# Get total population and median household income (national)
data = census_source.get_census_acs_detailed(
    variables=["B01001_001E", "B19013_001E"],
    year=2024,
    dataset="acs/acs1"
)
```

#### 3. **`get_census_acs_detailed_by_state(variables, year, dataset, states)`**

Fetches ACS data broken down by state.

**Parameters:**

- `variables`: List of variable codes
- `year`: Survey year
- `dataset`: Dataset identifier
- `states`: List of state abbreviations or FIPS codes

**Example:**

```python
# Get population and income data for NY and CA
data = census_source.get_census_acs_detailed_by_state(
    variables=["B01001_001E", "B19013_001E"],
    year=2024,
    dataset="acs/acs1",
    states=["NY", "CA"]
)
# Returns: DataFrame with data broken down by state
```

#### 4. **`get_census_acs_detailed_by_state_county(variables, year, dataset, states)`**

Fetches ACS data at the county level for specified states.

**Parameters:**

- `variables`: List of variable codes
- `year`: Survey year
- `dataset`: Dataset identifier
- `states`: List of states to query

**Example:**

```python
# Get demographic data at county level for Texas
data = census_source.get_census_acs_detailed_by_state_county(
    variables=["B01001_001E"],
    year=2024,
    dataset="acs/acs1",
    states=["TX"]
)
# Returns: DataFrame with county-level granularity
```

### Data Utilities

#### State and Race Mappings

```python
from pkg.data.sources.census.data import (
    us_state_mapping,    # Maps FIPS codes to state names
    us_race_mapping,     # Maps race codes to descriptions
)

# Example
print(us_state_mapping[36])  # Returns "New York"
print(us_race_mapping[1])    # Returns race category description
```

---

## Working with MultiIndex DataFrames

Many functions return pandas MultiIndex DataFrames for efficient slicing and grouping:

```python
df = fbi_source.get_cde_arrest_counts_by_state(
    state="all",
    offense_code=11,
    start_year=2020,
    end_year=2024
)

# Access data for a specific state
ny_data = df.xs('New York', level='State')

# Access specific date and state
specific_data = df.loc[('2024-01', 'New York')]

# Group by state and sum
by_state = df.groupby(level='State').sum()
```

---

## Environment Setup

Ensure you have the required API credentials set as environment variables:

```bash
# FBI API
export FBI_API_BASE_URL="https://api.data.gov/crime/fbi/cde/..."
export FBI_API_KEY="your_fbi_api_key"

# Census API
export CENSUS_API_BASE_URL="https://api.census.gov/data"
export CENSUS_API_KEY="your_census_api_key"

# Government API (if using .gov module)
export GOV_API_BASE_URL="https://api.data.gov"
export GOV_API_KEY="your_gov_api_key"
```

---

## Common Workflows

### 1. Compare Arrest Trends Across States

```python
from pkg.data.sources.fbi import get_cde_arrest_counts_by_state

states = ["NY", "CA", "TX"]
offense = 11  # Murder

for state in states:
    data = get_cde_arrest_counts_by_state(
        state=state,
        offense_code=offense,
        start_year=2020,
        end_year=2024
    )
    print(f"{state}: {data}")
```

### 2. Analyze Demographic Breakdowns

```python
# Get arrests by race for a specific state and offense
arrests_by_race = get_cde_arrest_counts_by_state(
    state="CA",
    offense_code=35,  # Drug violations
    start_year=2022,
    end_year=2024,
    breakdown="by_race"
)

# Group and analyze
summary = arrests_by_race.groupby(level='State').sum()
```

### 3. Fetch Census Demographics by State

```python
from pkg.data.sources.census import get_census_acs_detailed_by_state

# Get population and poverty rate for multiple states
data = get_census_acs_detailed_by_state(
    variables=["B01001_001E", "B17001_002E"],  # Total pop, below poverty
    year=2024,
    dataset="acs/acs1",
    states=["NY", "CA", "TX", "FL"]
)

print(data)
```

---

## Troubleshooting

### API Authentication Errors

Ensure your API keys are correctly set in the environment:

```python
import os
print(os.getenv('FBI_API_KEY'))
print(os.getenv('CENSUS_API_KEY'))
```

### DataFrame Issues

If you receive empty DataFrames or unexpected results:

- Verify the offense code or variable code is valid
- Check the year range is available for the dataset
- Ensure state abbreviations or names are correctly formatted

### Rate Limiting

The APIs have rate limits. If you receive 429 errors, add delays between requests:

```python
import time
time.sleep(1)  # Wait 1 second between requests
```

---

## Further Resources

- [FBI Crime Data Explorer](https://crime-data-explorer.fr.cloud.gov/)
- [Census Bureau API Documentation](https://api.census.gov/data.html)
- [Statpack Repository](https://github.com/apsamuel/statpack)

---

**Last Updated:** April 4, 2026
