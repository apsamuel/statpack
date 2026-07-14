import json
from pathlib import Path

import click
import pandas as pd

from .client import Client
from .models import get_fbi_code_from_offense_name, get_nibrs_code_from_offense_name

# ---------------------------------------------------------------------------
# Offense name/code resolution
# ---------------------------------------------------------------------------

# Namespace-aware resolvers. FBI arrest codes (numeric) and NIBRS codes
# (alphanumeric) are DIFFERENT code systems, so each command must resolve names
# against the correct namespace to avoid mapping a name to the wrong code.
_OFFENSE_RESOLVERS = {"fbi": get_fbi_code_from_offense_name, "nibrs": get_nibrs_code_from_offense_name}

# Which offense code namespace each offense-consuming entrypoint expects. Used by
# `list-offense-codes` to show the applicable options for a given command.
_OFFENSE_COMMAND_NAMESPACES = {
    "get-arrest-counts-by-state": "fbi",
    "get-arrest-totals-by-state": "fbi",
    "per-capita-by-race": "fbi",
    "get-nibrs-counts-by-state": "nibrs",
}


def _resolve_offense(offense_code, offense_name, namespace: str, required: bool = False):
    """Resolve the effective offense code from --offense-code / --offense-name.

    ``namespace`` selects the code system ("fbi" or "nibrs"). ``--offense-code``
    and ``--offense-name`` are mutually exclusive. When ``--offense-name`` is
    given it is resolved against the namespace-specific lookup table only.
    """
    if offense_name:
        if offense_code:
            raise click.UsageError("--offense-code and --offense-name are mutually exclusive; provide only one.")
        resolved = _OFFENSE_RESOLVERS[namespace](offense_name)
        if resolved is None:
            raise click.BadParameter(
                f"No {namespace.upper()} offense matches name {offense_name!r}. "
                "Names must match an offense name or short name exactly (case-insensitive). "
                "Use --offense-code instead, or see the offense code data files under "
                "src/statpack/data/sources/fbi/data/.",
                param_hint="--offense-name",
            )
        return resolved

    if required and not offense_code:
        raise click.UsageError("Provide --offense-code or --offense-name.")

    return offense_code


def _year_from_month_year(value: str | None) -> int | None:
    """Extract the 4-digit year from an ``MM-YYYY`` date string, or None if unparseable."""
    if not value:
        return None
    parts = str(value).split("-")
    for token in reversed(parts):
        token = token.strip()
        if len(token) == 4 and token.isdigit():
            return int(token)
    return None


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _to_table(df: pd.DataFrame, max_cell_width: int = 48) -> str:
    """Render a DataFrame as an aligned, kubectl-style plain text table."""

    def _stringify(value) -> str:
        if pd.isna(value):
            return ""
        text = str(value).replace("\n", "\\n")
        if len(text) > max_cell_width:
            return text[: max_cell_width - 3] + "..."
        return text

    table_df = df
    headers = [str(col).upper() for col in table_df.columns]
    rows = [[_stringify(value) for value in row] for row in table_df.itertuples(index=False, name=None)]

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    header_line = "  ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers)))
    body_lines = ["  ".join(row[idx].ljust(widths[idx]) for idx in range(len(row))) for row in rows]

    if not body_lines:
        return header_line

    return "\n".join([header_line, *body_lines])


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
    if output_format == "table":
        return _to_table(df)
    return str(df)


def _emit(result: pd.DataFrame | list, output_format: str, output_dest: str, raw: bool) -> None:
    """Format *result* and write to the requested destination."""
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
        f"Invalid output destination {output_dest!r}. Use 'stdout' or 'file:/path/to/file'.", param_hint="--output"
    )


def _output_options(fn):
    """Attach shared output options (--format, --output, --raw, --debug) to a command."""
    fn = click.option("--debug", is_flag=True, default=False, help="Enable verbose debug output.")(fn)
    fn = click.option(
        "--raw", is_flag=True, default=False, help="Return raw JSON records instead of a formatted table."
    )(fn)
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
        type=click.Choice(["json", "csv", "tsv", "html", "markdown", "table"]),
        help="Output format (ignored when --raw is set).",
    )(fn)
    return fn


# ---------------------------------------------------------------------------
# FBI command group
# ---------------------------------------------------------------------------


@click.group("fbi", help="FBI Crime Data Explorer (CDE) commands.")
@click.pass_context
def fbi(ctx: click.Context) -> None:
    ctx.ensure_object(dict)
    ctx.obj.setdefault("client", Client())


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


@fbi.command("list-offense-codes")
@click.option(
    "--namespace",
    type=click.Choice(["fbi", "nibrs"]),
    default=None,
    help="Offense code system to list. Omit to list both.",
)
@click.option(
    "--command",
    "command_name",
    default=None,
    metavar="COMMAND",
    help="List codes applicable to a specific entrypoint (e.g. get-nibrs-counts-by-state).",
)
@click.option("--category", default=None, metavar="CATEGORY", help="Filter to a single offense category.")
@click.option("--supported-only", is_flag=True, default=False, help="Only list codes supported by the endpoint.")
@_output_options
@click.pass_context
def list_offense_codes(ctx, namespace, command_name, category, supported_only, output_format, output_dest, raw, debug):
    """List the offense codes applicable to the FBI arrest / NIBRS entrypoints."""
    from .models import list_offense_options

    if command_name is not None:
        resolved_ns = _OFFENSE_COMMAND_NAMESPACES.get(command_name)
        if resolved_ns is None:
            raise click.BadParameter(
                f"Command {command_name!r} does not take an offense code. "
                f"Commands with offense codes: {', '.join(sorted(_OFFENSE_COMMAND_NAMESPACES))}.",
                param_hint="--command",
            )
        if namespace is not None and namespace != resolved_ns:
            raise click.UsageError(
                f"--namespace {namespace!r} conflicts with --command {command_name!r} "
                f"(which uses the {resolved_ns!r} namespace)."
            )
        namespaces = [resolved_ns]
    elif namespace is not None:
        namespaces = [namespace]
    else:
        namespaces = ["fbi", "nibrs"]

    options: list[dict] = []
    for ns in namespaces:
        options.extend(list_offense_options(ns, supported_only=supported_only, category=category))

    if raw:
        _emit(options, output_format, output_dest, raw=True)
        return

    columns = ["code", "namespace", "name", "short_name", "category", "supported"]
    df = pd.DataFrame(options, columns=columns)
    if not df.empty:
        df = df.set_index("code")
    _emit(df, output_format, output_dest, raw=False)


@fbi.command("get-reporting-agencies")
@click.option(
    "--territory", default=None, metavar="STATE", help="State abbreviation or name. Omit to query all territories."
)
@_output_options
@click.pass_context
def get_reporting_agencies(ctx, territory, output_format, output_dest, raw, debug):
    """Fetch FBI reporting agencies."""
    client: Client = ctx.obj["client"]
    result = client.get_agencies_by_territory(territory=territory, raw=raw, debug=debug)
    _emit(result, output_format, output_dest, raw)


@fbi.command("get-arrest-counts-by-state")
@click.option("--territory", required=True, metavar="STATE", help="State abbreviation or name.")
@click.option("--offense-code", "offense_code", default=None, metavar="CODE", help="FBI offense code (default: all).")
@click.option(
    "--offense-name",
    "offense_name",
    default=None,
    metavar="NAME",
    help="FBI offense name or short name to resolve to a code (mutually exclusive with --offense-code).",
)
@click.option("--start-date", "start_date", required=True, metavar="MM-YYYY", help="Start date.")
@click.option("--end-date", "end_date", required=True, metavar="MM-YYYY", help="End date.")
@_output_options
@click.pass_context
def get_arrest_counts_by_state(
    ctx, territory, offense_code, offense_name, start_date, end_date, output_format, output_dest, raw, debug
):
    """Fetch arrest counts (demographic breakdown) by state."""
    offense_code = _resolve_offense(offense_code, offense_name, namespace="fbi") or "all"
    client: Client = ctx.obj["client"]
    result = client.get_arrest_counts_by_state(
        territory=territory, offense_code=offense_code, start_date=start_date, end_date=end_date, raw=raw, debug=debug
    )
    _emit(result, output_format, output_dest, raw)


@fbi.command("get-arrest-totals-by-state")
@click.option("--territory", required=True, metavar="STATE", help="State abbreviation or name.")
@click.option("--offense-code", "offense_code", default=None, metavar="CODE", help="FBI offense code (default: all).")
@click.option(
    "--offense-name",
    "offense_name",
    default=None,
    metavar="NAME",
    help="FBI offense name or short name to resolve to a code (mutually exclusive with --offense-code).",
)
@click.option("--start-date", "start_date", required=True, metavar="MM-YYYY", help="Start date.")
@click.option("--end-date", "end_date", required=True, metavar="MM-YYYY", help="End date.")
@_output_options
@click.pass_context
def get_arrest_totals_by_state(
    ctx, territory, offense_code, offense_name, start_date, end_date, output_format, output_dest, raw, debug
):
    """Fetch arrest totals by state."""
    offense_code = _resolve_offense(offense_code, offense_name, namespace="fbi") or "all"
    client: Client = ctx.obj["client"]
    result = client.get_arrest_totals_by_state(
        territory=territory, offense_code=offense_code, start_date=start_date, end_date=end_date, raw=raw, debug=debug
    )
    _emit(result, output_format, output_dest, raw)


@fbi.command("get-expanded-homicide-counts-by-state")
@click.option("--territory", required=True, metavar="STATE", help="State abbreviation or name.")
@click.option("--start-date", "start_date", required=True, metavar="MM-YYYY", help="Start date.")
@click.option("--end-date", "end_date", required=True, metavar="MM-YYYY", help="End date.")
@_output_options
@click.pass_context
def get_expanded_homicide_counts_by_state(ctx, territory, start_date, end_date, output_format, output_dest, raw, debug):
    """Fetch expanded homicide (SHR) per-capita counts by state."""
    client: Client = ctx.obj["client"]
    result = client.get_expanded_homicide_counts_by_state(
        territory=territory, start_date=start_date, end_date=end_date, raw=raw, debug=debug
    )
    _emit(result, output_format, output_dest, raw)


@fbi.command("get-expanded-homicide-totals-by-state")
@click.option("--territory", required=True, metavar="STATE", help="State abbreviation or name.")
@click.option("--start-date", "start_date", required=True, metavar="MM-YYYY", help="Start date.")
@click.option("--end-date", "end_date", required=True, metavar="MM-YYYY", help="End date.")
@_output_options
@click.pass_context
def get_expanded_homicide_totals_by_state(ctx, territory, start_date, end_date, output_format, output_dest, raw, debug):
    """Fetch expanded homicide (SHR) aggregate totals by state."""
    client: Client = ctx.obj["client"]
    result = client.get_expanded_homicide_totals_by_state(
        territory=territory, start_date=start_date, end_date=end_date, raw=raw, debug=debug
    )
    _emit(result, output_format, output_dest, raw)


@fbi.command("get-nibrs-counts-by-state")
@click.option("--territory", required=True, metavar="STATE", help="State abbreviation or name.")
@click.option("--offense-code", "offense_code", default=None, metavar="CODE", help="NIBRS offense code.")
@click.option(
    "--offense-name",
    "offense_name",
    default=None,
    metavar="NAME",
    help="NIBRS offense name or short name to resolve to a code (mutually exclusive with --offense-code).",
)
@click.option("--start-date", "start_date", required=True, metavar="MM-YYYY", help="Start date.")
@click.option("--end-date", "end_date", required=True, metavar="MM-YYYY", help="End date.")
@_output_options
@click.pass_context
def get_nibrs_counts_by_state(
    ctx, territory, offense_code, offense_name, start_date, end_date, output_format, output_dest, raw, debug
):
    """Fetch NIBRS incident-based offense counts by state."""
    offense_code = _resolve_offense(offense_code, offense_name, namespace="nibrs", required=True)
    client: Client = ctx.obj["client"]
    result = client.get_nibrs_counts_by_state(
        territory=territory, offense_code=offense_code, start_date=start_date, end_date=end_date, raw=raw, debug=debug
    )
    _emit(result, output_format, output_dest, raw)


@fbi.command("per-capita-by-race")
@click.option("--state", required=True, metavar="STATE", help="State abbreviation or name.")
@click.option("--offense-code", "offense_code", default=None, metavar="CODE", help="FBI offense code (default: all).")
@click.option(
    "--offense-name",
    "offense_name",
    default=None,
    metavar="NAME",
    help="FBI offense name or short name to resolve to a code (mutually exclusive with --offense-code).",
)
@click.option("--start-date", "start_date", required=True, metavar="MM-YYYY", help="Start date.")
@click.option("--end-date", "end_date", required=True, metavar="MM-YYYY", help="End date.")
@click.option(
    "--year",
    default=None,
    type=int,
    metavar="YYYY",
    help="Census population estimate year (denominator). Defaults to the end-date year.",
)
@_output_options
@click.pass_context
def per_capita_by_race(
    ctx, state, offense_code, offense_name, start_date, end_date, year, output_format, output_dest, raw, debug
):
    """Per-capita arrest rates by race (FBI arrests / Census population)."""
    # Lazy import so the FBI CLI never requires Census credentials unless this command runs.
    from statpack.data.analysis import per_capita_by_race as _per_capita_by_race

    start_year = _year_from_month_year(start_date)
    end_year = _year_from_month_year(end_date)

    # Default the population (denominator) year to the arrest window so the numerator
    # and denominator refer to the same period instead of a hard-coded calendar year.
    if year is None:
        year = end_year
        if year is not None:
            click.echo(f"--year not set; using {year} (from --end-date) as the population year.", err=True)

    # Warn on time-alignment problems that distort the per-capita rate.
    if start_year is not None and end_year is not None:
        if start_year != end_year:
            click.echo(
                f"Warning: arrest range spans {start_year}-{end_year} ({end_year - start_year + 1} years) but the "
                f"population denominator is a single year ({year}); the rate is not annualized and will be inflated.",
                err=True,
            )
        elif year is not None and year != end_year:
            click.echo(
                f"Warning: population year ({year}) does not match the arrest year ({end_year}); "
                "numerator and denominator refer to different periods.",
                err=True,
            )

    offense_code = _resolve_offense(offense_code, offense_name, namespace="fbi") or "all"
    result = _per_capita_by_race(
        state=state,
        offense_code=offense_code,
        start_date=start_date,
        end_date=end_date,
        year=year,
        raw=raw,
        debug=debug,
    )
    _emit(result, output_format, output_dest, raw)


if __name__ == "__main__":
    fbi()
