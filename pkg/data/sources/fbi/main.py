import re
import requests
import json
import os
import pandas as pd
import time

from . import FBI_API_BASE_URL, FBI_API_KEY
from .data import (
    us_territory_mapping,
    get_abbr_from_state,
    get_state_from_abbr,
    us_offense_mapping,
    get_offense_from_code,
    get_code_from_offense,
    nibrs_offense_codes,
    nibrs_offense_mapping,
)

def get_cde_reporting_agencies() -> pd.DataFrame:
    """
    Fetches FBI agency crosswalk data.
    """
    headers = {"X-API-KEY": FBI_API_KEY, "User-Agent": "StatPack/1.0"}
    results = []
    for state_abbr in us_territory_mapping.keys():
        url = f"{FBI_API_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/{state_abbr}?API_KEY={FBI_API_KEY}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"Data fetched successfully for {state_abbr}")
            data = response.json()
            for ori, agency in data.items():
                if isinstance(agency, list):
                    for item in agency:
                        if not isinstance(item, dict):
                            continue
                        results.append(item)

        else:
            response.raise_for_status()
    return pd.DataFrame(results)

def get_cde_arrest_totals_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
    table: str = "arrestee race",
) -> pd.DataFrame:
    """
    Fetches FBI arrest data from the government API for the specified year range and state abbreviation.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }
    results = []
    if offense_code is None:
        offense_code = "all"
    if state_abbr is None:
        state_abbr = "NY"
    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=totals&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for {state_abbr}")
        data = response.json()
        available_keys = list(
            k.lower() for k in list(data.keys()) if k not in ["cde_properties"]
        )
        if table not in available_keys:
            raise ValueError(
                f"Table '{table}' not found in response. Available tables: {available_keys}"
            )
        # we need to add the header row to results

        for table_name, table_data in data.items():
            if table_name.lower() == table.lower():
                for entry, value in table_data.items():
                    results.append({table_name: entry, "Value": value})
    else:
        response.raise_for_status()

    return pd.DataFrame(results)

def get_cde_arrest_counts_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
) -> pd.DataFrame:
    """
    Fetches FBI arrest data from the government API for the specified year range and state abbreviation.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }
    results = [
    ]
    if offense_code is None:
        offense_code = "all"

    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    if state_abbr is None:
        for state_abbr, state in us_territory_mapping.items():
            url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print(f"Data fetched successfully for {state_abbr}")
                data = response.json()
                state_name = get_state_from_abbr(state_abbr)
                rates = data.get("rates")
                state_rates = rates.get(f"{state_name} Arrests", {})
                dates = list(state_rates.keys())
                totals = data.get("actuals")
                state_totals = totals.get(f"{state_name} Arrests", {})
                population = data.get("populations")
                state_population = population.get("population", {}).get(state_name, None)
                for d in dates:
                    results.append(
                        {
                            "Date": d,
                            "State": state_name,
                            "Offense": (
                                get_offense_from_code(int(offense_code))
                                if offense_code != "all"
                                else "all"
                            ),
                            "Arrest Rate": state_rates.get(d, None),
                            "Arrest Total": state_totals.get(d, None),
                            "Population": (
                                state_population.get(d, None)
                                if state_population
                                else None
                            ),
                        }
                    )
            else:
                response.raise_for_status()
    else:
        url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"Data fetched successfully for {state_abbr}")
            data = response.json()
            state_name = get_state_from_abbr(state_abbr)
            rates = data.get("rates")
            state_rates = rates[f"{state_name} Arrests"]
            dates = list(state_rates.keys())
            totals = data.get("actuals")
            state_totals = totals[f"{state_name} Arrests"]
            population = data.get("populations")
            state_population = population.get("population", {}).get(state_name, None)

            for d in dates:
                results.append(
                    {
                        "Date": d,
                        "State": state_name,
                        "Offense": (
                            get_offense_from_code(int(offense_code))
                            if offense_code != "all"
                            else "all"
                        ),
                        "Arrest Rate": state_rates.get(d, None),
                        "Arrest Total": state_totals.get(d, None),
                        "Population": (
                            state_population.get(d, None) if state_population else None
                        ),
                    }
                    # [
                    #     d,
                    #     state_name,
                    #     get_offense_from_code(int(offense_code)) if offense_code != "all" else "all",
                    #     state_rates.get(d, None),
                    #     state_totals.get(d, None),
                    #     state_population.get(d, None) if state_population else None
                    # ]
                )

        else:
            response.raise_for_status()
    return pd.DataFrame(results).set_index(['Date', 'State']).sort_index()


def get_cde_arrest_totals_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None,
):
    """
    Fetches FBI arrest data from the government API for the specified year range and origin code.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }
    results = []

    if offense_code is None:
        offense_code = "all"

    if origin_code is None:
        origin_code = "AL0430200"

    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/agency/{origin_code}/{offense_code}?type=totals&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for origin code {origin_code}")
        data = response.json()
        return data
    else:
        response.raise_for_status()


def get_cde_arrest_counts_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None,
):
    """
    Fetches FBI arrest data from the government API for the specified year range and origin code.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
        "Accept": "application/json",
    }

    if offense_code is None:
        offense_code = "all"

    if origin_code is None:
        origin_code = "AL0430200"

    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/arrest/agency/{origin_code}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for origin code {origin_code}")
        data = response.json()
        return data
    else:
        response.raise_for_status()

def get_cde_nibrs_totals_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    nibrs_code: int = None,
):
    """gather a state wide NIBRS

    Args:
        start_date (str, optional): _description_. Defaults to None.
        end_date (str, optional): _description_. Defaults to None.
        state_abbr (str, optional): _description_. Defaults to None.
        nibrs_code (int, optional): _description_. Defaults to None.
    """

    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
        "Accept": "application/json",
    }

    results = []
    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    if state_abbr is None:
        for state_abbr, state in us_territory_mapping.items():
            if nibrs_code is None:
                for nibrs_info in nibrs_offense_codes:
                    nibrs_code = nibrs_info.code

                    url = f"{FBI_API_BASE_URL}/crime/fbi/cde/nibrs/state/{state_abbr}/{nibrs_code}?from={start_date}&to={end_date}&type=totals&API_KEY={FBI_API_KEY}"
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        print(f"Data fetched successfully for {state_abbr} and NIBRS code {nibrs_code}")
                        data = response.json()
                        results.append({
                            "state_code": state_abbr,
                            "nibrs_code": nibrs_code,
                            "crime": nibrs_offense_mapping[nibrs_code]["name"],
                            **{f"victim.age.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["age"].items()},
                            **{f"victim.sex.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["sex"].items()},
                            **{f"victim.race.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["race"].items()},
                            **{f"victim.location.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["location"].items()},
                            **{f"victim.ethnicity.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["ethnicity"].items()},
                            **{f"offender.age.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["age"].items()},
                            **{f"offender.sex.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["sex"].items()},
                            **{f"offender.race.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["race"].items()},
                            **{f"offender.ethnicity.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["ethnicity"].items()},
                            "nibrs_code": nibrs_code,
                            "crime": nibrs_offense_mapping[nibrs_code]["name"],
                        })
                        time.sleep(1)
                    else:
                        response.raise_for_status()
            else:
                url = f"{FBI_API_BASE_URL}/crime/fbi/cde/nibrs/state/{state_abbr}/{nibrs_code}?from={start_date}&to={end_date}&type=totals&API_KEY={FBI_API_KEY}"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    print(f"Data fetched successfully for {state_abbr}")
                    data = response.json()
                    results.append({
                        "state": state_abbr,
                        "nibrs_code": nibrs_code,
                        "crime": nibrs_offense_mapping[nibrs_code]["name"],
                        **{f"victim.age.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["age"].items()},
                        **{f"victim.sex.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["sex"].items()},
                        **{f"victim.race.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["race"].items()},
                        **{f"victim.location.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["location"].items()},
                        **{f"victim.ethnicity.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["ethnicity"].items()},
                        **{f"offender.age.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["age"].items()},
                        **{f"offender.sex.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["sex"].items()},
                        **{f"offender.race.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["race"].items()},
                        **{f"offender.ethnicity.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["ethnicity"].items()},
                        # **{f"offender_relationship_{k}": v for k, v in data["offender"]["relationship"].items()},

                        # "data": data
                    })
                    time.sleep(1)
                else:
                    response.raise_for_status()

    else:
        if nibrs_code is None:
            for nibrs_info in nibrs_offense_codes:
                nibrs_code = nibrs_info.code

                url = f"{FBI_API_BASE_URL}/crime/fbi/cde/nibrs/state/{state_abbr}/{nibrs_code}?from={start_date}&to={end_date}&type=totals&API_KEY={FBI_API_KEY}"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    print(f"Data fetched successfully for {state_abbr} and NIBRS code {nibrs_code}")
                    data = response.json()
                    results.append({
                        "state": state_abbr,
                        "nibrs_code": nibrs_code,
                        "crime": nibrs_offense_mapping[nibrs_code]["name"],
                        **{f"victim.age.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["age"].items()},
                        **{f"victim.sex.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["sex"].items()},
                        **{f"victim.race.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["race"].items()},
                        **{f"victim.location.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["location"].items()},
                        **{f"victim.ethnicity.{k.lower().replace(' ', '_')}": v for k, v in data["victim"]["ethnicity"].items()},
                        **{f"offender.age.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["age"].items()},
                        **{f"offender.sex.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["sex"].items()},
                        **{f"offender.race.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["race"].items()},
                        **{f"offender.ethnicity.{k.lower().replace(' ', '_')}": v for k, v in data["offender"]["ethnicity"].items()},
                        # **{f"offender_relationship_{k}": v for k, v in data["offender"]["relationship"].items()},
                    })
                    time.sleep(1)
                else:
                    response.raise_for_status()
        else:
            url = f"{FBI_API_BASE_URL}/crime/fbi/cde/nibrs/state/{state_abbr}/{nibrs_code}?from={start_date}&to={end_date}&type=totals&API_KEY={FBI_API_KEY}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print(f"Data fetched successfully for {state_abbr} and NIBRS code {nibrs_code}")
                data = response.json()
                results.append({
                    "state": state_abbr,
                    "nibrs_code": nibrs_code,
                    "crime": nibrs_offense_mapping[nibrs_code]["name"],
                    **{f"victim.age.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["victim"]["age"].items()},
                    **{f"victim.sex.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["victim"]["sex"].items()},
                    **{f"victim.race.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["victim"]["race"].items()},
                    **{f"victim.location.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["victim"]["location"].items()},
                    **{f"victim.ethnicity.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["victim"]["ethnicity"].items()},
                    **{f"offender.age.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["offender"]["age"].items()},
                    **{f"offender.sex.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["offender"]["sex"].items()},
                    **{f"offender.race.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["offender"]["race"].items()},
                    **{f"offender.ethnicity.{k.lower().replace(' ', '_').replace(',', '-')}": v for k, v in data["offender"]["ethnicity"].items()},
                })
            else:
                response.raise_for_status()
    return results