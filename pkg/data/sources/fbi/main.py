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


def _flatten_get_cde_summarized_by_state_payload_wide(
    payload: dict,
    requested_state_abbr: str,
    requested_offense_code: str,
) -> pd.DataFrame:
    """Flatten one summarized API payload into a super-wide monthly DataFrame.

    Output grain: one row per date for the requested state/offense.
    """

    def _normalize_key(value: str) -> str:
        normalized = str(value).strip().lower()
        normalized = re.sub(r"[\s/\-]+", "_", normalized)
        normalized = normalized.replace("%", "percent")
        normalized = re.sub(r"[^a-z0-9_\.]+", "", normalized)
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        return normalized

    monthly_maps: list[tuple[str, dict]] = []

    offense_rates = payload.get("offenses", {}).get("rates", {})
    for series_name, series_values in offense_rates.items():
        monthly_maps.append((f"offenses.rates.{_normalize_key(series_name)}", series_values))

    offense_actuals = payload.get("offenses", {}).get("actuals", {})
    for series_name, series_values in offense_actuals.items():
        monthly_maps.append((f"offenses.actuals.{_normalize_key(series_name)}", series_values))

    coverage = payload.get("tooltips", {}).get("Percent of Population Coverage", {})
    for series_name, series_values in coverage.items():
        monthly_maps.append((f"tooltips.coverage_percent.{_normalize_key(series_name)}", series_values))

    populations = payload.get("populations", {}).get("population", {})
    for series_name, series_values in populations.items():
        monthly_maps.append((f"populations.population.{_normalize_key(series_name)}", series_values))

    participated_populations = payload.get("populations", {}).get("participated_population", {})
    for series_name, series_values in participated_populations.items():
        monthly_maps.append((f"populations.participated_population.{_normalize_key(series_name)}", series_values))

    all_dates: set[str] = set()
    for _, series_values in monthly_maps:
        if isinstance(series_values, dict):
            all_dates.update(series_values.keys())

    left_headers = payload.get("tooltips", {}).get("leftYAxisHeaders", {})
    max_data_date = payload.get("cde_properties", {}).get("max_data_date", {}).get("UCR")
    last_refresh_date = payload.get("cde_properties", {}).get("last_refresh_date", {}).get("UCR")

    rows: list[dict] = []
    for date_value in sorted(all_dates):
        row = {
            "date": date_value,
            "requested.state_abbr": requested_state_abbr,
            "requested.state_name": get_state_from_abbr(requested_state_abbr),
            "requested.offense_code": requested_offense_code,
            "meta.max_data_date.ucr": max_data_date,
            "meta.last_refresh_date.ucr": last_refresh_date,
            "tooltips.left_y_axis_header.rates": left_headers.get("yAxisHeaderRates"),
            "tooltips.left_y_axis_header.actual": left_headers.get("yAxisHeaderActual"),
        }
        for column_name, series_values in monthly_maps:
            row[column_name] = series_values.get(date_value) if isinstance(series_values, dict) else None
        rows.append(row)

    return pd.DataFrame(rows)

def get_cde_summarized_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: str = None,
) -> pd.DataFrame:
    """Fetch FBI CDE summarized offense data by state and return a wide DataFrame.

    Each row represents one date for a given state/offense combination.
    """
    frames: list[pd.DataFrame] = []
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }
    supported_offense_codes = ["V", "ASS", "LAR", "MVT", "HOM", "RPE", "ROB", "ARS", "P"]

    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    states_to_query = (
        list(us_territory_mapping.keys()) if state_abbr is None else [state_abbr]
    )
    offenses_to_query = (
        supported_offense_codes if offense_code is None else [str(offense_code)]
    )

    for abbr in states_to_query:
        for code in offenses_to_query:
            url = (
                f"{FBI_API_BASE_URL}/crime/fbi/cde/summarized/state/{abbr}/{code}"
                f"?from={start_date}&to={end_date}&API_KEY={FBI_API_KEY}"
            )
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                frames.append(
                    _flatten_get_cde_summarized_by_state_payload_wide(
                        payload=data,
                        requested_state_abbr=abbr,
                        requested_offense_code=code,
                    )
                )
            else:
                response.raise_for_status()

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True).sort_values(
        by=["date", "requested.state_abbr", "requested.offense_code"],
        ignore_index=True,
    )

def get_cde_reporting_agencies(
) -> pd.DataFrame:
    """
    Fetches FBI agency crosswalk data.
    """
    headers = {"X-API-KEY": FBI_API_KEY, "User-Agent": "StatPack/1.0"}
    results = []
    for state_abbr in us_territory_mapping.keys():
        url = f"{FBI_API_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/{state_abbr}?API_KEY={FBI_API_KEY}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # print(f"Data fetched successfully for {state_abbr}")
            data = response.json()
            for ori, agency in data.items():
                if isinstance(agency, list):
                    for item in agency:
                        if not isinstance(item, dict):
                            continue
                        results.append(item)

        # else:
        #     response.raise_for_status()
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
    # else:
    #     response.raise_for_status()

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
            # else:
            #     response.raise_for_status()
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

        # else:
        #     response.raise_for_status()
    return pd.DataFrame(results).set_index(['Date', 'State']).sort_index()

def get_cde_arrest_totals_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None,
) -> pd.DataFrame:
    """
    Fetches FBI arrest totals by agency ORI code and returns a DataFrame.
    Each row represents one date with rate and actual arrest counts.
    """
    headers = {
        "X-API-KEY": FBI_API_KEY,
        "User-Agent": "StatPack/1.0",
    }

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
    response.raise_for_status()

    data = response.json()
    results = []
    rates = data.get("rates", {})
    actuals = data.get("actuals", {})
    all_dates = sorted(set(list(rates.keys()) + list(actuals.keys())))
    for date in all_dates:
        results.append({
            "date": date,
            "ori_code": origin_code,
            "offense_code": offense_code,
            "arrest_rate": rates.get(date),
            "arrest_total": actuals.get(date),
        })
    return pd.DataFrame(results)


def get_cde_arrest_counts_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None,
) -> pd.DataFrame:
    """
    Fetches FBI arrest counts by agency ORI code and returns a DataFrame.
    Each row represents one date/offense combination with rate, total, and population.
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
    response.raise_for_status()

    data = response.json()
    results = []
    rates = data.get("rates", {})
    actuals = data.get("actuals", {})
    populations = data.get("populations", {}).get("population", {})
    all_dates = sorted(set(list(rates.keys()) + list(actuals.keys())))
    for date in all_dates:
        results.append({
            "date": date,
            "ori_code": origin_code,
            "offense_code": offense_code,
            "arrest_rate": rates.get(date),
            "arrest_total": actuals.get(date),
            "population": populations.get(date),
        })
    return pd.DataFrame(results)

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
                    # else:
                    #     response.raise_for_status()
            else:
                url = f"{FBI_API_BASE_URL}/crime/fbi/cde/nibrs/state/{state_abbr}/{nibrs_code}?from={start_date}&to={end_date}&type=totals&API_KEY={FBI_API_KEY}"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    # print(f"Data fetched successfully for {state_abbr}")
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
                # else:
                #     response.raise_for_status()

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
                # else:
                #     response.raise_for_status()
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
                    **{f"offender.ethnicity.{k.lower().replace(' ', '_').replace(',', '-')}" : v for k, v in data["offender"]["ethnicity"].items()},
                })
            # else:
            #     response.raise_for_status()
    return pd.DataFrame(results)