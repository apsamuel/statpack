import requests
from . import FRED_API_BASE_URL, FRED_API_KEY
from .data import FREDData


class Client:

    def __init__(self, api_base_url: str = FRED_API_BASE_URL, api_key: str = FRED_API_KEY):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        self.last = None
        self.requests = 0
        self.failed_requests = []
        self.limited = False
        self.limit_remaining = None
        self.limit_reset = None
        self.data = FREDData()

    # handle pagination of results gracefully and recursively until all data is fetched
    def _get(
        self, url_path: str = None, default_return=None, success_codes: list = None, debug: bool = False
    ) -> dict | list | None:
        if url_path is None:
            raise ValueError("'url_path' is required")

        if success_codes is None:
            success_codes = [200]

        separator = "&" if "?" in url_path else "?"
        leading_slash = "" if url_path.startswith("/") else "/"
        url = f"{self.api_base_url}{leading_slash}{url_path}{separator}api_key={self.api_key}&file_type=json"

        if debug:
            print(f"Making GET request to {url}")

        response = requests.get(url, headers=self.headers)
        self.requests += 1

        if response.status_code in success_codes:
            self.last = response

            data = response.json()

            # Handle pagination if the response includes pagination metadata
            if "count" in data and "offset" in data and "limit" in data:
                total_count = int(data["count"])
                offset = int(data["offset"])
                limit = int(data["limit"])

                if debug:
                    print(f"Pagination detected: total_count={total_count}, offset={offset}, limit={limit}")

                if offset + limit < total_count:
                    next_offset = offset + limit
                    next_url_path = f"{url_path}{separator}offset={next_offset}"
                    next_data = self._get(next_url_path, default_return, success_codes, debug)
                    if isinstance(data, dict) and isinstance(next_data, dict):
                        data.update(next_data)
                    elif isinstance(data, list) and isinstance(next_data, list):
                        data.extend(next_data)
                    else:
                        if debug:
                            print("Warning: Inconsistent data types during pagination")
            return data
