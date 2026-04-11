import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date
from ..model import Request, FailedRequest
from .data import CensusData, State, Race
from . import CENSUS_API_BASE_URL, CENSUS_API_KEY


class Client:
    def __init__(self, api_base_url: str = CENSUS_API_BASE_URL, api_key: str = CENSUS_API_KEY):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.last: Request | None = None
        self.requests: int = 0
        self.failed_requests: list[FailedRequest] = []
        self.limited = False
        self.limit_remaining = None
        self.limit_reset = None
        self.data = CensusData()
        self.latest_census_year = date.today().year - 1

    def _get(self, url_path: str = None, default_return=None, success_codes: list = None, debug: bool = False):
        if url_path is None:
            raise ValueError("URL path is required")

        if success_codes is None:
            success_codes = [200]

        separator = "&" if "?" in url_path else "?"

        leading_slash = "" if url_path.startswith("/") else "/"

        url = f"{self.api_base_url}{leading_slash}{url_path}{separator}key={self.api_key}"

        if debug:
            print(f"Making GET request to {url}")

        response = requests.get(url)

        self.requests += 1
        if response.status_code in success_codes:
            self.last = Request(
                url=url, params=None, request_headers=response.request.headers, response_headers=response.headers
            )
            return response.json()
        else:
            failed_request = FailedRequest(url=url, status_code=response.status_code, reason=response.reason)
            self.failed_requests.append(failed_request)

            if response.status_code in (429,):
                if debug:
                    print(f"Rate limit hit: {response.status_code} {response.reason}")
                self.limited = True
                self.limit_remaining = response.headers.get("X-RateLimit-Remaining")
                self.limit_reset = response.headers.get("X-RateLimit-Reset")

            if response.status_code in (500, 502, 503, 504):
                if debug:
                    print(f"Server error: {response.status_code} {response.reason}")

            return default_return

    def get_acs_detailed_variables(self, year: int = 2024, raw: bool = False) -> list[dict] | pd.DataFrame:
        results = []
        url = lambda year: f"{self.api_base_url}/{year}/acs/acs1/variables.html"
        response = requests.get(url(year))
        if response.status_code == 200:
            html = BeautifulSoup(response.text, "html.parser")
            table = html.find("table")
            if table:
                headers = [th.get_text(strip=True) for th in table.find("tr").find_all("th")]
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) == len(headers):
                        record = {headers[i]: cols[i].get_text(strip=True) for i in range(len(headers))}
                        results.append(record)
        return pd.DataFrame(results) if not raw else results

    def get_acs_detailed_national(
        self,
        year: int = 2024,
        debug: bool = False,
        raw: bool = False,
        variables=["NAME", "B01001_001E", "B01001_002E", "B01001_026E"],
    ) -> list[dict] | pd.DataFrame:
        results = []
        url = lambda year: f"{year}/acs/acs1?get={','.join(variables)}&for=us:*&key={self.api_key}"
        data = self._get(url_path=url(year), debug=debug)
        headers = data[0]
        for row in data[1:]:
            record = {headers[i]: row[i] for i in range(len(headers))}
            results.append(record)
        return pd.DataFrame(results) if not raw else results

    def get_acs_detailed_by_state(
        self,
        year: int = 2024,
        state: str = None,
        debug: bool = False,
        raw: bool = False,
        variables=["NAME", "B01001_001E", "B01001_002E", "B01001_026E"],
    ):
        results = []

        year: int = int(year)

        if year < 2005 or year > self.latest_census_year:
            raise ValueError(f"Year must be between 2005 and {self.latest_census_year}")

        if state is None:
            raise ValueError("State is required")

        state: State | None = self.data.get_state_by_name(state) or self.data.get_state_by_code(int(state))

        if state is None:
            raise ValueError(f"State not found")

        url = lambda year, state: f"{year}/acs/acs1?get={','.join(variables)}&for=state:{state.code}&key={self.api_key}"

        data = self._get(url_path=url(year, state), debug=debug)
        if data:
            headers = data[0]
            for row in data[1:]:
                record = {headers[i]: row[i] for i in range(len(headers))}
                results.append(record)
        return pd.DataFrame(results) if not raw else results
