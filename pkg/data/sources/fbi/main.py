import requests
import json
import os

from . import FBI_API_BASE_URL, FBI_API_KEY
from .data import united_states_territories, offense_codes

def get_cde_reporting_agencies(
):
    """
    Fetches FBI agency crosswalk data.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0"
    }
    results = united_states_territories.copy()
    for state_abbr in united_states_territories.keys():
        url = f"{FBI_API_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/{state_abbr}?API_KEY={FBI_API_KEY}"
        print(f"Fetching data from {url}")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"Data fetched successfully for {state_abbr}")
            data = response.json()
            results[state_abbr]["fbi_agencies"] = data
        else:
            response.raise_for_status()

    with open(os.path.join(os.path.dirname(__file__), "../../__datasets","fbi_agency_crosswalk.json"), "w") as f:
        json.dump(results, f, indent=4)
    return results

def get_cde_arrest_totals_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
):
    """
    Fetches FBI arrest data from the government API for the specified year range and state abbreviation.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }
    if offense_code is None: offense_code = "all"
    if state_abbr is None: state_abbr = "NY"
    if start_date is None: start_date = "01-2020"
    if end_date is None: end_date = "12-2020"

    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=totals&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for {state_abbr}")
        data = response.json()
        return data
    else:
        response.raise_for_status()

def get_cde_arrest_counts_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
):
    """
    Fetches FBI arrest data from the government API for the specified year range and state abbreviation.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }
    if offense_code is None: offense_code = "all"
    if state_abbr is None: state_abbr = "NY"
    if start_date is None: start_date = "01-2020"
    if end_date is None: end_date = "12-2020"

    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for {state_abbr}")
        data = response.json()
        return data
    else:
        response.raise_for_status()

def get_cde_arrest_counts_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None
):
    """
    Fetches FBI arrest data from the government API for the specified year range and origin code.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }

    if offense_code is None: offense_code = "all"
    if origin_code is None: origin_code = "AL0430200"
    if start_date is None: start_date = "01-2020"
    if end_date is None: end_date = "12-2020"
    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/agency/{origin_code}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for origin code {origin_code}")
        data = response.json()
        return data
    else:
        response.raise_for_status()

def get_cde_arrest_totals_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None
):
    """
    Fetches FBI arrest data from the government API for the specified year range and origin code.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }

    if offense_code is None: offense_code = "all"
    if origin_code is None: origin_code = "AL0430200"
    if start_date is None: start_date = "01-2020"
    if end_date is None: end_date = "12-2020"
    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/agency/{origin_code}/{offense_code}?type=totals&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for origin code {origin_code}")
        data = response.json()
        return data
    else:
        response.raise_for_status()
