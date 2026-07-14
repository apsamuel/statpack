# fbi

The FBI (Federal Bureau of Investigation) is the principal federal investigative agency and domestic intelligence service of the United States. It operates under the jurisdiction of the U.S. Department of Justice and is tasked with investigating and enforcing federal laws.

## NIBRS Data Source

This data source provides access to the FBI's National Incident-Based Reporting System (NIBRS) data. NIBRS is a comprehensive, incident-based reporting system that collects detailed information on crimes reported to law enforcement agencies across the United States.

[2025.1 NIBRS XML Schema](https://le.fbi.gov/file-repository/nibrs-iepd-2025-0-1.zip/@@download/file/NIBRS%202025.0.1.zip)

## Per-capita arrest rates by race

The `per-capita-by-race` subcommand joins FBI arrest counts (numerator) with
U.S. Census population estimates (denominator) to produce per-capita arrest
rates broken down by race.

```bash
statpack fbi per-capita-by-race \
  --state NY \
  --offense-code all \
  --start-date 01-2024 \
  --end-date 12-2024 \
  --year 2024 \
  --format table
```

Options:

- `--state` (required) — state abbreviation or name.
- `--offense-code` / `--offense-name` — FBI offense to count (defaults to `all`).
- `--start-date` / `--end-date` (required) — arrest date range as `MM-YYYY`.
- `--year` — Census population estimate year used as the denominator (default `2024`).
- Standard output options (`--format`, `--output`, `--raw`, `--debug`).

Each output row reports `arrests`, `population`, and the rate `per_100000`
for one canonical OMB race category.

### Caveats

- **Five race categories only.** Rates are reported for the five OMB race
  categories the FBI arrest data exposes: White, Black or African American,
  American Indian or Alaska Native, Asian, and Native Hawaiian or Other
  Pacific Islander. FBI arrest data has **no Hispanic/Latino category**, so
  Hispanic ethnicity is not reported here (it overlaps every race and is never
  summed with race-alone counts).
- **Aggregate vs. annual date alignment.** Arrests are summed over the full
  `--start-date`/`--end-date` range, while the denominator is a single-year
  Census estimate (`--year`). Choose a range and year that align for a
  meaningful rate.
- FBI arrest buckets that do not map to a canonical race (`Unknown`,
  `Multiple`, `Not Specified`, and the combined Asian/NHPI bucket) are
  excluded from the numerator.
