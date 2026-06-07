import os
from pathlib import Path

from .client import Client

WONDER_BASE_URL = "https://wonder.cdc.gov"

name = "cdc"
description = "CDC WONDER Data Explorer"

license = "Public Domain"
provider = "CDC"
maintainer = "aaron.psamuel@spicydev.it"
api = "https://wonder.cdc.gov/controller/datarequest/"
about = "https://wonder.cdc.gov"
supported = [
    {
        "name": "Underlying Cause of Death (ICD-10)",
        "url": "https://wonder.cdc.gov/ucd-icd10.html",
        "dataset_id": "D76",
        "years": "1999-2020",
    },
    {
        "name": "Natality",
        "url": "https://wonder.cdc.gov/natality-current.html",
        "dataset_id": "D149",
        "years": "2007-2024",
    },
    {
        "name": "United States Cancer Statistics — Incidence",
        "url": "https://wonder.cdc.gov/cancer-v2022.html",
        "dataset_id": "cancer-v2022",
        "years": "1999-2022",
    },
    {
        "name": "United States Cancer Statistics — Mortality (bridged race)",
        "url": "https://wonder.cdc.gov/cancermort-v2021.html",
        "dataset_id": "cancermort-v2021",
        "years": "1999-2021",
    },
    {
        "name": "AIDS Public Use Data",
        "url": "https://wonder.cdc.gov/aids-v2002.html",
        "dataset_id": "AIDS-v2002",
        "years": "1981-2002",
    },
]
docs = ["https://wonder.cdc.gov/wonder/help/ucd.html", "https://wonder.cdc.gov/wonder/help/natality.html"]
load_seed = os.environ.get("LOAD_SEED_DATA", "true").lower() == "true"
seed = Path(__file__).parent / "data" / "seed.json"
