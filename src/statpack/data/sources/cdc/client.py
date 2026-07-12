import re
import time
from xml.sax.saxutils import escape as xml_escape

import requests
import pandas as pd
from bs4 import BeautifulSoup

from ..models import FailedRequest, Request
from .models import Data, WonderDataset, get_data_model

# ── D76: Underlying Cause of Death ICD-10 (1999-2020) ────────────────────────

# Human-readable group-by names → CDC WONDER B-parameter values
_D76_GROUP_BY: dict[str, str] = {
    "year": "D76.V1-level1",
    "month": "D76.V1-level2",
    "icd10_chapter": "D76.V2-level1",
    "icd10_subchapter": "D76.V2-level2",
    "cause_113": "D76.V4-level2",
    "age_10yr": "D76.V5",
    "age_infant": "D76.V6",
    "gender": "D76.V7",
    "race": "D76.V8",
    "state": "D76.V9-level2",
    "county": "D76.V9-level3",
    "census_region": "D76.V10-level1",
    "census_division": "D76.V10-level2",
    "urbanization_2006": "D76.V11",
    "hispanic": "D76.V17",
    "urbanization_2013": "D76.V19",
    "autopsy": "D76.V20",
    "place_of_death": "D76.V21",
    "injury_intent": "D76.V22",
    "injury_mechanism": "D76.V23",
    "weekday": "D76.V24",
    "substance": "D76.V25",
    "hhs_region": "D76.V27",
}

# Human-readable measure names → CDC WONDER M-parameter values
_D76_MEASURES: dict[str, str] = {
    "deaths": "D76.M1",
    "population": "D76.M2",
    "crude_rate": "D76.M3",
    "crude_rate_lower_ci": "D76.M31",
    "crude_rate_upper_ci": "D76.M32",
    "age_adjusted_rate": "D76.M4",
    "age_adjusted_rate_se": "D76.M41",
    "age_adjusted_rate_lower_ci": "D76.M42",
    "age_adjusted_rate_upper_ci": "D76.M43",
}

# Default V_ (where-clause) parameters — all values included
_D76_V_DEFAULTS: dict[str, str | list[str]] = {
    "V_D76.V1": "*All*",
    "V_D76.V9": "*All*",
    "V_D76.V17": "*All*",
    "V_D76.V6": "",
    "V_D76.V5": ["*All*"],
    "V_D76.V7": ["*All*"],
    "V_D76.V8": ["*All*"],
    "V_D76.V19": "*All*",
    "V_D76.V20": ["*All*"],
    "V_D76.V21": ["*All*"],
    "V_D76.V22": ["*All*"],
    "V_D76.V23": ["*All*"],
    "V_D76.V25": ["*All*"],
    "V_D76.V27": "*All*",
}

# Default I_ (info/label) parameters
_D76_I_DEFAULTS: dict[str, str] = {
    "I_D76.V1": "*All* (All Dates)",
    "I_D76.V2": "*All* (All Causes of Death)",
    "I_D76.V4": "*All* (All Causes of Death)",
    "I_D76.V5": "*All* (All Ages)",
    "I_D76.V6": "*All* (All Ages)",
    "I_D76.V7": "*All* (All Genders)",
    "I_D76.V8": "*All* (All Races)",
    "I_D76.V17": "*All* (All Origins)",
    "I_D76.V9": "*All* (All States and DC)",
    "I_D76.V19": "*All* (All Urbanization Levels)",
    "I_D76.V20": "*All* (All Autopsies)",
    "I_D76.V21": "*All* (All Places of Death)",
    "I_D76.V22": "*All* (All Intents)",
    "I_D76.V23": "*All* (All Mechanisms and All Other Causes)",
    "I_D76.V25": "*All* (All Drug/Alcohol Induced Causes)",
    "I_D76.V27": "*All* (All HHS Regions)",
}

# Default O_ (options/radio) parameters
_D76_O_DEFAULTS: dict[str, str] = {
    "O_bmi": "bmival",
    "O_age": "D76.V5",
    "O_death_nohr": "0",
    "O_location": "D76.V9",
    "O_rate_per": "100000",
    "O_precision": "1",
    "O_title": "",
    "O_show_totals": "false",
    "O_show_zeros": "false",
    "O_show_suppressed": "false",
    "O_aar": "aar_none",
    "O_aar_pop": "0000",
    "O_ucd_icd10_103cause": "D76.V27",
}

# CDC WONDER web service restriction: these group-by dimensions require the browser interface.
# The /controller/datarequest/ API endpoint only returns national-level data.
# Attempting to group by any location variable returns HTTP 500 with the message:
# "Only national data are available for this dataset when using the WONDER web service."
_D76_LOCATION_GROUP_DIMS: frozenset[str] = frozenset(
    {"state", "county", "census_region", "census_division", "hhs_region", "urbanization_2006", "urbanization_2013"}
)

# Misc/hidden form fields required by the WONDER request
_D76_MISC: dict[str, str] = {
    "action-Send": "Send",
    "finder-stage-D76.V1": "codeset",
    "finder-stage-D76.V2": "codeset",
    "finder-stage-D76.V8": "codeset",
    "finder-stage-D76.V7": "codeset",
    "finder-stage-D76.V17": "codeset",
    "finder-stage-D76.V9": "codeset",
    "stage": "request",
}


class Client:

    def __init__(self, api_base_url: str = "https://wonder.cdc.gov"):
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {"User-Agent": "StatPack/1.0", "Accept": "application/xml,text/html"}
        self.last: Request | None = None
        self.requests: int = 0
        self.failed_requests: list[FailedRequest] = []
        self.limited = False
        self.limit_remaining = None
        self.limit_reset = None
        self.data = get_data_model()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sanitize_column_name(self, name: str) -> str:
        name = name.lower().replace(" ", "_")
        name = re.sub(r"[\)\(/\-]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = re.sub(r"_+$", "", name)
        return name

    def _build_xml_request(self, params: dict) -> str:
        """Convert a parameter dict to a CDC WONDER XML request string.

        Values may be strings or lists of strings. All content is XML-escaped.
        """
        xml = "<request-parameters>\n"
        for key, value in params.items():
            xml += "<parameter>\n"
            xml += f"<name>{xml_escape(str(key))}</name>\n"
            if isinstance(value, list):
                if value:
                    for v in value:
                        xml += f"<value>{xml_escape(str(v))}</value>\n"
                else:
                    xml += "<value></value>\n"
            else:
                xml += f"<value>{xml_escape(str(value))}</value>\n"
            xml += "</parameter>\n"
        xml += "</request-parameters>"
        return xml

    def _parse_xml_response(self, xml_text: str, debug: bool = False) -> list[list[str]]:
        """Parse a CDC WONDER XML response into a list of data rows.

        Each row is a list of cell values. Uses the 'v' (numeric value)
        attribute when available, falling back to 'l' (display label).
        Rows with no cells are skipped.
        """
        if "<html" in xml_text[:500].lower():
            print("[CDC WONDER] Response is HTML, not XML — check parameters or API availability")
            if debug:
                print(xml_text[:2000])
            return []

        soup = BeautifulSoup(xml_text, "lxml-xml")

        error_tag = soup.find("error")
        if error_tag:
            print(f"[CDC WONDER] API error: {error_tag.get_text(strip=True)}")
            if debug:
                print(xml_text[:2000])
            return []

        message_tag = soup.find("message")
        if message_tag:
            msg_text = message_tag.get_text(strip=True)
            if msg_text:
                print(f"[CDC WONDER] Message: {msg_text[:500]}")

        records = []
        for row in soup.find_all("r"):
            cells = row.find_all("c")
            if not cells:
                continue
            row_data = []
            for cell in cells:
                v = cell.get("v")
                l_val = cell.get("l")
                row_data.append(v if v is not None else (l_val or ""))
            records.append(row_data)

        return records

    # ── Transport ─────────────────────────────────────────────────────────────

    def _get(
        self, url_path: str = None, default_return=None, success_codes: list = None, debug: bool = False, **kwargs
    ):
        return None

    def _post(
        self, dataset_id: str, params: dict, default_return=None, success_codes: list | None = None, debug: bool = False
    ) -> str | None:
        """POST an XML data request to a CDC WONDER dataset endpoint.

        Args:
            dataset_id: CDC WONDER dataset identifier (e.g. "D76").
            params: Combined parameter dict (B_, M_, V_, I_, O_, misc keys).
            default_return: Value returned on a non-success response.
            success_codes: HTTP status codes considered successful. Defaults to [200].
            debug: Print request/response details.

        Returns:
            Raw XML response text, or default_return on failure.
        """
        if success_codes is None:
            success_codes = [200]

        url = f"{self.api_base_url}/controller/datarequest/{dataset_id}"
        xml_request = self._build_xml_request(params)
        form_data = {"request_xml": xml_request, "accept_datause_restrictions": "true"}

        if debug:
            print(f"POST {url}")
            print(f"request_xml:\n{xml_request}")

        response = requests.post(url, data=form_data, headers=self.headers, timeout=60)
        self.requests += 1

        if debug:
            print(f"response: {response.status_code} ({response.reason})")

        if response.status_code in success_codes:
            self.last = Request(
                url=url, params=params, request_headers=dict(self.headers), response_headers=dict(response.headers)
            )
            return response.text

        self.failed_requests.append(
            FailedRequest(url=url, status_code=response.status_code, reason=response.reason, timestamp=time.time())
        )
        if debug:
            print(f"request failed: {response.status_code} {response.reason}")
        return default_return

    # ── Generic query ─────────────────────────────────────────────────────────

    def query(
        self,
        dataset_id: str,
        params: dict,
        columns: list[str] | None = None,
        raw: bool = False,
        debug: bool = False,
        default_return=None,
    ) -> list[list] | pd.DataFrame:
        """Send a raw parameter dict to any CDC WONDER dataset.

        Args:
            dataset_id: CDC WONDER dataset identifier (e.g. "D76").
            params: Full parameter dict (B_, M_, V_, I_, O_, misc keys) as
                expected by the CDC WONDER controller.
            columns: Optional column labels for the returned DataFrame.
            raw: Return list[list] instead of pd.DataFrame.
            debug: Enable debug logging.
            default_return: Value returned on failure.

        Returns:
            pd.DataFrame (default) or list[list] when raw=True.
        """
        xml_text = self._post(dataset_id=dataset_id, params=params, default_return=default_return, debug=debug)
        if xml_text is None:
            return default_return

        records = self._parse_xml_response(xml_text, debug=debug)
        if raw:
            return records

        df = pd.DataFrame(records)
        if columns and not df.empty and len(df.columns) == len(columns):
            df.columns = [self._sanitize_column_name(c) for c in columns]
        return df

    # ── Domain methods ────────────────────────────────────────────────────────

    def get_mortality(
        self,
        group_by: list[str] | None = None,
        measures: list[str] | None = None,
        filters: dict | None = None,
        dataset: str = WonderDataset.UCD_1999_2020,
        raw: bool = False,
        debug: bool = False,
        default_return=None,
    ) -> list[list] | pd.DataFrame:
        """Query CDC WONDER Underlying Cause of Death data (D76, ICD-10, 1999-2020).

        Args:
            group_by: Dimensions to group results by. Valid values:
                year, month, icd10_chapter, icd10_subchapter, cause_113,
                age_10yr, age_infant, gender, race, state, county,
                census_region, census_division, urbanization_2006, hispanic,
                urbanization_2013, autopsy, place_of_death, injury_intent,
                injury_mechanism, weekday, substance, hhs_region.
                Defaults to ["year"].
            measures: Metrics to return. Valid values:
                deaths, population, crude_rate, crude_rate_lower_ci,
                crude_rate_upper_ci, age_adjusted_rate, age_adjusted_rate_se,
                age_adjusted_rate_lower_ci, age_adjusted_rate_upper_ci.
                Defaults to ["deaths", "population", "crude_rate"].
            filters: Dict of CDC WONDER V_ parameter overrides. Keys omit the
                leading "V_" prefix (e.g. {"D76.V7": ["F"], "D76.V9": "*All*"}).
                See https://wonder.cdc.gov/wonder/help/ucd.html for variable codes.
            dataset: CDC WONDER dataset ID. Defaults to WonderDataset.UCD_1999_2020.
            raw: Return list[list] instead of pd.DataFrame.
            debug: Enable debug logging.
            default_return: Value returned on failure.

        Returns:
            pd.DataFrame with columns from group_by + measures, or list[list] when raw=True.

        Example::

            client = Client()
            df = client.get_mortality(
                group_by=["year", "state"],
                measures=["deaths", "population"],
                filters={"D76.V7": ["F"]},   # female only
            )
        """
        if group_by is None:
            group_by = ["year"]
        if measures is None:
            measures = ["deaths", "population", "crude_rate"]

        # Validate: CDC WONDER web service does not support geographic group_by.
        _forbidden_geo = _D76_LOCATION_GROUP_DIMS.intersection(group_by)
        if _forbidden_geo:
            raise ValueError(
                f"CDC WONDER web service only returns national data. "
                f"Geographic group_by dimensions are not supported via the API: "
                f"{sorted(_forbidden_geo)}. "
                f"Remove them from group_by. "
                f"(Restriction: state, county, region, division, and urbanization "
                f"are available in the CDC WONDER browser interface only.)"
            )

        # B_ parameters (group-by / by-variables)
        b_params: dict[str, str] = {}
        for i, dim in enumerate(group_by[:5], start=1):
            b_val = _D76_GROUP_BY.get(dim)
            if b_val is None:
                raise ValueError(f"Unknown group_by dimension '{dim}'. " f"Valid options: {sorted(_D76_GROUP_BY)}")
            b_params[f"B_{i}"] = b_val
        for i in range(len(group_by) + 1, 6):
            b_params[f"B_{i}"] = "*None*"

        # M_ parameters (measures)
        m_params: dict[str, str] = {}
        for i, m in enumerate(measures, start=1):
            m_val = _D76_MEASURES.get(m)
            if m_val is None:
                raise ValueError(f"Unknown measure '{m}'. " f"Valid options: {sorted(_D76_MEASURES)}")
            m_params[f"M_{i}"] = m_val

        # F_ parameters (finder — empty list = no hierarchical restriction)
        f_params: dict[str, list] = {
            "F_D76.V1": [],
            "F_D76.V2": [],
            "F_D76.V4": [],
            "F_D76.V8": [],
            "F_D76.V7": [],
            "F_D76.V17": [],
            "F_D76.V9": [],
        }

        # V_ parameters (where-clause) — start from defaults, apply overrides
        v_params: dict = dict(_D76_V_DEFAULTS)
        if filters:
            for var, val in filters.items():
                key = var if var.startswith("V_") else f"V_{var}"
                v_params[key] = val

        # Validate: state codes passed in V_D76.V9 must be 2-digit FIPS, not 5-digit county codes.
        v9_val = v_params.get("V_D76.V9", "*All*")
        if v9_val and v9_val != "*All*":
            codes = v9_val if isinstance(v9_val, list) else [v9_val]
            for code in codes:
                if isinstance(code, str) and len(code) == 5 and code.isdigit():
                    raise ValueError(
                        f"State filter 'D76.V9' received '{code}', which looks like a 5-digit county "
                        f"FIPS code. Use 2-digit state FIPS codes (e.g., '46' for South Dakota) or "
                        f"'*All*' for all states. For county-level data, group by 'county' and filter "
                        f"via 'D76.V9' using the county's 5-digit code — but note that V_D76.V9 only "
                        f"accepts state-level codes; county filtering requires the Finder parameter."
                    )

        # Validate: when grouping by month, V_D76.V1 must be *All* or use month-level
        # codes (YYYY/MM).  Year-level codes (e.g. "2014") select a level-1 D76.V1 item
        # while month grouping (D76.V1-level2) selects its subordinates — CDC WONDER
        # treats this as a parent/child conflict and returns HTTP 500.
        if "month" in group_by:
            v1_check = v_params.get("V_D76.V1", "*All*")
            year_codes = (
                [v1_check]
                if isinstance(v1_check, str) and v1_check not in ("*All*", "")
                else (v1_check if isinstance(v1_check, list) else [])
            )
            bad = [c for c in year_codes if isinstance(c, str) and len(c) == 4 and c.isdigit()]
            if bad:
                raise ValueError(
                    f"Cannot filter by year {bad} when grouping by 'month': CDC WONDER "
                    f"disallows selecting a year (D76.V1 level-1) together with its subordinate "
                    f"months (D76.V1 level-2). Either omit the year filter to retrieve all years "
                    f"grouped by month, or supply month-level codes in 'YYYY/MM' format "
                    f'(e.g. filters={{"D76.V1": ["2014/01", "2014/02", ...]}}). '
                )

        # I_ parameters (info/label display)
        i_params = dict(_D76_I_DEFAULTS)
        # Keep I_D76.V1 in sync with V_D76.V1 so CDC WONDER doesn't see a mismatch.
        v1_val = v_params.get("V_D76.V1", "*All*")
        if v1_val and v1_val != "*All*":
            years = v1_val if isinstance(v1_val, list) else [v1_val]
            i_params["I_D76.V1"] = ", ".join(str(y) for y in years)

        # O_ parameters (options)
        o_params = dict(_D76_O_DEFAULTS)
        _age_adjusted_measures = {
            "age_adjusted_rate",
            "age_adjusted_rate_se",
            "age_adjusted_rate_lower_ci",
            "age_adjusted_rate_upper_ci",
        }
        _age_group_dims = {"age_10yr", "age_infant"}
        if any(m in _age_adjusted_measures for m in measures) and any(d in _age_group_dims for d in group_by):
            raise ValueError(
                "Age-adjusted rates cannot be produced when grouping by age ('age_10yr' or 'age_infant'). "
                "Remove age-adjusted measures or remove age dimensions from group_by."
            )
        if any("age_adjusted" in m for m in measures):
            o_params["O_aar"] = "aar_std"

        # VM_ parameters
        vm_params: dict[str, str] = {"VM_aar_pop": ""}

        # Misc/hidden form fields
        misc_params = dict(_D76_MISC)

        all_params = {
            **b_params,
            **m_params,
            **f_params,
            **v_params,
            **i_params,
            **o_params,
            **vm_params,
            **misc_params,
        }

        xml_text = self._post(dataset_id=dataset, params=all_params, default_return=default_return, debug=debug)
        if xml_text is None:
            return default_return

        records = self._parse_xml_response(xml_text, debug=debug)
        if raw:
            return records

        columns = list(group_by) + list(measures)
        df = pd.DataFrame(records)
        if not df.empty and len(df.columns) == len(columns):
            df.columns = [self._sanitize_column_name(c) for c in columns]
        return df

    def get_natality(
        self,
        group_by: list[str] | None = None,
        measures: list[str] | None = None,
        filters: dict | None = None,
        dataset: str = WonderDataset.NATALITY,
        raw: bool = False,
        debug: bool = False,
        default_return=None,
    ) -> list[list] | pd.DataFrame:
        """Query CDC WONDER Natality (births) data.

        Natality uses a different variable schema from D76. Pass CDC WONDER
        variable codes directly as group_by and measures values, or use
        client.query() for full parameter control.

        Args:
            group_by: CDC WONDER variable codes to group by (passed as B_ params).
                Example: ["D149.V1"] for year. Defaults to ["D149.V1"].
            measures: CDC WONDER measure codes (passed as M_ params).
                Defaults to ["D149.M1"] (number of births).
            filters: Dict of V_ parameter overrides (keys omit "V_" prefix).
            dataset: CDC WONDER dataset ID. Defaults to WonderDataset.NATALITY.
            raw: Return list[list] instead of pd.DataFrame.
            debug: Enable debug logging.
            default_return: Value returned on failure.

        Returns:
            pd.DataFrame or list[list] when raw=True.

        Note:
            See https://wonder.cdc.gov/natality-current.html for the available
            variable and measure codes for this dataset.
        """
        return self._generic_query(
            group_by=group_by if group_by is not None else ["D149.V1"],
            measures=measures if measures is not None else ["D149.M1"],
            filters=filters,
            dataset=dataset,
            raw=raw,
            debug=debug,
            default_return=default_return,
        )

    def get_cancer_incidence(
        self,
        group_by: list[str] | None = None,
        measures: list[str] | None = None,
        filters: dict | None = None,
        dataset: str = WonderDataset.CANCER_INCIDENCE,
        raw: bool = False,
        debug: bool = False,
        default_return=None,
    ) -> list[list] | pd.DataFrame:
        """Query CDC WONDER United States Cancer Statistics — Incidence data.

        Args:
            group_by: CDC WONDER variable codes to group by (passed as B_ params).
            measures: CDC WONDER measure codes (passed as M_ params).
            filters: Dict of V_ parameter overrides (keys omit "V_" prefix).
            dataset: CDC WONDER dataset ID. Defaults to WonderDataset.CANCER_INCIDENCE.
            raw: Return list[list] instead of pd.DataFrame.
            debug: Enable debug logging.
            default_return: Value returned on failure.

        Note:
            See https://wonder.cdc.gov/cancer-v2022.html for available
            variable and measure codes. Use client.query() for full control.
        """
        return self._generic_query(
            group_by=group_by or [],
            measures=measures or [],
            filters=filters,
            dataset=dataset,
            raw=raw,
            debug=debug,
            default_return=default_return,
        )

    def get_cancer_mortality(
        self,
        group_by: list[str] | None = None,
        measures: list[str] | None = None,
        filters: dict | None = None,
        dataset: str = WonderDataset.CANCER_MORTALITY,
        raw: bool = False,
        debug: bool = False,
        default_return=None,
    ) -> list[list] | pd.DataFrame:
        """Query CDC WONDER United States Cancer Statistics — Mortality data.

        Args:
            group_by: CDC WONDER variable codes to group by (passed as B_ params).
            measures: CDC WONDER measure codes (passed as M_ params).
            filters: Dict of V_ parameter overrides (keys omit "V_" prefix).
            dataset: CDC WONDER dataset ID. Defaults to WonderDataset.CANCER_MORTALITY.
            raw: Return list[list] instead of pd.DataFrame.
            debug: Enable debug logging.
            default_return: Value returned on failure.

        Note:
            See https://wonder.cdc.gov/cancermort-v2021.html for available
            variable and measure codes. Use client.query() for full control.
        """
        return self._generic_query(
            group_by=group_by or [],
            measures=measures or [],
            filters=filters,
            dataset=dataset,
            raw=raw,
            debug=debug,
            default_return=default_return,
        )

    def get_aids_data(
        self,
        group_by: list[str] | None = None,
        measures: list[str] | None = None,
        filters: dict | None = None,
        dataset: str = WonderDataset.AIDS,
        raw: bool = False,
        debug: bool = False,
        default_return=None,
    ) -> list[list] | pd.DataFrame:
        """Query CDC WONDER AIDS Public Use Data (archival, 1981-2002).

        Args:
            group_by: CDC WONDER variable codes to group by (passed as B_ params).
            measures: CDC WONDER measure codes (passed as M_ params).
            filters: Dict of V_ parameter overrides (keys omit "V_" prefix).
            dataset: CDC WONDER dataset ID. Defaults to WonderDataset.AIDS.
            raw: Return list[list] instead of pd.DataFrame.
            debug: Enable debug logging.
            default_return: Value returned on failure.

        Note:
            See https://wonder.cdc.gov/aids-v2002.html for available
            variable and measure codes. Use client.query() for full control.
        """
        return self._generic_query(
            group_by=group_by or [],
            measures=measures or [],
            filters=filters,
            dataset=dataset,
            raw=raw,
            debug=debug,
            default_return=default_return,
        )

    # ── Internal shared query helper ──────────────────────────────────────────

    def _generic_query(
        self,
        group_by: list[str],
        measures: list[str],
        filters: dict | None,
        dataset: str,
        raw: bool,
        debug: bool,
        default_return,
    ) -> list[list] | pd.DataFrame:
        """Build and dispatch a minimal CDC WONDER request for datasets that
        don't have a full parameter mapping defined in this client."""
        b_params: dict[str, str] = {}
        for i, v in enumerate(group_by[:5], start=1):
            b_params[f"B_{i}"] = v
        for i in range(len(group_by) + 1, 6):
            b_params[f"B_{i}"] = "*None*"

        m_params: dict[str, str] = {f"M_{i}": v for i, v in enumerate(measures, start=1)}

        v_params: dict = {}
        if filters:
            for var, val in filters.items():
                key = var if var.startswith("V_") else f"V_{var}"
                v_params[key] = val

        misc = {"action-Send": "Send", "stage": "request"}

        all_params = {**b_params, **m_params, **v_params, **misc}

        xml_text = self._post(dataset_id=dataset, params=all_params, default_return=default_return, debug=debug)
        if xml_text is None:
            return default_return

        records = self._parse_xml_response(xml_text, debug=debug)
        if raw:
            return records

        columns = list(group_by) + list(measures)
        df = pd.DataFrame(records)
        if not df.empty and len(df.columns) == len(columns):
            df.columns = [self._sanitize_column_name(c) for c in columns]
        return df
