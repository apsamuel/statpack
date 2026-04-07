import requests
from . import GOV_API_BASE_URL, GOV_API_KEY


class Client:
    def __init__(
        self, api_base_url: str = GOV_API_BASE_URL, api_key: str = GOV_API_KEY
    ):
        self.api_base_url = api_base_url
        self.api_key = api_key

    def get(self, path: str = None, default=None, success: list = None) -> dict:

        if path is None:
            raise ValueError("Path must be provided for the API request.")

        if success is None:
            success = [200]
        url = f"{self.api_base_url}/{path}?api_key={self.api_key}"
        response = requests.get(url)
        if response.status_code in success:
            return response.json()
        else:
            return default
