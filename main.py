#!/usr/bin/env python3
"""
Statpack CLI - Command-line interface for statistical data gathering.

Usage:
    python main.py fbi agencies --output stdout
    python main.py fbi arrests --state NY --offense 11 --start-date 01-2020 --end-date 12-2024 --format json --output file:data.json
    python main.py census acs-variables --year 2024 --output stdout --format csv
    python main.py census acs-by-state --variables B01001_001E --states NY CA TX --year 2024 --format json
"""

import argparse
import json
import csv
import sys
import os
from pathlib import Path
from typing import Optional
from io import StringIO

import pandas as pd

# Import data source modules
from pkg.data.sources.fbi import (
    get_cde_reporting_agencies,
    get_cde_arrest_totals_by_state,
    get_cde_arrest_counts_by_state,
    get_cde_arrest_totals_by_origin,
    get_cde_arrest_counts_by_origin,
    get_cde_nibrs_totals_by_state,
    get_cde_summarized_by_state,
    get_cde_expanded_homicide_counts_by_state,
)
from pkg.data.sources.census import (
    get_census_acs_variables,
    get_census_acs_detailed,
    get_census_acs_detailed_by_state,
    get_census_acs_detailed_by_state_county,
)


class OutputFormatter:
    """Handles output formatting and writing."""

    @staticmethod
    def format_dataframe(df: pd.DataFrame, format_type: str) -> str:
        """Format a DataFrame according to the specified format."""
        if format_type == "json":
            return df.to_json(orient="records", indent=2)
        elif format_type == "csv":
            return df.to_csv(index=False)
        elif format_type == "tsv":
            return df.to_csv(sep="\t", index=False)
        elif format_type == "parquet":
            # Return as bytes via StringIO for now (special handling needed)
            return df.to_parquet()
        elif format_type == "html":
            return df.to_html()
        elif format_type == "markdown":
            return df.to_markdown()
        else:
            # Default to pretty-printed string
            return str(df)

    @staticmethod
    def write_output(data: str, output_spec: str, format_type: str) -> None:
        """Write output to stdout or file."""
        if output_spec == "stdout":
            print(data)
        elif output_spec.startswith("file:"):
            filepath = output_spec.replace("file:", "")
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Handle binary formats
            if format_type == "parquet":
                path.write_bytes(data)
            else:
                path.write_text(data)
            print(f"Data written to {filepath}", file=sys.stderr)
        else:
            raise ValueError(f"Invalid output specification: {output_spec}")


class FBICommands:
    """FBI data source commands."""

    @staticmethod
    def agencies(args) -> pd.DataFrame:
        """Fetch FBI reporting agencies."""
        return get_cde_reporting_agencies()

    @staticmethod
    def arrests_by_state(args) -> pd.DataFrame:
        """Fetch arrest totals or counts by state."""
        if args.breakdown:
            return get_cde_arrest_counts_by_state(
                state_abbr=args.state or None,
                offense_code=args.offense,
                start_date=args.start_date,
                end_date=args.end_date,
            )
        else:
            return get_cde_arrest_totals_by_state(
                state_abbr=args.state or None,
                offense_code=args.offense,
                start_date=args.start_date,
                end_date=args.end_date,
            )

    @staticmethod
    def arrests_by_origin(args) -> pd.DataFrame:
        """Fetch arrests by agency (ORI code)."""
        if args.breakdown:
            return get_cde_arrest_counts_by_origin(
                origin_code=args.ori_code,
                offense_code=args.offense,
                start_date=args.start_date,
                end_date=args.end_date,
            )
        else:
            return get_cde_arrest_totals_by_origin(
                origin_code=args.ori_code,
                offense_code=args.offense,
                start_date=args.start_date,
                end_date=args.end_date,
            )

    @staticmethod
    def summarized_by_state(args) -> pd.DataFrame:
        """Fetch summarized offense data by state."""
        return get_cde_summarized_by_state(
            start_date=args.start_date,
            end_date=args.end_date,
            state_abbr=args.state or None,
            offense_code=args.offense or None,
        )

    @staticmethod
    def nibrs_by_state(args) -> pd.DataFrame:
        """Fetch NIBRS data by state."""
        results = get_cde_nibrs_totals_by_state(
            state_abbr=args.state or None,
            nibrs_code=args.nibrs_code,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        # Convert list results to DataFrame
        if isinstance(results, list):
            return pd.DataFrame(results)
        return results

    @staticmethod
    def expanded_homicide_counts_by_state(args) -> pd.DataFrame:
        """Fetch expanded homicide counts by state."""
        return get_cde_expanded_homicide_counts_by_state(
            start_date=args.start_date,
            end_date=args.end_date,
            state_abbr=args.state or None,
        )


class CensusCommands:
    """Census data source commands."""

    @staticmethod
    def acs_variables(args) -> pd.DataFrame:
        """Fetch available ACS variables."""
        return get_census_acs_variables(
            year=args.year,
            dataset=args.dataset,
        )

    @staticmethod
    def acs_detailed(args) -> pd.DataFrame:
        """Fetch ACS data at national level."""
        variables = args.variables.split(",") if isinstance(args.variables, str) else args.variables
        return get_census_acs_detailed(
            variables=variables,
            year=args.year,
            dataset=args.dataset,
        )

    @staticmethod
    def acs_by_state(args) -> pd.DataFrame:
        """Fetch ACS data by state."""
        variables = args.variables.split(",") if isinstance(args.variables, str) else args.variables
        states = args.states.split(",") if isinstance(args.states, str) else args.states
        return get_census_acs_detailed_by_state(
            variables=variables,
            year=args.year,
            dataset=args.dataset,
            states=states,
        )

    @staticmethod
    def acs_by_state_county(args) -> pd.DataFrame:
        """Fetch ACS data by state and county."""
        variables = args.variables.split(",") if isinstance(args.variables, str) else args.variables
        states = args.states.split(",") if isinstance(args.states, str) else args.states
        return get_census_acs_detailed_by_state_county(
            variables=variables,
            year=args.year,
            dataset=args.dataset,
            states=states,
        )


def setup_fbi_subparsers(subparsers):
    """Set up FBI subcommand parsers."""
    fbi_parser = subparsers.add_parser("fbi", help="FBI Crime Data Explorer")
    fbi_subparsers = fbi_parser.add_subparsers(dest="fbi_command", required=True)

    # Agencies command
    agencies = fbi_subparsers.add_parser("get-reporting-agencies", help="Fetch FBI reporting agencies")
    agencies.set_defaults(func=FBICommands.agencies)
    _add_output_args(agencies)

    # Arrests by state command
    arrests_state = fbi_subparsers.add_parser("get-arrests-by-state", help="Fetch arrests by state")
    arrests_state.add_argument("--state", help="State abbreviation or name (default: all states)")
    arrests_state.add_argument("--offense", type=int, required=False, help="FBI offense code", default=None)
    arrests_state.add_argument("--start-date", type=str, required=True, help="Start date (MM-YYYY format, e.g., 01-2020)")
    arrests_state.add_argument("--end-date", type=str, required=True, help="End date (MM-YYYY format, e.g., 12-2024)")
    arrests_state.add_argument("--breakdown", help="Demographic breakdown (e.g., by_race, by_age)")
    arrests_state.set_defaults(func=FBICommands.arrests_by_state)
    _add_output_args(arrests_state)

    # Arrests by origin (agency) command
    arrests_origin = fbi_subparsers.add_parser("get-arrests-by-origin", help="Fetch arrests by agency ORI code")
    arrests_origin.add_argument("--ori-code", required=True, help="Agency ORI code")
    arrests_origin.add_argument("--offense", type=int, required=True, help="FBI offense code")
    arrests_origin.add_argument("--start-date", type=str, required=True, help="Start date (MM-YYYY format, e.g., 01-2020)")
    arrests_origin.add_argument("--end-date", type=str, required=True, help="End date (MM-YYYY format, e.g., 12-2024)")
    arrests_origin.set_defaults(func=FBICommands.arrests_by_origin)
    _add_output_args(arrests_origin)

    # NIBRS command
    nibrs = fbi_subparsers.add_parser("get-nibrs-by-state", help="Fetch NIBRS data by state")
    nibrs.add_argument("--state", help="State abbreviation or name (default: all states)")
    nibrs.add_argument("--nibrs-code", required=True, help="NIBRS offense code (e.g., HOM, ASS, ROB)")
    nibrs.add_argument("--start-date", type=str, required=True, help="Start date (MM-YYYY format, e.g., 01-2020)")
    nibrs.add_argument("--end-date", type=str, required=True, help="End date (MM-YYYY format, e.g., 12-2024)")
    nibrs.set_defaults(func=FBICommands.nibrs_by_state)
    _add_output_args(nibrs)

    # Summarized by state command
    summarized = fbi_subparsers.add_parser("get-summary-by-state", help="Fetch summarized offense data by state")
    summarized.add_argument("--state", help="State abbreviation (default: all states)")
    summarized.add_argument(
        "--offense",
        choices=["V", "ASS", "LAR", "MVT", "HOM", "RPE", "ROB", "ARS", "P"],
        help="Offense code (default: all offenses)",
    )
    summarized.add_argument("--start-date", type=str, required=True, help="Start date (MM-YYYY format, e.g., 01-2020)")
    summarized.add_argument("--end-date", type=str, required=True, help="End date (MM-YYYY format, e.g., 12-2024)")
    summarized.set_defaults(func=FBICommands.summarized_by_state)
    _add_output_args(summarized)

    # Expanded Homicide By State
    expanded_homicide = fbi_subparsers.add_parser("get-expanded-homicide-by-state", help="Fetch expanded homicide counts by state")
    expanded_homicide.add_argument("--state", help="State abbreviation (default: all states)")
    expanded_homicide.add_argument("--start-date", type=str, required=True, help="Start date (MM-YYYY format, e.g., 01-2020)")
    expanded_homicide.add_argument("--end-date", type=str, required=True, help="End date (MM-YYYY format, e.g., 12-2024)")
    expanded_homicide.set_defaults(func=FBICommands.expanded_homicide_counts_by_state)
    _add_output_args(expanded_homicide)


def setup_census_subparsers(subparsers):
    """Set up Census subcommand parsers."""
    census_parser = subparsers.add_parser("census", help="U.S. Census Bureau Data")
    census_subparsers = census_parser.add_subparsers(dest="census_command", required=True)

    # ACS Variables command
    acs_vars = census_subparsers.add_parser("get-acs-variables", help="List available ACS variables")
    acs_vars.add_argument("--year", type=int, default=2024, help="Survey year (default: 2024)")
    acs_vars.add_argument("--dataset", default="acs/acs1", help="Dataset identifier (default: acs/acs1)")
    acs_vars.set_defaults(func=CensusCommands.acs_variables)
    _add_output_args(acs_vars)

    # ACS Detailed (national) command
    acs_detailed = census_subparsers.add_parser("get-acs-detailed", help="Fetch ACS data (national level)")
    acs_detailed.add_argument("--variables", required=True, help="Comma-separated variable codes")
    acs_detailed.add_argument("--year", type=int, default=2024, help="Survey year (default: 2024)")
    acs_detailed.add_argument("--dataset", default="acs/ acs1", help="Dataset identifier (default: acs/acs1)")
    acs_detailed.set_defaults(func=CensusCommands.acs_detailed)
    _add_output_args(acs_detailed)

    # ACS by State command
    acs_state = census_subparsers.add_parser("get-acs-by-state", help="Fetch ACS data by state")
    acs_state.add_argument("--variables", required=True, help="Comma-separated variable codes")
    acs_state.add_argument("--states", required=True, help="Comma-separated state abbreviations")
    acs_state.add_argument("--year", type=int, default=2024, help="Survey year (default: 2024)")
    acs_state.add_argument("--dataset", default="acs/acs1", help="Dataset identifier (default: acs/acs1)")
    acs_state.set_defaults(func=CensusCommands.acs_by_state)
    _add_output_args(acs_state)

    # ACS by State and County command
    acs_county = census_subparsers.add_parser("get-acs-by-state-county", help="Fetch ACS data by state and county")
    acs_county.add_argument("--variables", required=True, help="Comma-separated variable codes")
    acs_county.add_argument("--states", required=True, help="Comma-separated state abbreviations")
    acs_county.add_argument("--year", type=int, default=2024, help="Survey year (default: 2024)")
    acs_county.add_argument("--dataset", default="acs/acs1", help="Dataset identifier (default: acs/acs1)")
    acs_county.set_defaults(func=CensusCommands.acs_by_state_county)
    _add_output_args(acs_county)


def _add_output_args(parser):
    """Add common output arguments to a parser."""
    parser.add_argument(
        "--output",
        default="stdout",
        help='Output destination: "stdout" or "file:/path/to/file" (default: stdout)',
    )
    parser.add_argument(
        "--format",
        default="csv",
        choices=["json", "csv", "tsv", "html", "markdown", "parquet"],
        help="Output format (default: csv)",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Statpack CLI - Statistical data gathering tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch FBI agencies
  python main.py fbi agencies --output stdout

  # Fetch murder arrests in New York (2020-2024)
  python main.py fbi arrests --state NY --offense 11 --start-date 01-2020 --end-date 12-2024 --format json --output file:arrests.json

  # Fetch NIBRS homicide data for all states
  python main.py fbi nibrs --nibrs-code HOM --start-date 01-2020 --end-date 12-2024 --format csv

  # Fetch Census ACS population data by state
  python main.py census acs-by-state --variables B01001_001E --states NY,CA,TX --year 2024 --format json --output file:population.json

  # Fetch ACS variable list
  python main.py census acs-variables --year 2024 --output stdout --format markdown
        """,
    )

    subparsers = parser.add_subparsers(dest="source", required=True, help="Data source")

    setup_fbi_subparsers(subparsers)
    setup_census_subparsers(subparsers)

    args = parser.parse_args()

    try:
        # Fetch data
        df = args.func(args)

        # Format output
        formatted_data = OutputFormatter.format_dataframe(df, args.format)

        # Write output
        OutputFormatter.write_output(formatted_data, args.output, args.format)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
