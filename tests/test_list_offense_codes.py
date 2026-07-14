"""Tests for the offense-code listing feature.

Covers:
  - models.list_offense_options (namespace filtering, supported/category filters)
  - fbi CLI `list-offense-codes` subcommand dispatch and error handling
"""

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

import json

import pytest
from click.testing import CliRunner

from statpack.data.sources.fbi import models
from statpack.data.sources.fbi.cli import fbi


class TestListOffenseOptions:
    def test_fbi_namespace_returns_numeric_codes(self):
        options = models.list_offense_options("fbi")
        assert options, "expected some FBI offense options"
        assert all(opt["namespace"] == "fbi" for opt in options)
        assert all(opt["code"].isdigit() for opt in options)

    def test_nibrs_namespace_returns_codes(self):
        options = models.list_offense_options("nibrs")
        assert options, "expected some NIBRS offense options"
        assert all(opt["namespace"] == "nibrs" for opt in options)

    def test_supported_only_filters(self):
        all_opts = models.list_offense_options("nibrs")
        supported = models.list_offense_options("nibrs", supported_only=True)
        assert len(supported) < len(all_opts)
        assert all(opt["supported"] for opt in supported)

    def test_category_filter_is_case_insensitive(self):
        options = models.list_offense_options("fbi", category="violent crime")
        assert options, "expected violent-crime offenses"
        assert all(opt["category"].lower() == "violent crime" for opt in options)

    def test_numeric_codes_sorted_numerically(self):
        codes = [int(opt["code"]) for opt in models.list_offense_options("fbi")]
        assert codes == sorted(codes)

    def test_unknown_namespace_raises(self):
        with pytest.raises(ValueError):
            models.list_offense_options("bogus")


class TestListOffenseCodesCLI:
    def setup_method(self):
        self.runner = CliRunner()

    def test_lists_both_namespaces_by_default(self):
        result = self.runner.invoke(fbi, ["list-offense-codes", "--format", "csv"])
        assert result.exit_code == 0, result.output
        assert "fbi" in result.output
        assert "nibrs" in result.output

    def test_namespace_filter(self):
        result = self.runner.invoke(fbi, ["list-offense-codes", "--namespace", "nibrs", "--format", "csv"])
        assert result.exit_code == 0, result.output
        assert "fbi," not in result.output
        assert "nibrs" in result.output

    def test_command_maps_to_namespace(self):
        result = self.runner.invoke(
            fbi, ["list-offense-codes", "--command", "get-nibrs-counts-by-state", "--format", "csv"]
        )
        assert result.exit_code == 0, result.output
        assert "nibrs" in result.output
        assert "fbi," not in result.output

    def test_supported_only_flag(self):
        result = self.runner.invoke(fbi, ["list-offense-codes", "--namespace", "fbi", "--supported-only", "--raw"])
        assert result.exit_code == 0, result.output
        rows = json.loads(result.output)
        assert rows and all(row["supported"] is True for row in rows)

    def test_command_without_offense_code_is_rejected(self):
        result = self.runner.invoke(fbi, ["list-offense-codes", "--command", "get-reporting-agencies"])
        assert result.exit_code != 0
        assert "does not take an offense code" in result.output

    def test_namespace_command_conflict_is_rejected(self):
        result = self.runner.invoke(
            fbi, ["list-offense-codes", "--command", "get-nibrs-counts-by-state", "--namespace", "fbi"]
        )
        assert result.exit_code != 0
        assert "conflicts with" in result.output
