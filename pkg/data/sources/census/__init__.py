import os

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
CENSUS_API_BASE_URL = os.getenv("CENSUS_API_BASE_URL")

name = "census"
description = "U.S. Census Bureau Data"
license = "Public Domain"
provider = "U.S. Census Bureau"
maintainer = "Aaron Samuel"
url = "https://www.census.gov/data/developers/data-sets.html"
supported = [
    {
        "name": "American Community Survey (ACS)",
        "url": "https://api.census.gov/data/2024/acs/acs1.html",
        "variant": "1-year estimates",
    }
]

if CENSUS_API_BASE_URL is None or CENSUS_API_KEY is None:
    raise EnvironmentError("CENSUS_API_BASE_URL and CENSUS_API_KEY must be set in environment variables.")

from .main import (
    get_census_acs_variables,
    get_census_acs_detailed,
    get_census_acs_detailed_by_state,
    get_census_acs_detailed_by_state_county,
)




# ---
# name: census
# description: U.S. Census Bureau Data
# license: Public Domain
# url: https://www.census.gov/data/developers/data-sets.html
# maintainer: Aaron Samuel
# supported:
#   - name: American Community Survey (ACS)
#     url: https://api.census.gov/data/2024/acs/acs1.html