"""Tests for the per-capita-by-race analysis feature.

Covers:
  - analysis.taxonomy crosswalks (FBI race + ACS variable -> canonical)
  - Client.get_arrest_race_breakdown_by_state (totals endpoint, race extraction)
  - census.main.get_census_population_by_race (long-format reshape)
  - analysis.per_capita.per_capita_by_race (join + rate computation)
  - fbi CLI `per-capita-by-race` subcommand dispatch

HTTP and cross-source calls are mocked; no real network access occurs.
"""

import importlib
import os

# Ensure every source package can be imported even without real env vars.
# The top-level ``statpack`` package eagerly imports fbi, census, and fred,
# each of which raises at import time if its credentials are missing.
os.environ.setdefault("GOV_API_BASE_URL", "https://example.test")
os.environ.setdefault("GOV_API_KEY", "test-api-key")
os.environ.setdefault("CENSUS_API_BASE_URL", "https://census.example.test")
os.environ.setdefault("CENSUS_API_KEY", "census-test-key")
os.environ.setdefault("FRED_API_BASE_URL", "https://fred.example.test")
os.environ.setdefault("FRED_API_KEY", "fred-test-key")

import pandas as pd
import pytest
import responses as resp
from unittest.mock import MagicMock

from statpack.data.analysis import taxonomy
from statpack.data.analysis.per_capita import per_capita_by_race
from statpack.data.sources.fbi.client import Client
from statpack.data.sources.fbi.models import USTerritory

TEST_BASE_URL = "https://example.test"
TEST_API_KEY = "test-api-key"


# ---------------------------------------------------------------------------
# taxonomy crosswalks
# ---------------------------------------------------------------------------


class TestTaxonomy:
    def test_fbi_race_maps_to_canonical(self):
        assert taxonomy.canonical_from_fbi_race("Black or African American") == taxonomy.BLACK
        assert taxonomy.canonical_from_fbi_race("white") == taxonomy.WHITE

    def test_fbi_race_is_case_insensitive(self):
        assert taxonomy.canonical_from_fbi_race("  ASIAN ") == taxonomy.ASIAN

    def test_fbi_aggregate_buckets_are_unmapped(self):
        assert taxonomy.canonical_from_fbi_race("Unknown") is None
        assert taxonomy.canonical_from_fbi_race("Multiple") is None
        assert taxonomy.canonical_from_fbi_race("Not Specified") is None
        assert taxonomy.canonical_from_fbi_race("Asian, Native Hawaiian, or Other Pacific Islander") is None

    def test_acs_variable_maps_to_canonical(self):
        assert taxonomy.canonical_from_acs_variable("B02001_003E") == taxonomy.BLACK
        assert taxonomy.canonical_from_acs_variable("B03003_003E") == taxonomy.HISPANIC

    def test_unknown_acs_variable_is_unmapped(self):
        assert taxonomy.canonical_from_acs_variable("B99999_999E") is None

    def test_hispanic_is_ethnicity_not_race(self):
        assert taxonomy.HISPANIC not in taxonomy.CANONICAL_RACES
        assert taxonomy.HISPANIC in taxonomy.CANONICAL_ETHNICITIES


# ---------------------------------------------------------------------------
# Client.get_arrest_race_breakdown_by_state
# ---------------------------------------------------------------------------

_ARREST_TOTALS_PAYLOAD = {
    "Arrestee Sex": {"Male": 716, "Female": 66},
    "Arrestee Race": {
        "White": 516,
        "Black or African American": 216,
        "Asian": 27,
        "American Indian or Alaska Native": 1,
        "Native Hawaiian or Other Pacific Islander": 4,
        "Unknown": 18,
    },
    "cde_properties": {"max_data_date": {"UCR": "03/2026"}},
}


@pytest.fixture
def client():
    return Client(api_base_url=TEST_BASE_URL, api_key=TEST_API_KEY)


@pytest.fixture
def ny_territory():
    return USTerritory(name="New York", abbreviation="NY")


class TestGetArrestRaceBreakdownByState:
    @resp.activate
    def test_uses_type_totals_endpoint(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        client.get_arrest_race_breakdown_by_state(
            territory="NY", offense_code="all", start_date="01-2024", end_date="12-2024"
        )
        assert "type=totals" in resp.calls[0].request.url

    @resp.activate
    def test_extracts_race_records(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json=_ARREST_TOTALS_PAYLOAD,
            match_querystring=False,
        )
        result = client.get_arrest_race_breakdown_by_state(
            territory="NY", offense_code="all", start_date="01-2024", end_date="12-2024", raw=True
        )
        by_race = {r["race"]: r["count"] for r in result}
        assert by_race["White"] == 516
        assert by_race["Black or African American"] == 216
        assert all(r["territory"] == "New York" for r in result)

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
        result = client.get_arrest_race_breakdown_by_state(
            territory="NY", offense_code="all", start_date="01-2024", end_date="12-2024"
        )
        assert isinstance(result, pd.DataFrame)
        assert set(result.columns) == {"territory", "race", "count"}

    @resp.activate
    def test_missing_table_raises(self, client, ny_territory):
        client.data = MagicMock()
        client.data.get_territory_by_abbr.return_value = ny_territory
        resp.add(
            resp.GET,
            f"{TEST_BASE_URL}/crime/fbi/cde/arrest/state/NY/all",
            json={"Arrestee Sex": {"Male": 1}, "cde_properties": {}},
            match_querystring=False,
        )
        with pytest.raises(ValueError, match="not found"):
            client.get_arrest_race_breakdown_by_state(
                territory="NY", offense_code="all", start_date="01-2024", end_date="12-2024"
            )

    def test_no_territory_returns_empty(self, client):
        assert client.get_arrest_race_breakdown_by_state(raw=True) == []
        assert client.get_arrest_race_breakdown_by_state().empty


# ---------------------------------------------------------------------------
# census.get_census_population_by_race
# ---------------------------------------------------------------------------


class TestGetCensusPopulationByRace:
    def test_reshapes_to_long_format(self, monkeypatch):
        import statpack.data.sources.census.main as census_main

        fake_df = pd.DataFrame(
            [{"NAME": "New York", "B02001_002E": "1000000", "B02001_003E": "500000", "B03003_003E": "300000"}]
        )
        monkeypatch.setattr(census_main, "get_census_acs_detailed_by_state", lambda **kwargs: fake_df)

        records = census_main.get_census_population_by_race(states=["NY"], year=2024, raw=True)
        by_var = {r["variable"]: r["population"] for r in records}
        assert by_var["B02001_002E"] == 1000000
        assert by_var["B02001_003E"] == 500000
        assert all(r["state"] == "New York" for r in records)

    def test_returns_dataframe_by_default(self, monkeypatch):
        import statpack.data.sources.census.main as census_main

        fake_df = pd.DataFrame([{"NAME": "New York", "B02001_002E": "1000000"}])
        monkeypatch.setattr(census_main, "get_census_acs_detailed_by_state", lambda **kwargs: fake_df)
        result = census_main.get_census_population_by_race(states=["NY"], raw=False)
        assert isinstance(result, pd.DataFrame)
        assert "population" in result.columns


# ---------------------------------------------------------------------------
# analysis.per_capita_by_race
# ---------------------------------------------------------------------------


class TestPerCapitaByRace:
    def _patch_sources(self, monkeypatch, arrests, population):
        import statpack.data.sources.census as census_pkg
        import statpack.data.sources.fbi as fbi_pkg

        fake_client = MagicMock()
        fake_client.get_arrest_race_breakdown_by_state.return_value = arrests
        monkeypatch.setattr(fbi_pkg, "Client", MagicMock(return_value=fake_client))
        monkeypatch.setattr(census_pkg, "get_census_population_by_race", lambda **kwargs: population)

    def test_computes_rate_per_100k(self, monkeypatch):
        arrests = [
            {"territory": "New York", "race": "White", "count": 100},
            {"territory": "New York", "race": "Black or African American", "count": 90},
            {"territory": "New York", "race": "Asian", "count": 5},
            {"territory": "New York", "race": "Unknown", "count": 999},
        ]
        population = [
            {"state": "New York", "variable": "B02001_002E", "population": 1_000_000},
            {"state": "New York", "variable": "B02001_003E", "population": 300_000},
            {"state": "New York", "variable": "B02001_005E", "population": 100_000},
        ]
        self._patch_sources(monkeypatch, arrests, population)

        rows = per_capita_by_race(state="NY", start_date="01-2024", end_date="12-2024", year=2024, raw=True)
        by_race = {r["race"]: r for r in rows}
        assert by_race[taxonomy.WHITE]["per_100000"] == 10.0
        assert by_race[taxonomy.BLACK]["per_100000"] == 30.0
        assert by_race[taxonomy.ASIAN]["per_100000"] == 5.0

    def test_missing_population_yields_none_rate(self, monkeypatch):
        arrests = [{"territory": "New York", "race": "White", "count": 100}]
        population = []  # no population data
        self._patch_sources(monkeypatch, arrests, population)

        rows = per_capita_by_race(state="NY", raw=True)
        white = next(r for r in rows if r["race"] == taxonomy.WHITE)
        assert white["arrests"] == 100
        assert white["population"] is None
        assert white["per_100000"] is None

    def test_unmapped_fbi_races_are_ignored(self, monkeypatch):
        arrests = [
            {"territory": "New York", "race": "Multiple", "count": 500},
            {"territory": "New York", "race": "White", "count": 100},
        ]
        population = [{"state": "New York", "variable": "B02001_002E", "population": 1_000_000}]
        self._patch_sources(monkeypatch, arrests, population)

        rows = per_capita_by_race(state="NY", raw=True)
        white = next(r for r in rows if r["race"] == taxonomy.WHITE)
        assert white["arrests"] == 100  # "Multiple" bucket dropped

    def test_only_five_omb_races_reported(self, monkeypatch):
        self._patch_sources(monkeypatch, [], [])
        rows = per_capita_by_race(state="NY", raw=True)
        assert [r["race"] for r in rows] == taxonomy.CANONICAL_RACES

    def test_returns_dataframe_by_default(self, monkeypatch):
        self._patch_sources(monkeypatch, [], [])
        result = per_capita_by_race(state="NY")
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


class TestPerCapitaByRaceCLI:
    def test_command_invokes_analysis(self, monkeypatch):
        from click.testing import CliRunner

        import statpack.data.analysis as analysis_pkg
        from statpack.data.sources.fbi.cli import fbi

        captured = {}

        def fake_analysis(**kwargs):
            captured.update(kwargs)
            return pd.DataFrame([{"state": "New York", "race": "White", "per_100000": 10.0}])

        monkeypatch.setattr(analysis_pkg, "per_capita_by_race", fake_analysis)

        runner = CliRunner()
        result = runner.invoke(
            fbi,
            [
                "per-capita-by-race",
                "--state",
                "NY",
                "--offense-code",
                "all",
                "--start-date",
                "01-2024",
                "--end-date",
                "12-2024",
                "--year",
                "2024",
                "--format",
                "csv",
            ],
        )
        assert result.exit_code == 0, result.output
        assert captured["state"] == "NY"
        assert captured["year"] == 2024
        assert "White" in result.output

    def test_year_defaults_to_end_date_year(self, monkeypatch):
        from click.testing import CliRunner

        import statpack.data.analysis as analysis_pkg
        from statpack.data.sources.fbi.cli import fbi

        captured = {}

        def fake_analysis(**kwargs):
            captured.update(kwargs)
            return pd.DataFrame([{"state": "New York", "race": "White", "per_100000": 10.0}])

        monkeypatch.setattr(analysis_pkg, "per_capita_by_race", fake_analysis)

        runner = CliRunner()
        result = runner.invoke(
            fbi,
            [
                "per-capita-by-race",
                "--state",
                "NY",
                "--start-date",
                "01-2023",
                "--end-date",
                "12-2023",
                "--format",
                "csv",
            ],
        )
        assert result.exit_code == 0, result.output
        assert captured["year"] == 2023  # derived from --end-date, not the old 2024 default
        assert "using 2023" in result.output

    def test_multi_year_range_warns(self, monkeypatch):
        from click.testing import CliRunner

        import statpack.data.analysis as analysis_pkg
        from statpack.data.sources.fbi.cli import fbi

        def fake_analysis(**kwargs):
            return pd.DataFrame([{"state": "New York", "race": "White", "per_100000": 10.0}])

        monkeypatch.setattr(analysis_pkg, "per_capita_by_race", fake_analysis)

        runner = CliRunner()
        result = runner.invoke(
            fbi,
            [
                "per-capita-by-race",
                "--state",
                "NY",
                "--start-date",
                "01-2022",
                "--end-date",
                "12-2024",
                "--format",
                "csv",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "not annualized" in result.output

    def test_explicit_year_mismatch_warns(self, monkeypatch):
        from click.testing import CliRunner

        import statpack.data.analysis as analysis_pkg
        from statpack.data.sources.fbi.cli import fbi

        def fake_analysis(**kwargs):
            return pd.DataFrame([{"state": "New York", "race": "White", "per_100000": 10.0}])

        monkeypatch.setattr(analysis_pkg, "per_capita_by_race", fake_analysis)

        runner = CliRunner()
        result = runner.invoke(
            fbi,
            [
                "per-capita-by-race",
                "--state",
                "NY",
                "--start-date",
                "01-2023",
                "--end-date",
                "12-2023",
                "--year",
                "2020",
                "--format",
                "csv",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "does not match the arrest year" in result.output
