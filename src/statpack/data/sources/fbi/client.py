import re
from typing import Any

import requests
from . import GOV_API_BASE_URL, GOV_API_KEY
from ..models import Request, FailedRequest
from .models import Data, USTerritory

import pandas as pd

import time


class Client:
    routes: dict[str, dict[str, str]] = {}

    def __init__(self, api_base_url: str | None = GOV_API_BASE_URL, api_key: str | None = GOV_API_KEY):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.headers = {"X-Api-Key": self.api_key, "User-Agent": "StatPack/1.0", "Accept": "application/json"}
        self.last: Request | None = None
        self.requests: int = 0
        self.failed_requests: list[FailedRequest] = []
        self.limited = False
        self.limit_remaining = None
        self.limit_reset = None
        self.data = Data()

    def _clean_column_prefix(self, prefix: str) -> str:
        prefix = prefix.lower()
        prefix = prefix.replace(" ", "_")
        return prefix

    def _clean_column_name(self, name: str) -> str:
        name = name.lower()
        # name = name.replace(" ", "")
        name = name.replace(" ", "_")
        name = re.sub(r"[\)\()/-]", "_", name)

        # replace multiple underscores with a single underscore
        name = re.sub(r"_+", "_", name)
        # remove trailing underscores
        name = re.sub(r"_+$", "", name)
        return name

    def get(
        self,
        url_path: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        debug: bool = False,
        **kwargs,
    ) -> Any:
        if url_path is None:
            raise ValueError("'url_path' must be provided")

        if success_codes is None:
            success_codes = [200]

        # handle query parameters in url_path
        separator = "&" if "?" in url_path else "?"

        # support url_path with or without leading slash
        leading_slash = "" if url_path.startswith("/") else "/"

        url = f"{self.api_base_url}{leading_slash}{url_path}{separator}api_key={self.api_key}"

        if debug:
            print(f"making request to URL: {url}")

        response = requests.get(url, headers=self.headers)
        self.requests += 1
        if debug:
            print(f"received response with status code: {response.status_code} ({response.reason})")

        # return the response data as a native Python object (dict, list, etc.)
        if response.status_code in success_codes:
            self.last = Request(
                url=url, params=None, request_headers=self.headers, response_headers=dict(response.headers)
            )
            return response.json()
        else:
            # log the failed request details for debugging and analysis and rate limit handling
            self.failed_requests.append(
                FailedRequest(url=url, status_code=response.status_code, reason=response.reason, timestamp=time.time())
            )

            # invalid protocol (http vs https)
            if response.status_code in (400,):
                if debug:
                    print(f"Please utilize HTTPS protocol for URL {url} to ensure secure communication with the API.")

            # handle not found
            if response.status_code in (404,):
                if debug:
                    print(f"Resource not found for URL {url}. Check the endpoint and parameters.")

            # handle unauthorized access
            if response.status_code in (403,):
                if debug:
                    print(f"Unauthorized access for URL {url}. Check your API key and permissions.")
            # handle rate limit handling
            if response.status_code in (429,):
                limit = response.headers.get("X-RateLimit-Limit")
                reset = response.headers.get("X-RateLimit-Remaining")
                retry_after = response.headers.get("Retry-After")
                self.limited = True
                self.limit_remaining = reset if reset is not None else None
                self.limit_reset = retry_after if retry_after is not None else None
                if debug:
                    print(f"rate limit: {limit}, remaining: {reset}, retry-after: {retry_after}")
            # the API Umbrella API often returns a 503 (Service Unavailable) when the rate limit is exceeded, but it also includes rate limit information in the response headers.
            # We check for this and handle it accordingly.
            if response.status_code in (503,):
                # if ["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"] in response.headers.keys():
                #     limit = response.headers.get("X-RateLimit-Limit")
                #     reset = response.headers.get("X-RateLimit-Remaining")
                #     retry_after = response.headers.get("Retry-After")
                #     self.limited = True
                #     self.limit_remaining = reset if reset is not None else None
                #     self.limit_reset = retry_after if retry_after is not None else None
                #     if debug:
                #         print(f"rate limit exceeded. Limit: {limit}, Remaining: {reset}, Retry-After: {retry_after}")
                # else:
                # the 503 may be due to other issues, so we can log that as well
                if debug:
                    print(f"Received 503 Service Unavailable for URL {url}, but rate limit headers are missing.")

            if debug:
                print(f"Request failed for URL {url} with status code {response.status_code} ({response.reason}).")
            return default_return

    def get_agencies_by_territory(
        self,
        territory: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ) -> list[dict] | pd.DataFrame:
        """Get agencies by territory.

        Args:
            territory (str, optional): The territory abbreviation or name. Defaults to None, which means all territories.
            default_return (Any, optional): The value to return if the request fails. Defaults to None.
            success_codes (list, optional): A list of HTTP status codes considered successful. Defaults to None.
            raw (bool, optional): If True, returns the raw response from the API. Defaults to False.
            debug (bool, optional): If True, enables debug logging. Defaults to False.

        """
        url_path = lambda terr: f"crime/fbi/cde/agency/byStateAbbr/{terr}"
        results = []
        if territory:
            territory_obj = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            if territory_obj is None:
                return pd.DataFrame() if not raw else []
            data = self.get(
                url_path=url_path(territory_obj.abbreviation),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )
            (
                print(
                    f"found {len(data.keys())} agencies for territory {territory_obj.name} ({territory_obj.abbreviation})"
                )
                if debug
                else None
            )
            locations = list(data.keys())

            for location in locations:
                origins = data[location]
                results.extend(origins)

            if raw:
                return results
            return pd.DataFrame(results)

        for terr in self.data.us_territories:
            data = self.get(
                url_path=url_path(terr.abbreviation),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )
            if data is not None:
                (
                    print(f"found {len(data.keys())} agencies for territory {terr.name} ({terr.abbreviation})")
                    if debug
                    else None
                )
                for location in data.keys():
                    results.extend(data[location])

        return pd.DataFrame(results) if not raw else results

    def get_arrest_counts_by_state(
        self,
        territory: str | None = None,
        offense_code: str = "all",
        start_date: str | None = None,
        end_date: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ):
        url_path = (
            lambda terr, offense_code, start_date, end_date: f"crime/fbi/cde/arrest/state/{terr}/{offense_code}?type=counts&from={start_date}&to={end_date}"
        )
        results = []
        if territory:
            territory_obj = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            if territory_obj is None:
                return pd.DataFrame() if not raw else []
            data = self.get(
                url_path=url_path(territory_obj.abbreviation, offense_code, start_date, end_date),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )

            # rates {'New York Arrests': {'01-2025': 190.36, '02-2025': 172, '03-2025': 196.62, '04-2025': 197.75, '05-2025': 201.22, '06-2025': 191.59}, 'United States Arrests': {'01-2025': 175.61, '02-2025': 167.75, '03-2025': 195.27, '04-2025': 189.99, '05-2025': 198.19, '06-2025': 188.09}}
            # actuals {'New York Arrests': {'01-2025': 27942, '02-2025': 25288, '03-2025': 28925, '04-2025': 29110, '05-2025': 29602, '06-2025': 28217}}
            # populations.population {'New York': {'01-2025': 20002427, '02-2025': 20002427, '03-2025': 20002427, '04-2025': 20002427, '05-2025': 20002427, '06-2025': 20002427}, 'United States': {'01-2025': 345206793, '02-2025': 345206793, '03-2025': 345206793, '04-2025': 345206793, '05-2025': 345206793, '06-2025': 345206793}}
            # populations.participated_population {'New York': {'01-2025': 14678214, '02-2025': 14702062, '03-2025': 14711092, '04-2025': 14720611, '05-2025': 14711358, '06-2025': 14728066}, 'United States': {'01-2025': 314995268, '02-2025': 313004395, '03-2025': 311656141, '04-2025': 310452899, '05-2025': 310254293, '06-2025': 309658518}}
            territory_rates = data.get("rates", {}).get(territory_obj.name + " Arrests", {})
            us_rates = data.get("rates", {}).get("United States Arrests", {})

            territory_totals = data.get("actuals", {}).get(territory_obj.name + " Arrests", {})

            territory_population = data.get("populations", {}).get("population", {}).get(territory_obj.name, {})
            us_population = data.get("populations", {}).get("population", {}).get("United States", {})

            territory_participated_population = (
                data.get("populations", {}).get("participated_population", {}).get(territory_obj.name, {})
            )
            us_participated_population = (
                data.get("populations", {}).get("participated_population", {}).get("United States", {})
            )

            dates = (
                set(territory_rates.keys())
                | set(us_rates.keys())
                | set(territory_totals.keys())
                | set(territory_population.keys())
                | set(us_population.keys())
                | set(territory_participated_population.keys())
                | set(us_participated_population.keys())
            )
            # print(f"dates={dates}") if debug else None
            for date in sorted(list(dates)):
                results.append(
                    {
                        "date": date,
                        "territory": territory_obj.name,
                        "us": "United States",
                        "territory_rate": territory_rates.get(date),
                        "us_rate": us_rates.get(date),
                        "territory_total": territory_totals.get(date),
                        "territory_population": territory_population.get(date),
                        "us_population": us_population.get(date),
                        "territory_participated_population": territory_participated_population.get(date),
                        "us_participated_population": us_participated_population.get(date),
                    }
                )
        return pd.DataFrame(results) if not raw else results

    def get_arrest_totals_by_state(
        self,
        territory: str | None = None,
        offense_code: str = "all",
        start_date: str | None = None,
        end_date: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ):
        url_path = (
            lambda terr, offense_code, start_date, end_date: f"crime/fbi/cde/arrest/state/{terr}/{offense_code}?type=totals&from={start_date}&to={end_date}"
        )
        results = []
        if territory:
            territory_obj = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            if territory_obj is None:
                return pd.DataFrame() if not raw else []
            data = self.get(
                url_path=url_path(territory_obj.abbreviation, offense_code, start_date, end_date),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )

            if data:
                data_prefixes = [k for k in data.keys() if k not in ("cde_properties")]
                row = {
                    "territory": territory_obj.name,
                    "us": "United States",
                    "start_date": start_date,
                    "end_date": end_date,
                }
                for data_prefix in data_prefixes:
                    for data_title, total in data[data_prefix].items():
                        column_prefix = self._clean_column_prefix(data_prefix)
                        column_title = self._clean_column_name(data_title)
                        column_name = f"{column_prefix}.{column_title}"
                        row[column_name] = total
                results.append(row)

        return pd.DataFrame(results) if not raw else results

    def get_arrest_race_breakdown_by_state(
        self,
        territory: str | None = None,
        offense_code: str = "all",
        start_date: str | None = None,
        end_date: str | None = None,
        table: str = "Arrestee Race",
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ):
        """Fetch the arrestee race (or other demographic) breakdown for a single state.

        Uses the arrest ``type=totals`` endpoint, which returns aggregate demographic
        breakdown tables (e.g. ``"Arrestee Race"``) over the requested date range. The
        ``type=counts`` endpoint, by contrast, returns a monthly rate time-series with no
        demographic dimension.

        Returns records shaped ``{"territory", "race", "count"}`` (default) or a DataFrame.
        """
        url_path = (
            lambda terr, offense_code, start_date, end_date: f"crime/fbi/cde/arrest/state/{terr}/{offense_code}?type=totals&from={start_date}&to={end_date}"
        )
        results = []
        if territory:
            territory_obj = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            if territory_obj is None:
                return pd.DataFrame() if not raw else []
            data = self.get(
                url_path=url_path(territory_obj.abbreviation, offense_code, start_date, end_date),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )
            if data:
                available = {k.lower(): k for k in data.keys() if k != "cde_properties"}
                if table.lower() not in available:
                    raise ValueError(
                        f"Table {table!r} not found in response. Available tables: {sorted(available.values())}"
                    )
                breakdown = data[available[table.lower()]]
                for label, count in breakdown.items():
                    results.append({"territory": territory_obj.name, "race": label, "count": count})

        return pd.DataFrame(results) if not raw else results

    def get_expanded_homicide_counts_by_state(
        self,
        territory: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ):
        url_path = (
            lambda terr, start_date, end_date: f"crime/fbi/cde/shr/state/{terr}?type=counts&from={start_date}&to={end_date}"
        )
        results = []

        if territory:
            territory_obj = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            if territory_obj is None:
                return pd.DataFrame() if not raw else []
            data = self.get(
                url_path=url_path(territory_obj.abbreviation, start_date, end_date),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )

            # these are labeled actuals, but they are per capita rates
            per_capita_rates = data.get("actuals", {}).get(territory_obj.name + " Offenses", {})

            dates = set(per_capita_rates.keys())
            for date in sorted(list(dates)):
                results.append(
                    {
                        "date": date,
                        "territory": territory_obj.name,
                        "us": "United States",
                        "per_capita_rate": per_capita_rates.get(date),
                    }
                )

        return pd.DataFrame(results) if not raw else results

    def get_expanded_homicide_totals_by_state(
        self,
        territory: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ):
        url_path = (
            lambda terr, start_date, end_date: f"crime/fbi/cde/shr/state/{terr}?type=totals&from={start_date}&to={end_date}"
        )
        results = []

        if territory:
            territory_obj = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            if territory_obj is None:
                return pd.DataFrame() if not raw else []
            data = self.get(
                url_path=url_path(territory_obj.abbreviation, start_date, end_date),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )
            data_prefixes = [k for k in data.keys() if k not in ("cde_properties")]
            row = {
                "territory": territory_obj.name,
                "us": "United States",
                "start_date": start_date,
                "end_date": end_date,
            }
            # dict_keys(['victim', 'offense', 'offender',])
            for data_prefix in data_prefixes:
                for data_category, totals in data[data_prefix].items():
                    # victim - dict_keys(['age', 'sex', 'race', 'ethnicity'])
                    column_prefix = self._clean_column_prefix(data_prefix)
                    column_category = self._clean_column_name(data_category)
                    column_name = f"{column_prefix}.{column_category}"
                    # dict_keys(['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80-89', 'Unknown', '90-Older'])
                    for key, value in data[data_prefix][data_category].items():
                        column_target = self._clean_column_name(key)
                        row[f"{column_name}.{column_target}"] = value
            results.append(row)
        return pd.DataFrame(results) if not raw else results

    def get_nibrs_counts_by_state(
        self,
        territory: str | None = None,
        offense_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        default_return: Any = None,
        success_codes: list | None = None,
        raw: bool = False,
        debug: bool = False,
    ):

        if territory is None:
            return pd.DataFrame() if not raw else []
        territory_obj: USTerritory | None = self.data.get_territory_by_abbr(
            territory
        ) or self.data.get_territory_by_name(territory)
        if territory_obj is None:
            return pd.DataFrame() if not raw else []
        (
            print(f"fetching NIBRS counts for territory {territory_obj.name} ({territory_obj.abbreviation})")
            if debug
            else None
        )
        url_path = (
            lambda terr, offense_code, start_date, end_date: f"crime/fbi/cde/nibrs/state/{terr}/{offense_code}?type=counts&from={start_date}&to={end_date}"
        )

        results = []
        data = self.get(
            url_path=url_path(territory_obj.abbreviation, offense_code, start_date, end_date),
            default_return=default_return,
            success_codes=success_codes,
            debug=debug,
        )

        if data is not None:

            offenses_data = data.get("offenses") or {}
            rates_data = offenses_data.get("rates") or {}
            actuals_data = offenses_data.get("actuals") or {}
            populations_data = data.get("populations") or {}
            population_data = populations_data.get("population") or {}
            participated_population_data = populations_data.get("participated_population") or {}

            territory_rates = rates_data.get(territory_obj.name + " Offenses", {})
            territory_clearance_rates = rates_data.get(territory_obj.name + " Clearances", {})

            us_rates = rates_data.get("United States Offenses", {})
            us_clearance_rates = rates_data.get("United States Clearances", {})

            territory_totals = actuals_data.get(territory_obj.name + " Offenses", {})
            territory_clearance_totals = actuals_data.get(territory_obj.name + " Clearances", {})

            territory_population = population_data.get(territory_obj.name, {})
            us_population = population_data.get("United States", {})

            territory_participated_population = participated_population_data.get(territory_obj.name, {})
            us_participated_population = participated_population_data.get("United States", {})

            dates = (
                set(territory_rates.keys())
                | set(territory_clearance_rates.keys())
                | set(us_rates.keys())
                | set(us_clearance_rates.keys())
                | set(territory_totals.keys())
                | set(territory_clearance_totals.keys())
                | set(territory_population.keys())
                | set(us_population.keys())
                | set(territory_participated_population.keys())
                | set(us_participated_population.keys())
            )

            for date in sorted(list(dates)):
                results.append(
                    {
                        "date": date,
                        "territory": territory_obj.name,
                        "us": "United States",
                        "territory_rate": territory_rates.get(date),
                        "territory_clearance_rate": territory_clearance_rates.get(date),
                        "us_rate": us_rates.get(date),
                        "us_clearance_rate": us_clearance_rates.get(date),
                        "territory_total": territory_totals.get(date),
                        "territory_clearance_total": territory_clearance_totals.get(date),
                        "territory_population": territory_population.get(date),
                        "us_population": us_population.get(date),
                        "territory_participated_population": territory_participated_population.get(date),
                        "us_participated_population": us_participated_population.get(date),
                    }
                )

        return pd.DataFrame(results) if not raw else results
