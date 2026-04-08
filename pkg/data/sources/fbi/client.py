import re

import requests
from . import GOV_API_BASE_URL, GOV_API_KEY
from .data import FBIData
from pydantic import BaseModel, Field
from urllib.parse import urlparse

import time

##
# state (state abbreviation)
# from (start date MM-YYYY)
# to (end date MM-YYYY)
# offense (offense type)
# type (totals, counts)


class Request(BaseModel):
    url: str
    params: dict | None = None
    request_headers: dict | None = None
    response_headers: dict | None = None


class FailedRequest(BaseModel):
    url: str
    status_code: int
    reason: str
    timestamp: float = Field(default_factory=time.time)


class Client:
    routes: dict[str, dict[str, str]] = {}

    def __init__(self, api_base_url: str = GOV_API_BASE_URL, api_key: str = GOV_API_KEY):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": self.api_key, "User-Agent": "StatPack/1.0", "Accept": "application/json"}
        self.last: Request | None = None
        self.requests: int = 0
        self.failed_requests: list[FailedRequest] = []
        self.limited = False
        self.limit_remaining = None
        self.limit_reset = None
        self.data = FBIData()

    def get(
        self, url_path: str = None, default_return=None, success_codes: list = None, debug: bool = False
    ) -> dict | list:
        if url_path is None:
            raise ValueError("'url_path' must be provided")

        if success_codes is None:
            success_codes = [200]

        # handle query parameters in url_path
        separator = "&" if "?" in url_path else "?"

        # support url_path with or without leading slash
        leading_slash = "" if url_path.startswith("/") else "/"

        # construct full URL
        parsed_url = urlparse(f"{self.api_base_url}{leading_slash}{url_path}{separator}")
        # extract query parameters from url_path as a dict
        # potentially used for preemptive error handling, logging, or other purposes
        # query = dict(
        #     [part.split("=", 1) for part in parsed_url.query.split("&") if "=" in part]
        # )

        url = f"{self.api_base_url}{leading_slash}{url_path}{separator}API_KEY={self.api_key}"

        if debug:
            print(f"making request to URL: {url}")

        response = requests.get(url, headers=self.headers)
        self.requests += 1
        if debug:
            print(f"received response with status code: {response.status_code} ({response.reason})")

        # return the response data as a native Python object (dict, list, etc.)
        if response.status_code in success_codes:
            self.last = Request(url=url, params=None, request_headers=self.headers, response_headers=response.headers)
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
                if ["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"] in response.headers.keys():
                    limit = response.headers.get("X-RateLimit-Limit")
                    reset = response.headers.get("X-RateLimit-Remaining")
                    retry_after = response.headers.get("Retry-After")
                    self.limited = True
                    self.limit_remaining = reset if reset is not None else None
                    self.limit_reset = retry_after if retry_after is not None else None
                    if debug:
                        print(f"rate limit exceeded. Limit: {limit}, Remaining: {reset}, Retry-After: {retry_after}")
                else:
                    # the 503 may be due to other issues, so we can log that as well
                    if debug:
                        print(f"Received 503 Service Unavailable for URL {url}, but rate limit headers are missing.")

            if debug:
                print(f"Request failed for URL {url} with status code {response.status_code} ({response.reason}).")
            return default_return

    def get_agencies_by_territory(
        self, territory: str = None, default_return=None, success_codes: list = None, debug: bool = False
    ) -> dict | list:
        """Get agencies by territory.

        Args:
            territory (str, optional): The territory abbreviation or name. Defaults to None, which means all territories.
            default_return (Any, optional): The value to return if the request fails. Defaults to None.
            success_codes (list, optional): A list of HTTP status codes considered successful. Defaults to None.
            debug (bool, optional): If True, enables debug logging. Defaults to False.
        """
        url_path = lambda territory: f"crime/fbi/cde/agency/byStateAbbr/{territory}?API_KEY={self.api_key}"
        if territory:
            territory = self.data.get_territory_by_abbr(territory) or self.data.get_territory_by_name(territory)
            result = self.get(
                url_path=url_path(territory.abbreviation),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )
            (
                print(f"found {len(result.keys())} agencies for territory {territory.name} ({territory.abbreviation})")
                if debug
                else None
            )
            return result

        results = []
        for territory in self.data.us_territories:
            result = self.get(
                url_path=url_path(territory.abbreviation),
                default_return=default_return,
                success_codes=success_codes,
                debug=debug,
            )
            if result is not None:
                (
                    print(
                        f"found {len(result.keys())} agencies for territory {territory.name} ({territory.abbreviation})"
                    )
                    if debug
                    else None
                )
                results.append(result)
        return results

    def get_agencies_by_origin_code(self, origin_code: str = None):
        None

    def get_arrests_by_offense(self, offense_code: str = None):
        None

    def get_arrests_by_origin_and_offense(self, origin_code: str = None, offense_code: str = None):
        None

    def get_arrests_by_state_and_offense(self, state: str = None, offense_code: str = None):
        None
