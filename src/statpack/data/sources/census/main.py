import requests
from bs4 import BeautifulSoup
import pandas as pd
from . import CENSUS_API_BASE_URL, CENSUS_API_KEY

from .models import us_state_mapping, us_race_mapping, us_state_abbr_to_fips


def _normalize_variables(variables) -> list[str]:
    """Normalize a variables argument into a list that always includes NAME."""
    if variables is None:
        var_list = []
    elif isinstance(variables, str):
        var_list = [v.strip() for v in variables.split(",") if v.strip()]
    else:
        var_list = [str(v).strip() for v in variables if str(v).strip()]

    if not any(v.upper() == "NAME" for v in var_list):
        var_list = ["NAME", *var_list]
    return var_list


def _states_to_fips(states) -> list[int]:
    """Convert state abbreviations/FIPS codes/names into FIPS integer codes."""
    if states is None:
        return []
    if isinstance(states, str):
        tokens = [s.strip() for s in states.split(",") if s.strip()]
    else:
        tokens = [str(s).strip() for s in states if str(s).strip()]

    name_to_fips = {name.lower(): code for code, name in us_state_mapping.items()}

    fips_codes: list[int] = []
    for token in tokens:
        if token.upper() in us_state_abbr_to_fips:
            fips_codes.append(us_state_abbr_to_fips[token.upper()])
        elif token.isdigit() and int(token) in us_state_mapping:
            fips_codes.append(int(token))
        elif token.lower() in name_to_fips:
            fips_codes.append(name_to_fips[token.lower()])
        else:
            raise ValueError(f"Unknown state: {token!r}")
    return fips_codes


def _records_from_response(data: list) -> list[dict]:
    """Convert a Census API JSON response (header row + data rows) into records."""
    if not data:
        return []
    headers = data[0]
    return [{headers[i]: row[i] for i in range(len(headers))} for row in data[1:]]


def get_census_acs_variables(year: int = 2024, dataset: str = "acs/acs1") -> pd.DataFrame:
    """Scrapes the available variables for a dataset from the HTML page

    Args:
        year (int, optional): _description_. Defaults to 2024.
        dataset (str, optional): _description_. Defaults to "acs/acs1".
    """
    url = f"{CENSUS_API_BASE_URL}/{year}/{dataset}/variables.html"

    response = requests.get(url)
    if response.status_code == 200:
        print(f"Data fetched successfully for year {year} and dataset {dataset}")
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        variables = []
        if table:
            headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) == len(headers):
                    record = {headers[i]: cols[i].get_text(strip=True) for i in range(len(headers))}
                    variables.append(record)
        return pd.DataFrame(variables)
    else:
        response.raise_for_status()
    return pd.DataFrame(variables)


# ACS - American Community Survey
# api.census.gov/data/2024/acs/acs1?get=NAME,group(B01001)&for=us:1&key=YOUR_KEY_GOES_HERE
# https://api.census.gov/data/2024/acs/acs1.html -
def get_census_acs_detailed(variables=None, year: int = 2024, dataset: str = "acs/acs1") -> pd.DataFrame:
    var_list = _normalize_variables(variables)
    url = f"{CENSUS_API_BASE_URL}/{year}/{dataset}?get={','.join(var_list)}&for=us:*&key={CENSUS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Data fetched successfully for year {year}")
        return pd.DataFrame(_records_from_response(response.json()))
    response.raise_for_status()
    return pd.DataFrame()


def get_census_acs_detailed_by_state(
    variables=None, year: int = 2024, dataset: str = "acs/acs1", states=None
) -> pd.DataFrame:
    var_list = _normalize_variables(variables)
    fips_codes = _states_to_fips(states)
    state_predicate = ",".join(str(code) for code in fips_codes) if fips_codes else "*"

    url = (
        f"{CENSUS_API_BASE_URL}/{year}/{dataset}?get={','.join(var_list)}"
        f"&for=state:{state_predicate}&key={CENSUS_API_KEY}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Data fetched successfully for year {year} and states {state_predicate}")
        return pd.DataFrame(_records_from_response(response.json()))
    response.raise_for_status()
    return pd.DataFrame()


def get_census_acs_detailed_by_state_county(
    variables=None, year: int = 2024, dataset: str = "acs/acs1", states=None
) -> pd.DataFrame:
    var_list = _normalize_variables(variables)
    fips_codes = _states_to_fips(states)

    results: list[dict] = []
    state_predicates = [str(code) for code in fips_codes] if fips_codes else ["*"]
    for state_predicate in state_predicates:
        url = (
            f"{CENSUS_API_BASE_URL}/{year}/{dataset}?get={','.join(var_list)}"
            f"&for=county:*&in=state:{state_predicate}&key={CENSUS_API_KEY}"
        )
        response = requests.get(url)
        if response.status_code == 200:
            results.extend(_records_from_response(response.json()))
        else:
            response.raise_for_status()
    print(f"Data fetched successfully for year {year} and states {','.join(state_predicates)}")
    return pd.DataFrame(results)


# ACS "race alone" variables (table B02001) plus Hispanic-or-Latino ethnicity
# (B03003_003E). Hispanic origin is an ethnicity that overlaps every race, so it is
# reported alongside the mutually-exclusive "alone" race categories rather than summed
# with them.
RACE_ACS_VARIABLES = {
    "B02001_002E": "White alone",
    "B02001_003E": "Black or African American alone",
    "B02001_004E": "American Indian and Alaska Native alone",
    "B02001_005E": "Asian alone",
    "B02001_006E": "Native Hawaiian and Other Pacific Islander alone",
    "B02001_007E": "Some Other Race alone",
    "B02001_008E": "Two or More Races",
    "B03003_003E": "Hispanic or Latino",
}


def get_census_population_by_race(
    states=None, year: int = 2024, dataset: str = "acs/acs1", raw: bool = False
) -> pd.DataFrame | list[dict]:
    """Fetch population counts by race/ethnicity for the requested states.

    Uses the ACS "race alone" variables (table ``B02001``) plus Hispanic-or-Latino
    ethnicity (``B03003_003E``). Returns long-format records shaped
    ``{"state", "variable", "label", "population"}`` (default) or a DataFrame.

    Args:
        states: State abbreviations, FIPS codes, or names. None queries all states.
        year (int, optional): ACS estimate year. Defaults to 2024.
        dataset (str, optional): Census dataset path. Defaults to "acs/acs1".
        raw (bool, optional): When True, return raw list[dict] records.
    """
    variables = list(RACE_ACS_VARIABLES.keys())
    df = get_census_acs_detailed_by_state(variables=variables, year=year, dataset=dataset, states=states)

    records: list[dict] = []
    for _, row in df.iterrows():
        state_name = row.get("NAME")
        for variable, label in RACE_ACS_VARIABLES.items():
            value = row.get(variable)
            if value is None:
                continue
            records.append({"state": state_name, "variable": variable, "label": label, "population": int(value)})

    if raw:
        return records
    return pd.DataFrame(records)
