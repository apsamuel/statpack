"""Per-capita crime statistics by race, joining FBI arrests with Census population."""

import pandas as pd

from .taxonomy import CANONICAL_RACES, canonical_from_acs_variable, canonical_from_fbi_race


def per_capita_by_race(
    state: str,
    offense_code: str = "all",
    start_date: str | None = None,
    end_date: str | None = None,
    year: int = 2024,
    per: int = 100_000,
    raw: bool = False,
    debug: bool = False,
) -> pd.DataFrame | list[dict]:
    """Compute per-capita arrest rates by race for a single state.

    Combines FBI arrest counts (numerator, aggregated over ``start_date``..``end_date``)
    with Census ACS population estimates (denominator, for ``year``), normalizing both to
    the canonical race taxonomy and joining on race.

    Notes:
        - The FBI "Arrestee Race" table has no Hispanic/Latino category, so the rate is
          reported for the five OMB race categories only.
        - Arrest counts are an aggregate over the full date range while population is an
          annual estimate, so the rate is (aggregate arrests / annual population) * ``per``.

    Args:
        state: State abbreviation or name.
        offense_code: FBI offense code, or "all". Defaults to "all".
        start_date: Arrest range start (MM-YYYY).
        end_date: Arrest range end (MM-YYYY).
        year: Census ACS estimate year for the population denominator.
        per: Rate base (people). Defaults to 100,000.
        raw: When True, return raw list[dict] records instead of a DataFrame.
        debug: Enable verbose debug output on the underlying source calls.

    Returns:
        pd.DataFrame | list[dict]: One row per canonical race with ``arrests``,
        ``population``, and the computed ``per_<per>`` rate.
    """
    # Lazy imports keep the two sources decoupled: importing this module never triggers
    # either source's import-time environment-variable validation.
    from statpack.data.sources.census import get_census_population_by_race
    from statpack.data.sources.fbi import Client as FbiClient

    arrests = FbiClient().get_arrest_race_breakdown_by_state(
        territory=state, offense_code=offense_code, start_date=start_date, end_date=end_date, raw=True, debug=debug
    )

    arrests_by_race: dict[str, int] = {}
    for record in arrests:
        canonical = canonical_from_fbi_race(record.get("race"))
        if canonical is None:
            continue
        arrests_by_race[canonical] = arrests_by_race.get(canonical, 0) + int(record.get("count") or 0)

    population = get_census_population_by_race(states=[state], year=year, raw=True)
    population_by_race: dict[str, int] = {}
    for record in population:
        canonical = canonical_from_acs_variable(record.get("variable"))
        if canonical is None:
            continue
        population_by_race[canonical] = population_by_race.get(canonical, 0) + int(record.get("population") or 0)

    state_name = arrests[0]["territory"] if arrests else state

    rows: list[dict] = []
    for race in CANONICAL_RACES:
        arrests_n = arrests_by_race.get(race)
        population_n = population_by_race.get(race)
        rate = None
        if arrests_n is not None and population_n:
            rate = round(arrests_n / population_n * per, 2)
        rows.append(
            {"state": state_name, "race": race, "arrests": arrests_n, "population": population_n, f"per_{per}": rate}
        )

    if raw:
        return rows
    return pd.DataFrame(rows)
