import re
import requests
import json
import os
import pandas as pd
import time

from . import GOV_API_BASE_URL, GOV_API_KEY
from .models import (
    us_territory_mapping,
    get_abbr_from_state,
    get_state_from_abbr,
    fbi_offense_mapping,
    get_offense_from_code,
    get_code_from_offense,
    nibrs_offense_codes_v2,
    nibrs_offense_mapping_v1,
    nibrs_offense_mapping_v2,
)

headers: dict = {"X-API-KEY": GOV_API_KEY, "User-Agent": "StatPack/1.0", "Accept": "application/json"}


def _normalize_wide_key(value: str, debug: bool = False) -> str:
    normalized = str(value).strip().lower()
    normalized = re.sub(r"[\s/\-]+", "_", normalized)
    normalized = normalized.replace("%", "percent")
    normalized = re.sub(r"[^a-z0-9_\.]+", "", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if debug:
        print(f"Normalized '{value}' to '{normalized}'")
    return normalized


def _normalize_dataframe_columns_wide(df: pd.DataFrame, debug: bool = False) -> pd.DataFrame:
    rename_map = {}
    if debug:
        print(f"Normalizing dataframe columns: {len(df.columns)} columns to normalize.")

    for column in df.columns:
        parts = str(column).split(".")
        rename_map[column] = ".".join(_normalize_wide_key(part, debug=debug) for part in parts)
    return df.rename(columns=rename_map)


def _records_to_wide_dataframe(
    records: list[dict],
    ordered_columns: list[str] = None,
    sort_by: list[str] = None,
    index_cols: list[str] = None,
    normalize_columns: bool = False,
    debug: bool = False,
) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    result = pd.json_normalize(records, sep=".")
    result = result.convert_dtypes()

    if normalize_columns:
        result = _normalize_dataframe_columns_wide(result, debug=debug)

    if ordered_columns:
        present_ordered = [column for column in ordered_columns if column in result.columns]
        dynamic_columns = sorted(column for column in result.columns if column not in present_ordered)
        result = result[present_ordered + dynamic_columns]

    if index_cols:
        present_index_cols = [column for column in index_cols if column in result.columns]
        if present_index_cols:
            return result.set_index(present_index_cols).sort_index()

    if sort_by:
        present_sort_cols = [column for column in sort_by if column in result.columns]
        if present_sort_cols:
            result = result.sort_values(by=present_sort_cols, ignore_index=True)

    return result


def _finalize_records(
    records: list[dict],
    raw: bool = False,
    ordered_columns: list[str] = None,
    sort_by: list[str] = None,
    index_cols: list[str] = None,
    normalize_columns: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    if raw:
        return records
    return _records_to_wide_dataframe(
        records=records,
        ordered_columns=ordered_columns,
        sort_by=sort_by,
        index_cols=index_cols,
        normalize_columns=normalize_columns,
        debug=debug,
    )


def get_expanded_homicide_counts_by_state(
    start_date: str = None, end_date: str = None, state_abbr: str = None, raw: bool = False, debug: bool = False
) -> pd.DataFrame | list[dict]:
    """Fetch expanded homicide SHR () totals and return a super-wide DataFrame.

    Args:
        start_date (str, optional): Start date for the data. Defaults to None.
        end_date (str, optional): End date for the data. Defaults to None.
        state_abbr (str, optional): Two-letter state abbreviation. If None, all states are queried.
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.

    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """
    records = []
    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    states_to_query = list(us_territory_mapping.keys()) if state_abbr is None else [state_abbr]

    if debug:
        print(f"Fetching SHR totals for states: {len(states_to_query)} from {start_date} to {end_date}")
    for abbr in states_to_query:
        url = f"{GOV_API_BASE_URL}/crime/fbi/cde/shr/state/{abbr}?type=totals&from={start_date}&to={end_date}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            state_name = get_state_from_abbr(abbr)
            requested = {"state_abbr": abbr, "state_name": state_name, "start_date": start_date, "end_date": end_date}
            records.append({"requested": requested, **requested, **data})
            if debug:
                print(f"Fetched SHR totals for state: {abbr}")
        elif state_abbr is not None:
            response.raise_for_status()

        if state_abbr is None:
            time.sleep(1)

    return _finalize_records(
        records=records,
        raw=raw,
        ordered_columns=["requested.state_abbr", "requested.state_name", "requested.start_date", "requested.end_date"],
        sort_by=["requested.state_abbr"],
        normalize_columns=True,
        debug=debug,
    )


def _flatten_get_summarized_by_state_payload_wide(
    # raw: bool,
    payload: dict,
    requested_state_abbr: str,
    requested_offense_code: str,
    debug: bool = False,
) -> pd.DataFrame:
    """Flatten one summarized API payload into a super-wide monthly DataFrame.

    Output grain: one row per date for the requested state/offense.
    """
    monthly_maps: list[tuple[str, dict]] = []

    offense_rates = payload.get("offenses", {}).get("rates", {})
    for series_name, series_values in offense_rates.items():
        monthly_maps.append((f"offenses.rates.{_normalize_wide_key(series_name)}", series_values))

    offense_actuals = payload.get("offenses", {}).get("actuals", {})
    for series_name, series_values in offense_actuals.items():
        monthly_maps.append((f"offenses.actuals.{_normalize_wide_key(series_name)}", series_values))

    coverage = payload.get("tooltips", {}).get("Percent of Population Coverage", {})
    for series_name, series_values in coverage.items():
        monthly_maps.append((f"tooltips.coverage_percent.{_normalize_wide_key(series_name)}", series_values))

    populations = payload.get("populations", {}).get("population", {})
    for series_name, series_values in populations.items():
        monthly_maps.append((f"populations.population.{_normalize_wide_key(series_name)}", series_values))

    participated_populations = payload.get("populations", {}).get("participated_population", {})
    for series_name, series_values in participated_populations.items():
        monthly_maps.append((f"populations.participated_population.{_normalize_wide_key(series_name)}", series_values))

    all_dates: set[str] = set()
    for _, series_values in monthly_maps:
        if isinstance(series_values, dict):
            all_dates.update(series_values.keys())

    if debug:
        print(f"Extracted {len(all_dates)} unique dates from offense rates, actuals, coverage, and population series.")

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

    if debug:
        print(f"Created DataFrame with {len(rows)} rows.")

    return pd.DataFrame(rows)


def get_summarized_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: str = None,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame:
    """Fetch FBI CDE summarized offense data by state and return a wide DataFrame.

    Each row represents one date for a given state/offense combination.
    """
    frames: list[pd.DataFrame] = []
    records: list = []
    supported_offense_codes = ["V", "ASS", "LAR", "MVT", "HOM", "RPE", "ROB", "ARS", "P"]

    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    states_to_query = list(us_territory_mapping.keys()) if state_abbr is None else [state_abbr]
    offenses_to_query = supported_offense_codes if offense_code is None else [str(offense_code)]

    for abbr in states_to_query:
        for code in offenses_to_query:
            url = (
                f"{GOV_API_BASE_URL}/crime/fbi/cde/summarized/state/{abbr}/{code}"
                f"?from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
            )
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                records.append(data)
                frames.append(
                    _flatten_get_summarized_by_state_payload_wide(
                        # raw=raw,
                        payload=data,
                        requested_state_abbr=abbr,
                        requested_offense_code=code,
                    )
                )
            else:
                if debug:
                    print(
                        f"Request failed for state {abbr} and offense {code}. "
                        f"Status code: {response.status_code} ({response.reason})"
                        f"Response header: {response.headers}"
                    )

    if raw:
        return records

    if not frames:
        return pd.DataFrame()

    if debug:
        print(f"returned {len(frames)} frames.")

    return pd.concat(frames, ignore_index=True).sort_values(
        by=["date", "requested.state_abbr", "requested.offense_code"], ignore_index=True
    )


def get_reporting_agencies(raw: bool = False, debug: bool = False) -> pd.DataFrame | list[dict]:
    """
    Fetches FBI agency crosswalk data.

    Args:
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.
    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """
    headers = {"X-API-KEY": GOV_API_KEY, "User-Agent": "StatPack/1.0"}
    results = []
    for state_abbr in us_territory_mapping.keys():
        url = f"{GOV_API_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/{state_abbr}?API_KEY={GOV_API_KEY}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for ori, agency in data.items():
                if isinstance(agency, list):
                    for item in agency:
                        if not isinstance(item, dict):
                            continue
                        results.append(item)

    if debug:
        print(f"Fetched {len(results)} total reporting agencies for {len(us_territory_mapping.keys())} states.")

    return _finalize_records(records=results, raw=raw)


def get_arrest_counts_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
    table: str = "arrestee race",
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """
    Fetches FBI arrest rates by state and breakdown table.

    Args:
        start_date (str, optional): Start date (MM-YYYY). Defaults to "01-2020".
        end_date (str, optional): End date (MM-YYYY). Defaults to "12-2020".
        state_abbr (str, optional): Two-letter state abbreviation. Defaults to "NY".
        offense_code (int, optional): FBI offense code. Defaults to "all".
        table (str, optional): Breakdown table name to extract. Defaults to "arrestee race".
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """

    results = []

    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    if state_abbr is None:
        for state_abbr, state in us_territory_mapping.items():
            url = f"{GOV_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print(f"Data fetched successfully for {state_abbr}")
                data = response.json()
                available_keys = list(k.lower() for k in list(data.keys()) if k not in ["cde_properties"])
                if table not in available_keys:
                    raise ValueError(f"Table '{table}' not found in response. Available tables: {available_keys}")

                for table_name, table_data in data.items():
                    print(f"Checking table: {table_name}")
                    if table_name.lower() == table.lower():
                        for entry, value in table_data.items():
                            results.append({table_name: entry, "Value": value})

    if debug:
        print(f"Fetched arrest counts by state with {len(results)} total records for table '{table}'.")
    return _finalize_records(records=results, raw=raw)


def get_arrest_totals_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
    table: str = "arrestee race",
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """
    Fetches FBI arrest totals by state and breakdown table.

    Args:
        start_date (str, optional): Start date (MM-YYYY). Defaults to "01-2020".
        end_date (str, optional): End date (MM-YYYY). Defaults to "12-2020".
        state_abbr (str, optional): Two-letter state abbreviation. Defaults to "NY".
        offense_code (int, optional): FBI offense code. Defaults to "all".
        table (str, optional): Breakdown table name to extract. Defaults to "arrestee race".
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.

    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """
    results = []
    if offense_code is None:
        offense_code = "all"
    if state_abbr is None:
        state_abbr = "NY"
    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    url = f"{GOV_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=totals&from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Data fetched successfully for {state_abbr}")
        data = response.json()
        results.append(data)
    #     available_keys = list(
    #         k.lower() for k in list(data.keys()) if k not in ["cde_properties"]
    #     )
    #     if table not in available_keys:
    #         raise ValueError(
    #             f"Table '{table}' not found in response. Available tables: {available_keys}"
    #         )

    #     for table_name, table_data in data.items():
    #         print(f"Checking table: {table_name}")
    #         if table_name.lower() == table.lower():
    #             for entry, value in table_data.items():
    #                 results.append({table_name: entry, "Value": value})

    # return _finalize_records(records=results, raw=raw)
    if debug:
        print(f"Returned {len(results)} records.")

    return results


def get_arrest_counts_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    offense_code: int = None,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """
    Fetches FBI arrest counts by state with demographic breakdown.

    Args:
        start_date (str, optional): Start date (MM-YYYY). Defaults to "01-2020".
        end_date (str, optional): End date (MM-YYYY). Defaults to "12-2020".
        state_abbr (str, optional): Two-letter state abbreviation. If None, all states are queried.
        offense_code (int, optional): FBI offense code. Defaults to "all".
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.
    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """
    results = []
    if offense_code is None:
        offense_code = "all"

    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    if state_abbr is None:
        for state_abbr, state in us_territory_mapping.items():
            url = f"{GOV_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
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
                            "Offense": (get_offense_from_code(int(offense_code)) if offense_code != "all" else "all"),
                            "Arrest Rate": state_rates.get(d, None),
                            "Arrest Total": state_totals.get(d, None),
                            "Population": (state_population.get(d, None) if state_population else None),
                        }
                    )
    else:
        url = f"{GOV_API_BASE_URL}/crime/fbi/cde/arrest/state/{state_abbr}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
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
                        "Offense": (get_offense_from_code(int(offense_code)) if offense_code != "all" else "all"),
                        "Arrest Rate": state_rates.get(d, None),
                        "Arrest Total": state_totals.get(d, None),
                        "Population": (state_population.get(d, None) if state_population else None),
                    }
                )

    if debug:
        print(f"Returned {len(results)} records.")

    return _finalize_records(records=results, raw=raw, index_cols=["Date", "State"])


def get_arrest_totals_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """
    Fetches FBI arrest totals by agency ORI code.

    Args:
        start_date (str, optional): Start date (MM-YYYY). Defaults to "01-2020".
        end_date (str, optional): End date (MM-YYYY). Defaults to "12-2020".
        origin_code (str, optional): Agency ORI code. Defaults to "AL0430200".
        offense_code (int, optional): FBI offense code. Defaults to "all".
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.


    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """
    if offense_code is None:
        offense_code = "all"
    if origin_code is None:
        origin_code = "AL0430200"
    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    url = f"{GOV_API_BASE_URL}/crime/fbi/cde/arrest/agency/{origin_code}/{offense_code}?type=totals&from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
    response = requests.get(url, headers=headers)
    # response.raise_for_status()

    data = response.json()
    results = []
    rates = data.get("rates", {})
    actuals = data.get("actuals", {})
    all_dates = sorted(set(list(rates.keys()) + list(actuals.keys())))
    for date in all_dates:
        results.append(
            {
                "date": date,
                "ori_code": origin_code,
                "offense_code": offense_code,
                "arrest_rate": rates.get(date),
                "arrest_total": actuals.get(date),
            }
        )

    if debug:
        print(f"Returned {len(results)} records.")

    return _finalize_records(records=results, raw=raw, sort_by=["date"])


def get_arrest_counts_by_origin(
    start_date: str = None,
    end_date: str = None,
    origin_code: str = None,
    offense_code: int = None,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """
    Fetches FBI arrest counts by agency ORI code.

    Args:
        start_date (str, optional): Start date (MM-YYYY). Defaults to "01-2020".
        end_date (str, optional): End date (MM-YYYY). Defaults to "12-2020".
        origin_code (str, optional): Agency ORI code. Defaults to "AL0430200".
        offense_code (int, optional): FBI offense code. Defaults to "all".
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.

    Returns:
        pd.DataFrame | list[dict]: Flattened DataFrame (default) or raw records.
    """
    if offense_code is None:
        offense_code = "all"
    if origin_code is None:
        origin_code = "AL0430200"
    if start_date is None:
        start_date = "01-2020"
    if end_date is None:
        end_date = "12-2020"

    url = f"{GOV_API_BASE_URL}/crime/fbi/cde/arrest/agency/{origin_code}/{offense_code}?type=counts&from={start_date}&to={end_date}&API_KEY={GOV_API_KEY}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()
    results = []
    rates = data.get("rates", {})
    actuals = data.get("actuals", {})
    populations = data.get("populations", {}).get("population", {})
    all_dates = sorted(set(list(rates.keys()) + list(actuals.keys())))
    for date in all_dates:
        results.append(
            {
                "date": date,
                "ori_code": origin_code,
                "offense_code": offense_code,
                "arrest_rate": rates.get(date),
                "arrest_total": actuals.get(date),
                "population": populations.get(date),
            }
        )

    if debug:
        print(f"Returned {len(results)} records.")
    return _finalize_records(records=results, raw=raw, sort_by=["date"])


def get_nibrs_totals_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    nibrs_code: int = None,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """gather a state wide NIBRS

    Args:
        start_date (str, optional): _description_. Defaults to None.
        end_date (str, optional): _description_. Defaults to None.
        state_abbr (str, optional): _description_. Defaults to None.
        nibrs_code (int, optional): _description_. Defaults to None.
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.
    """
    records = []
    if start_date is None:
        start_date = "01-2020"

    if end_date is None:
        end_date = "12-2020"

    states_to_query = list(us_territory_mapping.keys()) if state_abbr is None else [state_abbr]
    nibrs_codes_to_query = [info.code for info in nibrs_offense_codes_v2] if nibrs_code is None else [nibrs_code]

    for abbr in states_to_query:
        for code in nibrs_codes_to_query:
            print(f"Fetching NIBRS totals for state={abbr}, code={code}...")
            # code_key = int(code) if str(code).isdigit() else code
            code_key = str(code)
            crime_name = nibrs_offense_mapping_v2.get(code_key, {}).get("name")
            url = f"{GOV_API_BASE_URL}/crime/fbi/cde/nibrs/state/{abbr}/{code}?from={start_date}&to={end_date}&type=totals&API_KEY={GOV_API_KEY}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                records.append(
                    {
                        "state_abbr": abbr,
                        "state_name": get_state_from_abbr(abbr),
                        "nibrs_code": code_key,
                        "crime": crime_name,
                        "start_date": start_date,
                        "end_date": end_date,
                        **data,
                    }
                )

            if state_abbr is None:
                time.sleep(1)

    if debug:
        print(f"Returned {len(records)} records.")

    return _finalize_records(
        records=records,
        raw=raw,
        ordered_columns=["state_abbr", "state_name", "nibrs_code", "crime", "start_date", "end_date"],
        sort_by=["state_abbr", "nibrs_code"],
        normalize_columns=True,
    )


def get_nibrs_counts_by_state(
    start_date: str = None,
    end_date: str = None,
    state_abbr: str = None,
    nibrs_code: int = None,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """gather a state wide NIBRS

    Args:
        start_date (str, optional): _description_. Defaults to None.
        end_date (str, optional): _description_. Defaults to None.
        state_abbr (str, optional): _description_. Defaults to None.
        nibrs_code (int, optional): _description_. Defaults to None.
        raw (bool, optional): When True, return raw list[dict] records; otherwise return DataFrame.
        debug (bool, optional): When True, print debug information. Defaults to False.
    """
    None
