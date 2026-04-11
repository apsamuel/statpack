"""Comprehensive test suite for pkg.data.sources.fbi.client.Client.

Covers:
  - Client.__init__ — attribute defaults and header setup
  - Client._clean_column_prefix / _clean_column_name — string normalisation
  - Client.get — URL construction, api_key handling, response routing
  - Client.get_agencies_by_territory — single territory, all territories, raw/df
  - Client.get_arrest_counts_by_state — URL params, data shape, edge cases
  - Client.get_arrest_totals_by_state — URL params, data shape, edge cases
  - Request / FailedRequest pydantic models

HTTP is mocked throughout using the ``responses`` library so no real network
calls are made.
"""

import os

# Ensure the FBI package can be imported even when the real env vars are absent.
os.environ.setdefault("GOV_API_BASE_URL", "https://example.test")
os.environ.setdefault("GOV_API_KEY", "test-api-key")

import pytest
import responses as resp
from unittest.mock import MagicMock
import pandas as pd

from pkg.data.sources.fbi.client import Client, Request, FailedRequest
from pkg.data.sources.fbi.models import USTerritory


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TEST_BASE_URL = "https://example.test"
TEST_API_KEY = "test-api-key"


@pytest.fixture
def client():
    return Client(api_base_url=TEST_BASE_URL, api_key=TEST_API_KEY)


@pytest.fixture
def ny_territory():
    return USTerritory(name="New York", abbreviation="NY")


@pytest.fixture
def ca_territory():
    return USTerritory(name="California", abbreviation="CA")


# ---------------------------------------------------------------------------
# Request / FailedRequest models
# ---------------------------------------------------------------------------


class TestRequestModel:
    def test_stores_url(self):
        r = Request(url="https://example.test/path")
        assert r.url == "https://example.test/path"

    def test_optional_fields_default_to_none(self):
        r = Request(url="https://example.test")
        assert r.params is None
        assert r.request_headers is None
        assert r.response_headers is None

    def test_accepts_all_fields(self):
        r = Request(
            url="https://example.test",
            params={"a": "1"},
            request_headers={"X-Api-Key": "k"},
            response_headers={"Content-Type": "application/json"},
        )
        assert r.params == {"a": "1"}
        assert r.request_headers["X-Api-Key"] == "k"


class TestFailedRequestModel:
    def test_stores_fields(self):
        fr = FailedRequest(url="https://example.test", status_code=404, reason="Not Found")
        assert fr.status_code == 404
        assert fr.reason == "Not Found"

    def test_timestamp_auto_populated(self):
        import time

        before = time.time()
        fr = FailedRequest(url="https://example.test", status_code=500, reason="error")
        after = time.time()
        assert before <= fr.timestamp <= after


# ---------------------------------------------------------------------------
# Client.__init__
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_stores_api_base_url(self, client):
        assert client.api_base_url == TEST_BASE_URL

    def test_stores_api_key(self, client):
        assert client.api_key == TEST_API_KEY

    def test_header_x_api_key(self, client):
        assert client.headers["X-Api-Key"] == TEST_API_KEY

    def test_header_user_agent(self, client):
        assert client.headers["User-Agent"] == "StatPack/1.0"

    def test_header_accept(self, client):
        assert client.headers["Accept"] == "application/json"

    def test_requests_counter_starts_at_zero(self, client):
        assert client.requests == 0

    def test_limited_starts_false(self, client):
        assert client.limited is False

    def test_limit_remaining_starts_none(self, client):
        assert client.limit_remaining is None

    def test_limit_reset_starts_none(self, client):
        assert client.limit_reset is None

    def test_last_starts_none(self, client):
        assert client.last is None

    def test_failed_requests_starts_empty(self, client):
        assert client.failed_requests == []

    def test_data_attribute_is_fbi_data(self, client):
        from pkg.data.sources.fbi.models import FBIData

        assert isinstance(client.data, FBIData)


# ---------------------------------------------------------------------------
# Client._clean_column_prefix
# ---------------------------------------------------------------------------


class TestCleanColumnPrefix:
    def test_lowercases(self, client):
        assert client._clean_column_prefix("MyPrefix") == "myprefix"

    def test_replaces_spaces_with_underscore(self, client):
        assert client._clean_column_prefix("my prefix") == "my_prefix"

    def test_multiple_words(self, client):
        assert client._clean_column_prefix("Arrestee Race") == "arrestee_race"

    def test_already_clean_unchanged(self, client):
        assert client._clean_column_prefix("already_clean") == "already_clean"

    def test_empty_string(self, client):
        assert client._clean_column_prefix("") == ""


# ---------------------------------------------------------------------------
# Client._clean_column_name
# ---------------------------------------------------------------------------


class TestCleanColumnName:
    def test_lowercases(self, client):
        assert client._clean_column_name("Column") == "column"

    def test_replaces_spaces_with_underscore(self, client):
        assert client._clean_column_name("my column") == "my_column"

    def test_replaces_forward_slash(self, client):
        result = client._clean_column_name("rate/100k")
        assert "/" not in result

    def test_replaces_hyphen(self, client):
        result = client._clean_column_name("col-name")
        assert "-" not in result

    def test_replaces_parentheses(self, client):
        result = client._clean_column_name("rate (per 100k)")
        assert "(" not in result
        assert ")" not in result

    def test_collapses_multiple_underscores(self, client):
        result = client._clean_column_name("a__b___c")
        assert "__" not in result

    def test_strips_trailing_underscore(self, client):
        result = client._clean_column_name("column-")
        assert not result.endswith("_")

    def test_complex_realistic_name(self, client):
        result = client._clean_column_name("Murder and Nonnegligent Manslaughter (Rate)")
        assert "(" not in result
        assert ")" not in result
        assert "__" not in result
        assert not result.endswith("_")

    def test_empty_string(self, client):
        assert client._clean_column_name("") == ""


# ---------------------------------------------------------------------------
# Client.get — validation
# ---------------------------------------------------------------------------


class TestClientGetValidation:
    def test_raises_value_error_when_url_path_is_none(self, client):
        with pytest.raises(ValueError, match="url_path"):
            client.get(url_path=None)


# ---------------------------------------------------------------------------
# Client.get — URL construction
# ---------------------------------------------------------------------------


class TestClientGetUrlConstruction:
    @resp.activate
    def test_api_key_appended_lowercase(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("crime/fbi/cde/test")
        url = resp.calls[0].request.url
        assert f"api_key={TEST_API_KEY}" in url

    @resp.activate
    def test_uppercase_api_key_not_present(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("crime/fbi/cde/test")
        url = resp.calls[0].request.url
        assert "API_KEY=" not in url

    @resp.activate
    def test_api_key_appears_exactly_once(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("crime/fbi/cde/test")
        url = resp.calls[0].request.url
        assert url.count("api_key=") == 1

    @resp.activate
    def test_question_mark_separator_when_no_existing_query_params(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("crime/fbi/cde/test")
        url = resp.calls[0].request.url
        assert "?api_key=" in url

    @resp.activate
    def test_ampersand_separator_when_query_params_already_present(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("crime/fbi/cde/test?type=counts")
        url = resp.calls[0].request.url
        assert "type=counts&api_key=" in url

    @resp.activate
    def test_leading_slash_in_url_path_does_not_produce_double_slash(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("/crime/fbi/cde/test")
        url = resp.calls[0].request.url
        assert "//crime" not in url

    @resp.activate
    def test_no_leading_slash_adds_one(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/crime/fbi/cde/test", json={}, match_querystring=False)
        client.get("crime/fbi/cde/test")
        url = resp.calls[0].request.url
        assert f"{TEST_BASE_URL}/crime/" in url


# ---------------------------------------------------------------------------
# Client.get — headers sent with request
# ---------------------------------------------------------------------------


class TestClientGetHeaders:
    @resp.activate
    def test_x_api_key_header_is_sent(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, match_querystring=False)
        client.get("test")
        headers = resp.calls[0].request.headers
        assert headers.get("X-Api-Key") == TEST_API_KEY

    @resp.activate
    def test_user_agent_header_is_sent(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, match_querystring=False)
        client.get("test")
        headers = resp.calls[0].request.headers
        assert headers.get("User-Agent") == "StatPack/1.0"

    @resp.activate
    def test_accept_header_is_sent(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, match_querystring=False)
        client.get("test")
        headers = resp.calls[0].request.headers
        assert headers.get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# Client.get — successful response handling
# ---------------------------------------------------------------------------


class TestClientGetSuccess:
    @resp.activate
    def test_200_returns_json_body(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={"result": "ok"}, status=200, match_querystring=False)
        result = client.get("test")
        assert result == {"result": "ok"}

    @resp.activate
    def test_200_increments_requests_counter(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=200, match_querystring=False)
        assert client.requests == 0
        client.get("test")
        assert client.requests == 1

    @resp.activate
    def test_200_multiple_calls_accumulate_request_count(self, client):
        for _ in range(3):
            resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=200, match_querystring=False)
        for _ in range(3):
            client.get("test")
        assert client.requests == 3

    @resp.activate
    def test_200_updates_last_request(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=200, match_querystring=False)
        assert client.last is None
        client.get("test")
        assert client.last is not None
        assert isinstance(client.last, Request)

    @resp.activate
    def test_200_last_request_url_contains_path(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/my/path", json={}, status=200, match_querystring=False)
        client.get("my/path")
        assert "my/path" in client.last.url

    @resp.activate
    def test_200_last_request_stores_headers(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=200, match_querystring=False)
        client.get("test")
        assert client.last.request_headers is not None

    @resp.activate
    def test_custom_success_code_accepted(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={"partial": True}, status=206, match_querystring=False)
        result = client.get("test", success_codes=[200, 206])
        assert result == {"partial": True}

    @resp.activate
    def test_returns_list_response(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json=[{"a": 1}, {"a": 2}], status=200, match_querystring=False)
        result = client.get("test")
        assert isinstance(result, list)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Client.get — error response handling
# ---------------------------------------------------------------------------


class TestClientGetErrors:
    @resp.activate
    def test_non_200_returns_default_return(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=404, match_querystring=False)
        result = client.get("test", default_return="fallback")
        assert result == "fallback"

    @resp.activate
    def test_non_200_returns_none_by_default(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=500, match_querystring=False)
        assert client.get("test") is None

    @resp.activate
    def test_non_200_still_increments_requests(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=404, match_querystring=False)
        client.get("test")
        assert client.requests == 1

    @resp.activate
    def test_non_200_appends_to_failed_requests(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=404, match_querystring=False)
        client.get("test")
        assert len(client.failed_requests) == 1

    @resp.activate
    def test_failed_request_stores_status_code(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=403, match_querystring=False)
        client.get("test")
        assert client.failed_requests[0].status_code == 403

    @resp.activate
    def test_429_sets_limited_true(self, client):
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/test",
            json={},
            status=429,
            headers={"X-RateLimit-Limit": "1000", "X-RateLimit-Remaining": "0", "Retry-After": "3600"},
            match_querystring=False,
        )
        client.get("test")
        assert client.limited is True

    @resp.activate
    def test_429_captures_limit_remaining(self, client):
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/test",
            json={},
            status=429,
            headers={"X-RateLimit-Limit": "1000", "X-RateLimit-Remaining": "5", "Retry-After": "3600"},
            match_querystring=False,
        )
        client.get("test")
        assert client.limit_remaining == "5"

    @resp.activate
    def test_429_captures_retry_after(self, client):
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/test",
            json={},
            status=429,
            headers={"X-RateLimit-Limit": "1000", "X-RateLimit-Remaining": "0", "Retry-After": "3600"},
            match_querystring=False,
        )
        client.get("test")
        assert client.limit_reset == "3600"

    @resp.activate
    def test_429_missing_retry_after_sets_none(self, client):
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/test",
            json={},
            status=429,
            headers={"X-RateLimit-Limit": "1000", "X-RateLimit-Remaining": "0"},
            match_querystring=False,
        )
        client.get("test")
        assert client.limit_reset is None

    @resp.activate
    def test_404_does_not_set_limited(self, client):
        resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=404, match_querystring=False)
        client.get("test")
        assert client.limited is False

    @resp.activate
    def test_multiple_failures_all_appended(self, client):
        for _ in range(3):
            resp.add(resp.GET, f"{TEST_BASE_URL}/test", json={}, status=500, match_querystring=False)
        for _ in range(3):
            client.get("test")
        assert len(client.failed_requests) == 3


# ---------------------------------------------------------------------------
# Client.get_agencies_by_territory
# ---------------------------------------------------------------------------

_AGENCY_PAYLOAD = {
    "New York": [
        {"ori": "NY0010100", "agency_name": "NYPD", "state_abbr": "NY"},
        {"ori": "NY0020100", "agency_name": "Albany PD", "state_abbr": "NY"},
    ]
}


class TestGetAgenciesByTerritory:
    @resp.activate
    def test_returns_dataframe_by_default(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_agencies_by_territory(territory="NY")
        assert isinstance(result, pd.DataFrame)

    @resp.activate
    def test_dataframe_row_count_matches_agencies(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_agencies_by_territory(territory="NY")
        assert len(result) == 2

    @resp.activate
    def test_returns_list_when_raw(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_agencies_by_territory(territory="NY", raw=True)
        assert isinstance(result, list)
        assert len(result) == 2

    @resp.activate
    def test_resolves_territory_by_abbr(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        client.get_agencies_by_territory(territory="NY")
        client.data.get_territory_by_abbr.assert_called_once_with("NY")

    @resp.activate
    def test_falls_back_to_name_lookup_when_abbr_fails(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = None
        client.data.get_territory_by_name.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        client.get_agencies_by_territory(territory="New York")
        client.data.get_territory_by_name.assert_called_once_with("New York")

    @resp.activate
    def test_url_does_not_contain_duplicate_api_key(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        client.get_agencies_by_territory(territory="NY")
        url = resp.calls[0].request.url
        assert url.count("api_key=") == 1
        assert "API_KEY=" not in url

    @resp.activate
    def test_all_territories_iterates_each(self, client, ny_territory, ca_territory):
        client.data = MagicMock()
        client.data = MagicMock()
        client.data.us_territories = [ny_territory, ca_territory]
        for abbr, payload in (("NY", {"NY Location": [{"ori": "NY001"}]}), ("CA", {"CA Location": [{"ori": "CA001"}]})):
            resp.add(
                resp.GET,
                f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/{abbr}",
                json=payload,
                match_querystring=False,
            )
        result = client.get_agencies_by_territory()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @resp.activate
    def test_all_territories_raw_returns_list(self, client, ny_territory, ca_territory):
        client.data = MagicMock()
        client.data = MagicMock()
        client.data.us_territories = [ny_territory, ca_territory]
        for abbr, payload in (("NY", {"NY Location": [{"ori": "NY001"}]}), ("CA", {"CA Location": [{"ori": "CA001"}]})):
            resp.add(
                resp.GET,
                f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/{abbr}",
                json=payload,
                match_querystring=False,
            )
        result = client.get_agencies_by_territory(raw=True)
        assert isinstance(result, list)

    @resp.activate
    def test_all_territories_skips_failed_responses(self, client, ny_territory, ca_territory):
        client.data = MagicMock()
        client.data = MagicMock()
        client.data.us_territories = [ny_territory, ca_territory]
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json={"NY Location": [{"ori": "NY001"}]},
            match_querystring=False,
        )
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/CA",
            status=500,
            json={},
            match_querystring=False,
        )
        result = client.get_agencies_by_territory(raw=True)
        assert len(result) == 1

    @resp.activate
    def test_url_contains_territory_abbreviation(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/agency/byStateAbbr/NY",
            json=_AGENCY_PAYLOAD,
            match_querystring=False,
        )
        client.get_agencies_by_territory(territory="NY")
        url = resp.calls[0].request.url
        assert "/byStateAbbr/NY" in url


# ---------------------------------------------------------------------------
# Client.get_arrest_counts_by_state
# ---------------------------------------------------------------------------

_ARREST_COUNTS_PAYLOAD = {
    "rates": {
        "New York Arrests": {"01-2020": 190.36, "02-2020": 172.0},
        "United States Arrests": {"01-2020": 175.61, "02-2020": 167.75},
    },
    "actuals": {"New York Arrests": {"01-2020": 27942, "02-2020": 25288}},
    "populations": {
        "population": {
            "New York": {"01-2020": 20002427, "02-2020": 20002427},
            "United States": {"01-2020": 345206793, "02-2020": 345206793},
        },
        "participated_population": {
            "New York": {"01-2020": 14678214, "02-2020": 14702062},
            "United States": {"01-2020": 314995268, "02-2020": 313004395},
        },
    },
}


class TestGetArrestCountsByState:
    @resp.activate
    def test_returns_dataframe_by_default(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_counts_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert isinstance(result, pd.DataFrame)

    @resp.activate
    def test_returns_list_when_raw(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_counts_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020", raw=True
        )
        assert isinstance(result, list)

    @resp.activate
    def test_url_uses_type_counts(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_counts_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        url = resp.calls[0].request.url
        assert "type=counts" in url

    @resp.activate
    def test_url_includes_from_date(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_counts_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        assert "from=01-2020" in resp.calls[0].request.url

    @resp.activate
    def test_url_includes_to_date(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_counts_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        assert "to=02-2020" in resp.calls[0].request.url

    @resp.activate
    def test_url_includes_offense_code(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/11",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_counts_by_state(territory="NY", offense_code="11", start_date="01-2020", end_date="02-2020")
        assert "/11?" in resp.calls[0].request.url

    @resp.activate
    def test_url_does_not_contain_duplicate_api_key(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_counts_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        url = resp.calls[0].request.url
        assert url.count("api_key=") == 1
        assert "API_KEY=" not in url

    @resp.activate
    def test_dataframe_has_expected_columns(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_counts_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        expected = {
            "date",
            "territory",
            "us",
            "territory_rate",
            "us_rate",
            "territory_total",
            "territory_population",
            "us_population",
            "territory_participated_population",
            "us_participated_population",
        }
        assert expected.issubset(set(result.columns))

    @resp.activate
    def test_dataframe_row_count_matches_date_union(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_counts_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert len(result) == 2

    @resp.activate
    def test_dataframe_dates_are_sorted(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_counts_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        dates = result["date"].tolist()
        assert dates == sorted(dates)

    @resp.activate
    def test_dataframe_territory_column_is_territory_name(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_COUNTS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_counts_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert all(result["territory"] == "New York")

    def test_no_territory_returns_empty_dataframe(self, client):
        result = client.get_arrest_counts_by_state()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_no_territory_raw_returns_empty_list(self, client):
        result = client.get_arrest_counts_by_state(raw=True)
        assert result == []


# ---------------------------------------------------------------------------
# Client.get_arrest_totals_by_state
# ---------------------------------------------------------------------------

_ARREST_TOTALS_PAYLOAD = {
    "male": {"Murder": 100, "Robbery": 200},
    "female": {"Murder": 50, "Robbery": 80},
    "cde_properties": {"max_data_date": "2020-12"},
}


class TestGetArrestTotalsByState:
    @resp.activate
    def test_returns_dataframe_by_default(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert isinstance(result, pd.DataFrame)

    @resp.activate
    def test_returns_list_when_raw(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020", raw=True
        )
        assert isinstance(result, list)

    @resp.activate
    def test_url_uses_type_totals(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_totals_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        assert "type=totals" in resp.calls[0].request.url

    @resp.activate
    def test_url_includes_date_range(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_totals_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        url = resp.calls[0].request.url
        assert "from=01-2020" in url
        assert "to=02-2020" in url

    @resp.activate
    def test_url_does_not_contain_duplicate_api_key(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_totals_by_state(territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020")
        url = resp.calls[0].request.url
        assert url.count("api_key=") == 1
        assert "API_KEY=" not in url

    @resp.activate
    def test_cde_properties_excluded_from_columns(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert not any("cde_properties" in col for col in result.columns)

    @resp.activate
    def test_dataframe_includes_territory_column(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert "territory" in result.columns
        assert result["territory"].iloc[0] == "New York"

    @resp.activate
    def test_dataframe_includes_start_and_end_date_columns(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert "start_date" in result.columns
        assert "end_date" in result.columns

    @resp.activate
    def test_columns_are_prefixed_dot_notation(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        prefixed = [col for col in result.columns if "." in col]
        assert len(prefixed) > 0

    @resp.activate
    def test_column_names_are_lowercased(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        for col in result.columns:
            assert col == col.lower(), f"Column '{col}' is not lowercase"

    @resp.activate
    def test_single_row_returned_for_single_territory(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_totals_by_state(
            territory="NY", offense_code="all", start_date="01-2020", end_date="02-2020"
        )
        assert len(result) == 1

    def test_no_territory_returns_empty_dataframe(self, client):
        result = client.get_arrest_totals_by_state()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_no_territory_raw_returns_empty_list(self, client):
        result = client.get_arrest_totals_by_state(raw=True)
        assert result == []
