#!/usr/bin/env python3
"""
Statpack CLI - Command-line interface for statistical data gathering.

Usage:
    python main.py fbi get-reporting-agencies
    python main.py fbi get-arrest-counts-by-state --territory NY --start-date 01-2020 --end-date 12-2024 --format json
    python main.py census get-acs-variables --year 2024 --format markdown
    python main.py census get-acs-by-state --variables B01001_001E --states NY,CA,TX --year 2024 --format json
"""

import json
import sys
from pathlib import Path

import click
import pandas as pd

from pkg.data.sources.fbi.cli import fbi
from pkg.data.sources.census import (
    get_census_acs_variables,
    get_census_acs_detailed,
    get_census_acs_detailed_by_state,
    get_census_acs_detailed_by_state_county,
)


# ---------------------------------------------------------------------------
# Output helpers (shared by census commands until census/cli.py is created)
# ---------------------------------------------------------------------------


def _format_dataframe(df: pd.DataFrame, output_format: str) -> str:
    df = df.reset_index()
    if output_format == "json":
        return df.to_json(orient="records", indent=2)
    if output_format == "csv":
        return df.to_csv(index=False)
    if output_format == "tsv":
        return df.to_csv(sep="\t", index=False)
    if output_format == "html":
        return df.to_html(index=False)
    if output_format == "markdown":
        return df.to_markdown(index=False)
    return str(df)


def _emit(result: pd.DataFrame | list, output_format: str, output_dest: str, raw: bool) -> None:
    if raw or isinstance(result, list):
        data = json.dumps(result if isinstance(result, list) else [result], indent=2, default=str)
    else:
        data = _format_dataframe(result, output_format)

    if output_dest == "stdout":
        click.echo(data)
        return

    if output_dest.startswith("file:"):
        path = Path(output_dest[len("file:") :])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        click.echo(f"Written to {path}", err=True)
        return

    raise click.BadParameter(
        f"Invalid output destination {output_dest!r}. Use 'stdout' or 'file:/path'.", param_hint="--output"
    )


def _output_options(fn):
    fn = click.option("--debug", is_flag=True, default=False, help="Enable verbose debug output.")(fn)
    fn = click.option("--raw", is_flag=True, default=False, help="Return raw JSON records.")(fn)
    fn = click.option(
        "--output",
        "output_dest",
        default="stdout",
        show_default=True,
        metavar="DEST",
        help='Output destination: "stdout" or "file:/path/to/file".',
    )(fn)
    fn = click.option(
        "--format",
        "output_format",
        default="csv",
        show_default=True,
        type=click.Choice(["json", "csv", "tsv", "html", "markdown"]),
        help="Output format.",
    )(fn)
    return fn


# ---------------------------------------------------------------------------
# Top-level CLI group
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """Statpack CLI - Statistical data gathering tool."""


cli.add_command(fbi)


# ---------------------------------------------------------------------------
# Census commands (to be migrated to pkg/data/sources/census/cli.py)
# ---------------------------------------------------------------------------


@cli.group("census", help="U.S. Census Bureau Data commands.")
def census() -> None:
    pass


@census.command("get-acs-variables")
@click.option("--year", default=2024, show_default=True, type=int, help="Survey year.")
@click.option("--dataset", default="acs/acs1", show_default=True, help="Dataset identifier.")
@_output_options
def get_acs_variables(year, dataset, output_format, output_dest, raw, debug):
    """List available ACS variables."""
    result = get_census_acs_variables(year=year, dataset=dataset)
    _emit(result, output_format, output_dest, raw)


@census.command("get-acs-detailed")
@click.option("--variables", required=True, help="Comma-separated variable codes.")
@click.option("--year", default=2024, show_default=True, type=int, help="Survey year.")
@click.option("--dataset", default="acs/acs1", show_default=True, help="Dataset identifier.")
@_output_options
def get_acs_detailed(variables, year, dataset, output_format, output_dest, raw, debug):
    """Fetch ACS data at the national level."""
    var_list = variables.split(",") if isinstance(variables, str) else variables
    result = get_census_acs_detailed(variables=var_list, year=year, dataset=dataset)
    _emit(result, output_format, output_dest, raw)


@census.command("get-acs-by-state")
@click.option("--variables", required=True, help="Comma-separated variable codes.")
@click.option("--states", required=True, help="Comma-separated state abbreviations.")
@click.option("--year", default=2024, show_default=True, type=int, help="Survey year.")
@click.option("--dataset", default="acs/acs1", show_default=True, help="Dataset identifier.")
@_output_options
def get_acs_by_state(variables, states, year, dataset, output_format, output_dest, raw, debug):
    """Fetch ACS data by state."""
    var_list = variables.split(",") if isinstance(variables, str) else variables
    state_list = states.split(",") if isinstance(states, str) else states
    result = get_census_acs_detailed_by_state(variables=var_list, year=year, dataset=dataset, states=state_list)
    _emit(result, output_format, output_dest, raw)


@census.command("get-acs-by-state-county")
@click.option("--variables", required=True, help="Comma-separated variable codes.")
@click.option("--states", required=True, help="Comma-separated state abbreviations.")
@click.option("--year", default=2024, show_default=True, type=int, help="Survey year.")
@click.option("--dataset", default="acs/acs1", show_default=True, help="Dataset identifier.")
@_output_options
def get_acs_by_state_county(variables, states, year, dataset, output_format, output_dest, raw, debug):
    """Fetch ACS data by state and county."""
    var_list = variables.split(",") if isinstance(variables, str) else variables
    state_list = states.split(",") if isinstance(states, str) else states
    result = get_census_acs_detailed_by_state_county(variables=var_list, year=year, dataset=dataset, states=state_list)
    _emit(result, output_format, output_dest, raw)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
