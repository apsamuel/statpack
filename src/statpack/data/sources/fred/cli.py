import os

FRED_API_BASE_URL = os.getenv("FRED_API_BASE_URL")
FRED_API_KEY = os.getenv("FRED_API_KEY")

name = "fred"
description = "Federal Reserve Economic Data (FRED)"
license = "Public Domain"
provider = "Federal Reserve Bank of St. Louis"
maintainer = "aaron.psamuel@spicydev.it"
api = "https://fred.stlouisfed.org/docs/api/fred/"
about = "https://fredhelp.stlouisfed.org/fred/about/about-fred/what-is-fred/"
supported = []
docs = [""]

if FRED_API_BASE_URL is None or FRED_API_KEY is None:
    raise EnvironmentError(
        "FRED_API_BASE_URL and FRED_API_KEY (https://fredaccount.stlouisfed.org/apikey) must be set in environment variables."
    )
