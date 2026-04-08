"""Tests for the statpack CLI (top-level main.py).

Covers:
- OutputFormatter: format_dataframe (json / csv / tsv / html / markdown)
- OutputFormatter: write_output (stdout, file:, invalid spec)
- FBICommands dispatch methods (agencies, arrests_by_state, arrests_by_origin,
  summarized_by_state, nibrs_by_state, expanded_homicide_counts_by_state)
- CLI arg-parse + end-to-end integration (--format, --output stdout/file)
- Error exits (missing required args, bad subcommand)
"""

import importlib
import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------


def _simple_df():
    return pd.DataFrame([{"state": "NY", "value": 42}])


# ---------------------------------------------------------------------------
# OutputFormatter unit tests
# ---------------------------------------------------------------------------


class TestOutputFormatter:
    @pytest.fixture(autouse=True)
    def _load(self, monkeypatch):
        monkeypatch.setenv("GOV_API_BASE_URL", "https://example.test")
        monkeypatch.setenv("GOV_API_KEY", "test-api-key")
        import main as m

        self.m = importlib.reload(m)

    def test_format_json_is_valid_json(self):
        out = self.m.OutputFormatter.format_dataframe(_simple_df(), "json")
        parsed = json.loads(out)
        assert parsed == [{"state": "NY", "value": 42}]

    def test_format_csv_contains_header_and_row(self):
        out = self.m.OutputFormatter.format_dataframe(_simple_df(), "csv")
        lines = out.strip().splitlines()
        assert lines[0] == "state,value"
        assert "NY" in lines[1]

    def test_format_tsv_uses_tab_delimiter(self):
        out = self.m.OutputFormatter.format_dataframe(_simple_df(), "tsv")
        assert "\t" in out

    def test_format_html_contains_table_tag(self):
        out = self.m.OutputFormatter.format_dataframe(_simple_df(), "html")
        assert "<table" in out.lower()

    def test_format_markdown_contains_pipe(self, mocker):
        mocker.patch.object(
            pd.DataFrame,
            "to_markdown",
            return_value="| state | value |\n|-------|-------|\n| NY    | 42    |",
        )
        out = self.m.OutputFormatter.format_dataframe(_simple_df(), "markdown")
        assert "|" in out

    def test_format_unknown_falls_back_to_str(self):
        out = self.m.OutputFormatter.format_dataframe(_simple_df(), "unknown_format")
        assert "NY" in out

    def test_write_output_stdout_prints(self, capsys):
        self.m.OutputFormatter.write_output("hello world", "stdout", "csv")
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_write_output_file_creates_file(self, tmp_path):
        dest = tmp_path / "out.csv"
        self.m.OutputFormatter.write_output("a,b\n1,2", f"file:{dest}", "csv")
        assert dest.read_text() == "a,b\n1,2"

    def test_write_output_file_creates_parent_dirs(self, tmp_path):
        dest = tmp_path / "nested" / "deep" / "out.csv"
        self.m.OutputFormatter.write_output("x", f"file:{dest}", "csv")
        assert dest.exists()

    def test_write_output_invalid_spec_raises(self):
        with pytest.raises(ValueError, match="Invalid output specification"):
            self.m.OutputFormatter.write_output("x", "notvalid", "csv")


# ---------------------------------------------------------------------------
# FBICommands dispatch tests
# ---------------------------------------------------------------------------


class TestFBICommandsDispatch:
    """Test that FBICommands static methods correctly route to the right
    function and pass through argparse Namespace fields."""

    @pytest.fixture(autouse=True)
    def _load(self, monkeypatch):
        monkeypatch.setenv("GOV_API_BASE_URL", "https://example.test")
        monkeypatch.setenv("GOV_API_KEY", "test-api-key")
        import main as m

        self.m = importlib.reload(m)

    def _args(self, **kwargs):
        """Build a minimal argparse Namespace."""
        import argparse

        defaults = dict(
            state=None,
            offense=None,
            start_date="01-2025",
            end_date="02-2025",
            breakdown=None,
            ori_code="AL0430200",
            nibrs_code="13A",
            output="stdout",
            format="csv",
        )
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_agencies_calls_get_reporting_agencies(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_reporting_agencies", return_value=_simple_df()
        )
        result = self.m.FBICommands.agencies(self._args())
        mock_fn.assert_called_once()
        assert isinstance(result, pd.DataFrame)

    def test_arrests_by_state_totals_path(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_arrest_totals_by_state", return_value=_simple_df()
        )
        self.m.FBICommands.arrests_by_state(self._args(state="NY", breakdown=None))
        _, kwargs = mock_fn.call_args
        assert kwargs["state_abbr"] == "NY"

    def test_arrests_by_state_breakdown_path(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_arrest_counts_by_state", return_value=_simple_df()
        )
        self.m.FBICommands.arrests_by_state(self._args(state="CA", breakdown="by_race"))
        _, kwargs = mock_fn.call_args
        assert kwargs["state_abbr"] == "CA"

    def test_arrests_by_origin_totals_path(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_arrest_totals_by_origin", return_value=_simple_df()
        )
        self.m.FBICommands.arrests_by_origin(self._args(breakdown=None))
        _, kwargs = mock_fn.call_args
        assert kwargs["origin_code"] == "AL0430200"

    def test_arrests_by_origin_breakdown_path(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_arrest_counts_by_origin", return_value=_simple_df()
        )
        self.m.FBICommands.arrests_by_origin(self._args(breakdown="by_age"))
        _, kwargs = mock_fn.call_args
        assert kwargs["origin_code"] == "AL0430200"

    def test_nibrs_by_state_returns_dataframe(self, mocker):
        mocker.patch.object(
            self.m, "get_nibrs_totals_by_state", return_value=_simple_df()
        )
        result = self.m.FBICommands.nibrs_by_state(self._args())
        assert isinstance(result, pd.DataFrame)

    def test_nibrs_by_state_converts_list_to_dataframe(self, mocker):
        mocker.patch.object(
            self.m, "get_nibrs_totals_by_state", return_value=[{"a": 1}]
        )
        result = self.m.FBICommands.nibrs_by_state(self._args())
        assert isinstance(result, pd.DataFrame)

    def test_expanded_homicide_passes_state(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_expanded_homicide_counts_by_state", return_value=_simple_df()
        )
        self.m.FBICommands.expanded_homicide_counts_by_state(self._args(state="TX"))
        _, kwargs = mock_fn.call_args
        assert kwargs["state_abbr"] == "TX"

    def test_expanded_homicide_none_state_passes_none(self, mocker):
        mock_fn = mocker.patch.object(
            self.m, "get_expanded_homicide_counts_by_state", return_value=_simple_df()
        )
        self.m.FBICommands.expanded_homicide_counts_by_state(self._args(state=None))
        _, kwargs = mock_fn.call_args
        assert kwargs["state_abbr"] is None


# ---------------------------------------------------------------------------
# CLI integration (end-to-end arg parsing + output routing)
# ---------------------------------------------------------------------------


class TestCLIIntegration:
    """Run the CLI in-process via the cli_runner fixture."""

    def test_missing_source_exits_nonzero(self, cli_runner):
        _, _, code = cli_runner([])
        assert code != 0

    def test_unknown_subcommand_exits_nonzero(self, cli_runner):
        _, _, code = cli_runner(["fbi", "nonexistent-command"])
        assert code != 0

    def test_fbi_agencies_stdout_csv(self, cli_runner, mocker):
        import pkg.data.sources.fbi as fbi_pkg

        mocker.patch.object(
            fbi_pkg, "get_reporting_agencies", return_value=_simple_df()
        )
        stdout, _, code = cli_runner(
            ["fbi", "get-reporting-agencies", "--output", "stdout", "--format", "csv"]
        )
        assert code == 0
        assert "state" in stdout

    def test_fbi_agencies_stdout_json(self, cli_runner, mocker):
        import pkg.data.sources.fbi as fbi_pkg

        mocker.patch.object(
            fbi_pkg, "get_reporting_agencies", return_value=_simple_df()
        )
        stdout, _, code = cli_runner(
            ["fbi", "get-reporting-agencies", "--output", "stdout", "--format", "json"]
        )
        assert code == 0
        parsed = json.loads(stdout)
        assert parsed == [{"state": "NY", "value": 42}]

    def test_fbi_agencies_write_to_file(self, cli_runner, mocker, tmp_path):
        import pkg.data.sources.fbi as fbi_pkg

        mocker.patch.object(
            fbi_pkg, "get_reporting_agencies", return_value=_simple_df()
        )
        dest = tmp_path / "agencies.csv"
        _, stderr, code = cli_runner(
            [
                "fbi",
                "get-reporting-agencies",
                "--output",
                f"file:{dest}",
                "--format",
                "csv",
            ]
        )
        assert code == 0
        assert dest.exists()
        assert "NY" in dest.read_text()

    def test_fbi_nibrs_requires_nibrs_code(self, cli_runner):
        _, _, code = cli_runner(
            [
                "fbi",
                "get-nibrs-by-state",
                "--state",
                "NY",
                "--start-date",
                "01-2025",
                "--end-date",
                "02-2025",
                # --nibrs-code intentionally omitted
            ]
        )
        assert code != 0

    def test_fbi_arrests_requires_start_date(self, cli_runner):
        _, _, code = cli_runner(
            [
                "fbi",
                "get-arrests-by-state",
                "--state",
                "NY",
                "--end-date",
                "02-2025",
                # --start-date intentionally omitted
            ]
        )
        assert code != 0

    def test_exception_in_command_exits_with_code_1(self, cli_runner, mocker):
        import pkg.data.sources.fbi as fbi_pkg

        mocker.patch.object(
            fbi_pkg,
            "get_reporting_agencies",
            side_effect=RuntimeError("simulated failure"),
        )
        _, stderr, code = cli_runner(
            ["fbi", "get-reporting-agencies", "--output", "stdout"]
        )
        assert code == 1
        assert "simulated failure" in stderr
