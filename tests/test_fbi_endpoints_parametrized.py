"""Wave-2 parametrized tests for all get_cde_* public functions.

Covers:
- raw=True  → always returns list[dict]
- raw=False → always returns pd.DataFrame
- Error paths (HTTP 4xx → raise_for_status propagates)
- Edge cases (empty payloads, all-states branch, invalid table arg)

HTTP mocking: ``responses`` library (registered URLs only; unregistered calls
raise ConnectionError).  Object patching: ``mocker`` from pytest-mock.
"""
import pytest
import pandas as pd
import responses as resp


# ---------------------------------------------------------------------------
# get_cde_reporting_agencies
# ---------------------------------------------------------------------------


class TestGetCdeReportingAgencies:
    @resp.activate
    def test_raw_true_returns_list(self, fbi_main, mocker):
        mocker.patch.object(fbi_main, "us_territory_mapping", {"TX": {"name": "Texas"}})
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/agency/byStateAbbr/TX",
                 json={"TXORI": [{"ori": "TX001", "agency_name": "Austin PD"}]}, match_querystring=False)
        result = fbi_main.get_cde_reporting_agencies(raw=True)
        assert isinstance(result, list)
        assert result[0]["ori"] == "TX001"

    @resp.activate
    def test_raw_false_returns_dataframe(self, fbi_main, mocker):
        mocker.patch.object(fbi_main, "us_territory_mapping", {"TX": {"name": "Texas"}})
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/agency/byStateAbbr/TX",
                 json={"TXORI": [{"ori": "TX001", "agency_name": "Austin PD"}]}, match_querystring=False)
        result = fbi_main.get_cde_reporting_agencies(raw=False)
        assert isinstance(result, pd.DataFrame)
        assert "ori" in result.columns

    @resp.activate
    def test_empty_response_returns_empty_dataframe(self, fbi_main, mocker):
        mocker.patch.object(fbi_main, "us_territory_mapping", {"TX": {"name": "Texas"}})
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/agency/byStateAbbr/TX",
                 json={}, match_querystring=False)
        result = fbi_main.get_cde_reporting_agencies()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @resp.activate
    def test_non_list_values_are_skipped(self, fbi_main, mocker):
        mocker.patch.object(fbi_main, "us_territory_mapping", {"TX": {"name": "Texas"}})
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/agency/byStateAbbr/TX",
                 json={"TXORI": [{"ori": "TX001"}, "not-a-dict", 42], "meta": "ignored-string"},
                 match_querystring=False)
        result = fbi_main.get_cde_reporting_agencies(raw=True)
        assert len(result) == 1
        assert result[0]["ori"] == "TX001"


# ---------------------------------------------------------------------------
# get_cde_arrest_totals_by_state
# ---------------------------------------------------------------------------

ARREST_TOTALS_PAYLOAD = {
    "arrestee race": {"White": 100, "Black": 80},
    "cde_properties": {"max_data_date": {"UCR": "2025-02"}},
}


class TestGetCdeArrestTotalsByState:
    @resp.activate
    def test_raw_true_returns_list(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=ARREST_TOTALS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_state(
            state_abbr="NY",
            start_date="01-2025",
            end_date="12-2025",
            raw=True,
        )

        assert isinstance(result, list)
        assert len(result) == 2  # White + Black entries

    @resp.activate
    def test_raw_false_returns_dataframe(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=ARREST_TOTALS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_state(
            state_abbr="NY",
            start_date="01-2025",
            end_date="12-2025",
            raw=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    @resp.activate
    def test_invalid_table_raises_value_error(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=ARREST_TOTALS_PAYLOAD, match_querystring=False)
        with pytest.raises(ValueError, match="Table 'bad table' not found"):
            fbi_main.get_cde_arrest_totals_by_state(
                state_abbr="NY",
                start_date="01-2025",
                end_date="12-2025",
                table="bad table",
            )

    @resp.activate
    def test_custom_table_extracts_correct_rows(self, fbi_main):
        payload = {"arrestee age": {"Juvenile": 20, "Adult": 300}, "cde_properties": {}}
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=payload, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_state(
            state_abbr="NY",
            start_date="01-2025",
            end_date="12-2025",
            table="arrestee age",
            raw=True,
        )

        assert len(result) == 2
        assert all("arrestee age" in r for r in result)


# ---------------------------------------------------------------------------
# get_cde_arrest_counts_by_state
# ---------------------------------------------------------------------------

def _make_counts_payload(state_name: str) -> dict:
    return {
        "rates": {f"{state_name} Arrests": {"2025-01": 1.5, "2025-02": 1.7}},
        "actuals": {f"{state_name} Arrests": {"2025-01": 150, "2025-02": 170}},
        "populations": {"population": {state_name: {"2025-01": 10000, "2025-02": 10100}}},
    }


class TestGetCdeArrestCountsByState:
    @resp.activate
    def test_raw_true_returns_list(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=_make_counts_payload("New York"), match_querystring=False)
        result = fbi_main.get_cde_arrest_counts_by_state(
            state_abbr="NY",
            start_date="01-2025",
            end_date="02-2025",
            raw=True,
        )

        assert isinstance(result, list)
        assert len(result) == 2

    @resp.activate
    def test_raw_false_returns_indexed_dataframe(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=_make_counts_payload("New York"), match_querystring=False)
        result = fbi_main.get_cde_arrest_counts_by_state(
            state_abbr="NY",
            start_date="01-2025",
            end_date="02-2025",
            raw=False,
        )

        assert isinstance(result, pd.DataFrame)
        # index_cols=["Date", "State"] so they become the DataFrame index
        assert result.index.names == ["Date", "State"]

    @resp.activate
    def test_all_states_iterates_territory_mapping(self, fbi_main, mocker):
        mocker.patch.object(fbi_main, "us_territory_mapping",
                            {"NY": {"name": "New York"}, "CA": {"name": "California"}})
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=_make_counts_payload("New York"), match_querystring=False)
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/CA/all",
                 json=_make_counts_payload("California"), match_querystring=False)

        result = fbi_main.get_cde_arrest_counts_by_state(raw=True)

        assert len(result) == 4  # 2 states × 2 dates
        assert len(resp.calls) == 2

    @resp.activate
    def test_records_contain_expected_keys(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/state/NY/all",
                 json=_make_counts_payload("New York"), match_querystring=False)
        result = fbi_main.get_cde_arrest_counts_by_state(
            state_abbr="NY",
            start_date="01-2025",
            end_date="02-2025",
            raw=True,
        )

        for record in result:
            assert set(record.keys()) == {"Date", "State", "Offense", "Arrest Rate", "Arrest Total", "Population"}


# ---------------------------------------------------------------------------
# get_cde_arrest_totals_by_origin
# ---------------------------------------------------------------------------

ORIGIN_TOTALS_PAYLOAD = {
    "rates": {"2025-01": 1.2, "2025-02": 1.4},
    "actuals": {"2025-01": 12, "2025-02": 14},
}


class TestGetCdeArrestTotalsByOrigin:
    @resp.activate
    def test_raw_true_returns_list(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json=ORIGIN_TOTALS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_origin(
            origin_code="AL0430200",
            offense_code="all",
            start_date="01-2025",
            end_date="02-2025",
            raw=True,
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["ori_code"] == "AL0430200"

    @resp.activate
    def test_raw_false_returns_sorted_dataframe(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json=ORIGIN_TOTALS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_origin(
            origin_code="AL0430200",
            offense_code="all",
            start_date="01-2025",
            end_date="02-2025",
            raw=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert list(result["date"]) == ["2025-01", "2025-02"]

    @resp.activate
    def test_empty_payload_returns_empty_dataframe(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json={"rates": {}, "actuals": {}}, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_origin(raw=False)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @resp.activate
    def test_records_contain_rate_and_total_fields(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json=ORIGIN_TOTALS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_totals_by_origin(raw=True)
        for record in result:
            assert "arrest_rate" in record
            assert "arrest_total" in record
            assert "population" not in record  # totals endpoint has no population


# ---------------------------------------------------------------------------
# get_cde_arrest_counts_by_origin
# ---------------------------------------------------------------------------

ORIGIN_COUNTS_PAYLOAD = {
    "rates": {"2025-01": 0.9, "2025-02": 1.1},
    "actuals": {"2025-01": 9, "2025-02": 11},
    "populations": {"population": {"2025-01": 10000, "2025-02": 10100}},
}


class TestGetCdeArrestCountsByOrigin:
    @resp.activate
    def test_raw_true_returns_list_with_population(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json=ORIGIN_COUNTS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_counts_by_origin(
            origin_code="AL0430200",
            offense_code="all",
            start_date="01-2025",
            end_date="02-2025",
            raw=True,
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["population"] == 10000

    @resp.activate
    def test_raw_false_returns_sorted_dataframe(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json=ORIGIN_COUNTS_PAYLOAD, match_querystring=False)
        result = fbi_main.get_cde_arrest_counts_by_origin(
            origin_code="AL0430200",
            offense_code="all",
            start_date="01-2025",
            end_date="02-2025",
            raw=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert list(result["date"]) == ["2025-01", "2025-02"]
        assert "population" in result.columns

    @resp.activate
    def test_missing_population_key_falls_back_to_none(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 json={"rates": {"2025-01": 1.0}, "actuals": {"2025-01": 10}, "populations": {}},
                 match_querystring=False)
        result = fbi_main.get_cde_arrest_counts_by_origin(raw=True)
        assert result[0]["population"] is None

    @resp.activate
    def test_http_error_propagates(self, fbi_main):
        resp.add(resp.GET, url="https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
                 status=403, match_querystring=False)
        with pytest.raises(Exception):
            fbi_main.get_cde_arrest_counts_by_origin(raw=True)


# ---------------------------------------------------------------------------
# Parametrized raw=True/False smoke test across all functions
# ---------------------------------------------------------------------------

_PARAM_CASES = [
    (
        "get_cde_reporting_agencies", {},
        "https://example.test/crime/fbi/cde/agency/byStateAbbr/NY",
        {"NYORI": [{"ori": "NY001", "agency_name": "NYPD"}]},
    ),
    (
        "get_cde_arrest_totals_by_state",
        {"state_abbr": "NY", "start_date": "01-2025", "end_date": "02-2025"},
        "https://example.test/crime/fbi/cde/arrest/state/NY/all",
        {"arrestee race": {"White": 5, "Black": 3}, "cde_properties": {}},
    ),
    (
        "get_cde_arrest_totals_by_origin",
        {"origin_code": "AL0430200", "offense_code": "all", "start_date": "01-2025", "end_date": "02-2025"},
        "https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
        {"rates": {"2025-01": 1.0}, "actuals": {"2025-01": 10}},
    ),
    (
        "get_cde_arrest_counts_by_origin",
        {"origin_code": "AL0430200", "offense_code": "all", "start_date": "01-2025", "end_date": "02-2025"},
        "https://example.test/crime/fbi/cde/arrest/agency/AL0430200/all",
        {"rates": {"2025-01": 1.0}, "actuals": {"2025-01": 10}, "populations": {"population": {"2025-01": 500}}},
    ),
    (
        "get_cde_nibrs_totals_by_state",
        {"state_abbr": "NY", "nibrs_code": "13A", "start_date": "01-2025", "end_date": "02-2025"},
        "https://example.test/crime/fbi/cde/nibrs/state/NY/13A",
        {"actual": 5, "rate": 0.3},
    ),
    (
        "get_cde_expanded_homicide_counts_by_state",
        {"state_abbr": "NY", "start_date": "01-2025", "end_date": "02-2025"},
        "https://example.test/crime/fbi/cde/shr/state/NY",
        {"totals": {"Homicide Count": 3}},
    ),
]


@pytest.mark.parametrize("fn_name,kwargs,url,http_payload", _PARAM_CASES)
@resp.activate
def test_raw_true_always_returns_list(fn_name, kwargs, url, http_payload, fbi_main, mocker):
    mocker.patch.object(fbi_main, "us_territory_mapping", {"NY": {"name": "New York"}})
    resp.add(resp.GET, url=url, json=http_payload, match_querystring=False)
    fn = getattr(fbi_main, fn_name)
    result = fn(**kwargs, raw=True)
    assert isinstance(result, list), f"{fn_name} with raw=True should return list, got {type(result)}"


@pytest.mark.parametrize("fn_name,kwargs,url,http_payload", _PARAM_CASES)
@resp.activate
def test_raw_false_always_returns_dataframe(fn_name, kwargs, url, http_payload, fbi_main, mocker):
    mocker.patch.object(fbi_main, "us_territory_mapping", {"NY": {"name": "New York"}})
    resp.add(resp.GET, url=url, json=http_payload, match_querystring=False)
    fn = getattr(fbi_main, fn_name)
    result = fn(**kwargs, raw=False)
    assert isinstance(result, pd.DataFrame), f"{fn_name} with raw=False should return DataFrame, got {type(result)}"
