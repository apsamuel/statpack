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
        {"requested": {"state_abbr": "CA", "state_name": "California"}, "counts": {"Total Arrests": 2}},
        {"requested": {"state_abbr": "NY", "state_name": "New York"}, "counts": {"Total Arrests": 1}},
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


# ---------------------------------------------------------------------------
# Offense name -> code resolvers (namespace safety)
# ---------------------------------------------------------------------------


def _resolvers():
    from statpack.data.sources.fbi.models import get_fbi_code_from_offense_name, get_nibrs_code_from_offense_name

    return get_fbi_code_from_offense_name, get_nibrs_code_from_offense_name


def test_fbi_resolver_matches_full_name():
    fbi_resolve, _ = _resolvers()
    assert fbi_resolve("Aggravated Assault") == "50"
    assert fbi_resolve("Robbery") == "30"


def test_fbi_resolver_is_case_insensitive():
    fbi_resolve, _ = _resolvers()
    assert fbi_resolve("aggravated assault") == "50"
    assert fbi_resolve("  ROBBERY  ") == "30"


def test_fbi_resolver_matches_short_name():
    fbi_resolve, _ = _resolvers()
    # "Assault" is the short_name for Simple Assault (code 55).
    assert fbi_resolve("Assault") == "55"


def test_fbi_resolver_no_match_returns_none():
    fbi_resolve, _ = _resolvers()
    assert fbi_resolve("Not A Real Offense") is None


def test_nibrs_resolver_matches_full_name():
    _, nibrs_resolve = _resolvers()
    assert nibrs_resolve("Aggravated Assault") == "13A"
    assert nibrs_resolve("Robbery") == "120"


def test_nibrs_resolver_no_match_returns_none():
    _, nibrs_resolve = _resolvers()
    assert nibrs_resolve("Not A Real Offense") is None


def test_resolvers_use_separate_namespaces():
    """The same name must map to DIFFERENT codes in each namespace."""
    fbi_resolve, nibrs_resolve = _resolvers()
    fbi_code = fbi_resolve("Aggravated Assault")
    nibrs_code = nibrs_resolve("Aggravated Assault")
    assert fbi_code == "50"
    assert nibrs_code == "13A"
    assert fbi_code != nibrs_code
