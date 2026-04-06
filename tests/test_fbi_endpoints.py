"""Wave-1 endpoint tests using the ``responses`` library for HTTP mocking
and ``pytest-mock`` (mocker) for all other patching.
"""
import pandas as pd
import responses as resp


# ---------------------------------------------------------------------------
# get_cde_expanded_homicide_counts_by_state
# ---------------------------------------------------------------------------

@resp.activate
def test_get_cde_expanded_homicide_counts_by_state_raw_returns_records(fbi_main):
    resp.add(resp.GET, url="https://example.test/crime/fbi/cde/shr/state/NY",
             json={"totals": {"Homicide Count": 10}}, match_querystring=False)

    result = fbi_main.get_cde_expanded_homicide_counts_by_state(
        state_abbr="NY",
        start_date="01-2025",
        end_date="02-2025",
        raw=True,
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["state_abbr"] == "NY"
    assert result[0]["requested"]["start_date"] == "01-2025"


@resp.activate
def test_get_cde_expanded_homicide_counts_by_state_dataframe_normalizes_columns(fbi_main):
    resp.add(resp.GET, url="https://example.test/crime/fbi/cde/shr/state/NY",
             json={"totals": {"Homicide Count": 10}}, match_querystring=False)

    result = fbi_main.get_cde_expanded_homicide_counts_by_state(
        state_abbr="NY",
        start_date="01-2025",
        end_date="02-2025",
    )

    assert isinstance(result, pd.DataFrame)
    assert "requested.state_abbr" in result.columns
    assert "totals.homicide_count" in result.columns


def test_get_cde_expanded_homicide_counts_by_state_calls_sleep_for_all_states(
    fbi_main, mocker, mocked_responses
):
    mocker.patch.object(fbi_main, "us_territory_mapping",
                        {"NY": {"name": "New York"}, "CA": {"name": "California"}})
    sleep_spy = mocker.patch.object(fbi_main.time, "sleep")

    for abbr in ("NY", "CA"):
        mocked_responses.add(resp.GET,
                             url=f"https://example.test/crime/fbi/cde/shr/state/{abbr}",
                             json={"totals": {"Homicide Count": 1}},
                             match_querystring=False)

    fbi_main.get_cde_expanded_homicide_counts_by_state(state_abbr=None, raw=True)

    assert sleep_spy.call_count == 2


# ---------------------------------------------------------------------------
# get_cde_summarized_by_state
# ---------------------------------------------------------------------------

_SUMMARIZED_EMPTY_PAYLOAD = {
    "offenses": {"rates": {}, "actuals": {}},
    "tooltips": {"Percent of Population Coverage": {}, "leftYAxisHeaders": {}},
    "populations": {"population": {}, "participated_population": {}},
    "cde_properties": {"max_data_date": {"UCR": "2025-02"}, "last_refresh_date": {"UCR": "2026-01"}},
}


@resp.activate
def test_get_cde_summarized_by_state_raw_returns_payload_list(fbi_main):
    resp.add(resp.GET, url="https://example.test/crime/fbi/cde/summarized/state/NY/V",
             json=_SUMMARIZED_EMPTY_PAYLOAD, match_querystring=False)

    result = fbi_main.get_cde_summarized_by_state(
        state_abbr="NY",
        offense_code="V",
        start_date="01-2025",
        end_date="02-2025",
        raw=True,
    )

    assert isinstance(result, list)
    assert result == [_SUMMARIZED_EMPTY_PAYLOAD]


@resp.activate
def test_get_cde_summarized_by_state_dataframe_contains_expected_rows(fbi_main):
    payload = {
        "offenses": {
            "rates": {"Rate": {"2025-02": 2.0, "2025-01": 1.0}},
            "actuals": {"Actual": {"2025-01": 10, "2025-02": 20}},
        },
        "tooltips": {
            "Percent of Population Coverage": {"Coverage": {"2025-01": 80, "2025-02": 81}},
            "leftYAxisHeaders": {"yAxisHeaderRates": "Rates", "yAxisHeaderActual": "Actual"},
        },
        "populations": {
            "population": {"Population": {"2025-01": 1000, "2025-02": 1001}},
            "participated_population": {"Participated": {"2025-01": 900, "2025-02": 901}},
        },
        "cde_properties": {
            "max_data_date": {"UCR": "2025-02"},
            "last_refresh_date": {"UCR": "2026-01"},
        },
    }

    resp.add(resp.GET, url="https://example.test/crime/fbi/cde/summarized/state/NY/V",
             json=payload, match_querystring=False)

    result = fbi_main.get_cde_summarized_by_state(
        state_abbr="NY",
        offense_code="V",
        start_date="01-2025",
        end_date="02-2025",
    )

    assert isinstance(result, pd.DataFrame)
    assert list(result["date"]) == ["2025-01", "2025-02"]
    assert "offenses.rates.rate" in result.columns


# ---------------------------------------------------------------------------
# get_cde_nibrs_totals_by_state
# ---------------------------------------------------------------------------

@resp.activate
def test_get_cde_nibrs_totals_by_state_raw_returns_records(fbi_main):
    resp.add(resp.GET, url="https://example.test/crime/fbi/cde/nibrs/state/NY/13A",
             json={"actual": 7}, match_querystring=False)

    result = fbi_main.get_cde_nibrs_totals_by_state(
        state_abbr="NY",
        nibrs_code="13A",
        start_date="01-2025",
        end_date="02-2025",
        raw=True,
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["nibrs_code"] == "13A"
    assert result[0]["crime"] == "Aggravated Assault"


@resp.activate
def test_get_cde_nibrs_totals_by_state_dataframe_uses_ordered_columns(fbi_main):
    resp.add(resp.GET, url="https://example.test/crime/fbi/cde/nibrs/state/NY/13A",
             json={"actual": 7}, match_querystring=False)

    result = fbi_main.get_cde_nibrs_totals_by_state(
        state_abbr="NY",
        nibrs_code="13A",
        start_date="01-2025",
        end_date="02-2025",
        raw=False,
    )

    assert isinstance(result, pd.DataFrame)
    for col in ["state_abbr", "state_name", "nibrs_code", "crime", "start_date", "end_date"]:
        assert col in result.columns


# ---------------------------------------------------------------------------
# get_cde_reporting_agencies
# ---------------------------------------------------------------------------

def test_get_cde_reporting_agencies_flattens_only_dict_items(fbi_main, mocker, mocked_responses):
    mocker.patch.object(fbi_main, "us_territory_mapping", {"NY": {"name": "New York"}})
    mocked_responses.add(
        resp.GET,
        url="https://example.test/crime/fbi/cde/agency/byStateAbbr/NY",
        json={
            "ANYORI": [{"ori": "A", "agency_name": "Alpha PD"}, "not-a-dict"],
            "something_else": "ignored",
        },
        match_querystring=False,
    )

    result = fbi_main.get_cde_reporting_agencies()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["ori"] == "A"
