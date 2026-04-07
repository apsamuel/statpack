import requests
from bs4 import BeautifulSoup
import pandas as pd
from . import CENSUS_API_BASE_URL, CENSUS_API_KEY

from .data import us_state_mapping, us_race_mapping


def get_census_acs_variables(
    year: int = 2024, dataset: str = "acs/acs1"
) -> pd.DataFrame:
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
            headers = [
                th.get_text(strip=True) for th in table.find("tr").find_all("th")
            ]
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) == len(headers):
                    record = {
                        headers[i]: cols[i].get_text(strip=True)
                        for i in range(len(headers))
                    }
                    variables.append(record)
        return pd.DataFrame(variables)
    else:
        response.raise_for_status()
    return pd.DataFrame(variables)


# ACS - American Community Survey
# api.census.gov/data/2024/acs/acs1?get=NAME,group(B01001)&for=us:1&key=YOUR_KEY_GOES_HERE
# https://api.census.gov/data/2024/acs/acs1.html -
def get_census_acs_detailed(year: int = 2024) -> pd.DataFrame:
    results = []
    url = f"{CENSUS_API_BASE_URL}/{year}/acs/acs1?get=NAME,B01001_001E&for=us:*&key={CENSUS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Data fetched successfully for year {year}")
        data = response.json()
        # return data
        # get header row values
        headers = data[0]
        for row in data[1:]:
            record = {headers[i]: row[i] for i in range(len(headers))}
            results.append(record)
    else:
        response.raise_for_status()
    return pd.DataFrame(results)


def get_census_acs_detailed_by_state(
    year: int = 2024, state_fips: str = None  # Default to New York
) -> pd.DataFrame:
    results = []
    if state_fips is None:
        url = f"{CENSUS_API_BASE_URL}/{year}/acs/acs1?get=NAME,B01001_001E&for=state:*&key={CENSUS_API_KEY}"
        # for code, state in state_fips_codes.items():
        #  https://api.census.gov/data/2024/acs/acs1?get=NAME,B01001_001E&for=state:*&key=YOUR_KEY_GOES_HERE
    else:
        url = f"{CENSUS_API_BASE_URL}/{year}/acs/acs1?get=NAME,B01001_001E&for=state:{state_fips}&key={CENSUS_API_KEY}"

    response = requests.get(url)
    if response.status_code == 200:
        print(
            f"Data fetched successfully for year {year} and state FIPS {state_fips or 'ALL'}"
        )
        data = response.json()
        headers = data[0]
        for row in data[1:]:
            record = {headers[i]: row[i] for i in range(len(headers))}
            results.append(record)
    else:
        response.raise_for_status()
    return pd.DataFrame(results)


def get_census_acs_detailed_by_state_county(
    year: int = 2024,
    state_fips: str = None,
    county_fips: str = None,  # Default to New York County
) -> pd.DataFrame:
    results = []
    if state_fips is None or county_fips is None:
        url = f"{CENSUS_API_BASE_URL}/{year}/acs/acs1?get=NAME,B01001_001E&for=county:*&in=state:*&key={CENSUS_API_KEY}"
        # for code, state in state_fips_codes.items():
        #  https://api.census.gov/data/2024/acs/acs1?get=NAME,B01001_001E&for=state:*&key=YOUR_KEY_GOES_HERE
    else:
        url = f"{CENSUS_API_BASE_URL}/{year}/acs/acs1?get=NAME,B01001_001E&for=county:{county_fips}&in=state:{state_fips}&key={CENSUS_API_KEY}"

    response = requests.get(url)
    if response.status_code == 200:
        print(
            f"Data fetched successfully for year {year}, state FIPS {state_fips or 'ALL'}, county FIPS {county_fips or 'ALL'}"
        )
        data = response.json()
        headers = data[0]
        for row in data[1:]:
            record = {headers[i]: row[i] for i in range(len(headers))}
            results.append(record)
    else:
        response.raise_for_status()
    return pd.DataFrame(results)
