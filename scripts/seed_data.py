#!/usr/bin/env python3
"""
Seed data generator for statpack data sources.

Writes expensive-to-collect reference data as JSON files into each
source module's data/ directory so they can be loaded at startup
instead of fetched on every run.

Usage:
    python scripts/seed_data.py fred
    python scripts/seed_data.py fred --root-category-id 0 --filename seed.json
    python scripts/seed_data.py fred --output-dir /tmp/fred-data
"""
import json
import sys
from pathlib import Path

import click

# Ensure the workspace root is on sys.path so `pkg` is importable when the
# script is executed directly (e.g. `python scripts/seed_data.py`).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_FRED_DATA_DIR = _ROOT / "pkg" / "data" / "sources" / "fred" / "data"
_CENSUS_DATA_DIR = _ROOT / "pkg" / "data" / "sources" / "census" / "data"
_FBI_DATA_DIR = _ROOT / "pkg" / "data" / "sources" / "fbi" / "data"


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------


def _seed_fred(output_dir: Path, root_category_id: int, filename: str, verbose: bool) -> None:
    """Fetch FRED categories + series and write to *filename* inside *output_dir*."""
    from pkg.data.sources.fred.models import get_data_model

    click.echo(f"[fred] Starting seed data generation with root_category_id={root_category_id} …")
    data = get_data_model()
    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data.model_dump(), fh, indent=2, default=str)

    click.echo(f"[fred] Seed data written → {output_path}")


# ---------------------------------------------------------------------------
# FBI
# ---------------------------------------------------------------------------


def _seed_fbi(output_dir: Path, filename: str) -> None:
    """Serialize hardcoded FBI/NIBRS offense codes and US territories to *filename*.

    No network calls are made — all data is defined in the module itself.
    This is a one-time export intended to decouple the module from its
    hardcoded definitions so it can be refactored to load from the seed file.
    """
    from pkg.data.sources.fbi.models import get_data_model

    click.echo("[fbi] Building data model from hardcoded definitions …")
    data = get_data_model()
    click.echo(
        f"[fbi] {len(data.fbi_codes)} FBI offense codes, "
        f"{len(data.nibrs_codes_v1)} NIBRS v1 codes, "
        f"{len(data.nibrs_codes_v2)} NIBRS v2 codes, "
        f"{len(data.us_territories)} US territories."
    )

    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data.model_dump(), fh, indent=2, default=str)

    click.echo(f"[fbi] Seed data written → {output_path}")


# ---------------------------------------------------------------------------
# Census
# ---------------------------------------------------------------------------


def _seed_census(output_dir: Path, filename: str) -> None:
    """Fetch Census states + counties and write to *filename* inside *output_dir*."""
    from pkg.data.sources.census.models import get_data_model

    click.echo("[census] Fetching states and counties …")
    data = get_data_model()
    click.echo(f"[census] {len(data.states)} states, {len(data.counties)} counties fetched.")

    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data.model_dump(), fh, indent=2, default=str)

    click.echo(f"[census] Seed data written → {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """Generate seed data files for statpack data sources."""


@cli.command("fred")
@click.option(
    "--output-dir",
    default=str(_FRED_DATA_DIR),
    show_default=True,
    type=click.Path(file_okay=False, writable=True),
    help="Directory to write the seed file into.",
)
@click.option(
    "--root-category-id",
    default=0,
    show_default=True,
    type=int,
    help="FRED category ID to begin recursive traversal from (0 = root).",
)
@click.option("--filename", default="seed.json", show_default=True, help="Name of the output JSON file.")
@click.option("--verbose", is_flag=True, default=False, help="Print each category name as it is collected.")
def cmd_fred(output_dir: str, root_category_id: int, filename: str, verbose: bool) -> None:
    """Fetch FRED categories and series and write seed data to disk."""
    _seed_fred(output_dir=Path(output_dir), root_category_id=root_category_id, filename=filename, verbose=verbose)


@cli.command("census")
@click.option(
    "--output-dir",
    default=str(_CENSUS_DATA_DIR),
    show_default=True,
    type=click.Path(file_okay=False, writable=True),
    help="Directory to write the seed file into.",
)
@click.option("--filename", default="seed.json", show_default=True, help="Name of the output JSON file.")
def cmd_census(output_dir: str, filename: str) -> None:
    """Fetch Census Bureau states and counties and write seed data to disk."""
    _seed_census(output_dir=Path(output_dir), filename=filename)


@cli.command("fbi")
@click.option(
    "--output-dir",
    default=str(_FBI_DATA_DIR),
    show_default=True,
    type=click.Path(file_okay=False, writable=True),
    help="Directory to write the seed file into.",
)
@click.option("--filename", default="seed.json", show_default=True, help="Name of the output JSON file.")
def cmd_fbi(output_dir: str, filename: str) -> None:
    """Serialize hardcoded FBI/NIBRS offense codes and US territories to a seed file."""
    _seed_fbi(output_dir=Path(output_dir), filename=filename)


if __name__ == "__main__":
    cli()
