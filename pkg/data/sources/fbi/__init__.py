import os

GOV_API_BASE_URL = os.getenv("GOV_API_BASE_URL")
GOV_API_KEY = os.getenv("GOV_API_KEY")

name = "fbi"
description = "FBI Crime Data Explorer"

license = "Public Domain"
provider = "FBI"
maintainer = "aaron.psamuel@spicydev.it"
api = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi"
about = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/about"
supported = [
    {
        "name": "Uniform Crime Reporting (UCR)",
        "url": "https://www.fbi.gov/services/cjis/ucr",
        "variant": "National Incident-Based Reporting System (NIBRS)",
    }
]
docs = ["https://ucr.fbi.gov/nibrs/2011/resources/nibrs-offense-codes"]

if GOV_API_BASE_URL is None or GOV_API_KEY is None:
    raise EnvironmentError(
        "GOV_API_BASE_URL and GOV_API_KEY (https://api.data.gov/signup/) must be set in environment variables."
    )


from .client import Client

from .main import (
    get_reporting_agencies,
    get_arrest_counts_by_state,
    get_arrest_totals_by_state,
    get_arrest_counts_by_state,
    get_arrest_counts_by_origin,
    get_arrest_totals_by_origin,
    get_nibrs_totals_by_state,
    get_summarized_by_state,
    get_expanded_homicide_counts_by_state,
)
