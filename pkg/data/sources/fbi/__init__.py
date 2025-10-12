import os

FBI_API_BASE_URL = os.getenv("GOV_API_BASE_URL")
FBI_API_KEY = os.getenv("GOV_API_KEY")

name = "fbi"
description = "FBI Crime Data"
license = "Public Domain"
maintainer = "Aaron Samuel"
url = "https://www.fbi.gov/developer"
supported = [
    {
        "name": "Uniform Crime Reporting (UCR)",
        "url": "https://www.fbi.gov/services/cjis/ucr",
        "variant": "National Incident-Based Reporting System (NIBRS)",
    }
]

if FBI_API_BASE_URL is None or FBI_API_KEY is None:
    raise EnvironmentError("GOV_API_BASE_URL and GOV_API_KEY must be set in environment variables.")

from .main import (
    get_cde_reporting_agencies,
    get_cde_arrest_totals_by_state,
    get_cde_arrest_counts_by_state,
    get_cde_arrest_counts_by_origin,
    get_cde_arrest_totals_by_origin
)