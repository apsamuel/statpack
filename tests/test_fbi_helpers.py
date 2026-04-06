import pandas as pd


def test_normalize_wide_key_basic(fbi_main):
    assert fbi_main._normalize_wide_key("Percent of Population Coverage") == "percent_of_population_coverage"
    assert fbi_main._normalize_wide_key("Arrests/Rate-By Month") == "arrests_rate_by_month"


def test_records_to_wide_dataframe_empty_returns_empty_df(fbi_main):
    result = fbi_main._records_to_wide_dataframe([])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_records_to_wide_dataframe_orders_sorts_and_normalizes_columns(fbi_main):
    records = [
        {
            "requested": {"state_abbr": "CA", "state_name": "California"},
            "counts": {"Total Arrests": 2},
        },
        {
            "requested": {"state_abbr": "NY", "state_name": "New York"},
            "counts": {"Total Arrests": 1},
        },
    ]

    result = fbi_main._records_to_wide_dataframe(
        records=records,
        ordered_columns=["requested.state_abbr", "requested.state_name"],
        sort_by=["requested.state_abbr"],
        normalize_columns=True,
    )

    assert list(result["requested.state_abbr"]) == ["CA", "NY"]
    assert "counts.total_arrests" in result.columns


def test_finalize_records_raw_returns_list(fbi_main):
    records = [{"x": 1}, {"x": 2}]
    result = fbi_main._finalize_records(records=records, raw=True)
    assert result == records


def test_finalize_records_dataframe_returns_df(fbi_main):
    records = [{"x": 2}, {"x": 1}]
    result = fbi_main._finalize_records(records=records, raw=False, sort_by=["x"])
    assert isinstance(result, pd.DataFrame)
    assert list(result["x"]) == [1, 2]
