"""Canonical race/ethnicity taxonomy and cross-source crosswalks.

Canonical categories follow the U.S. OMB / Census race classification. Hispanic or
Latino is treated as a separate ethnicity dimension because a person of any race may
also be Hispanic; it is never summed together with the mutually-exclusive race-alone
categories.
"""

# Canonical OMB race categories.
WHITE = "White"
BLACK = "Black or African American"
AIAN = "American Indian or Alaska Native"
ASIAN = "Asian"
NHPI = "Native Hawaiian or Other Pacific Islander"

# Canonical ethnicity (overlaps every race).
HISPANIC = "Hispanic or Latino"

CANONICAL_RACES = [WHITE, BLACK, AIAN, ASIAN, NHPI]
CANONICAL_ETHNICITIES = [HISPANIC]

# FBI "Arrestee Race" labels -> canonical race. Aggregate / unknown FBI buckets
# ("Multiple", "Unknown", "Not Specified", and the combined
# "Asian, Native Hawaiian, or Other Pacific Islander") are intentionally omitted
# because they have no clean canonical or ACS-population counterpart.
FBI_RACE_TO_CANONICAL = {
    "white": WHITE,
    "black or african american": BLACK,
    "american indian or alaska native": AIAN,
    "asian": ASIAN,
    "native hawaiian or other pacific islander": NHPI,
}

# Census ACS variable codes -> canonical category.
ACS_VARIABLE_TO_CANONICAL = {
    "B02001_002E": WHITE,
    "B02001_003E": BLACK,
    "B02001_004E": AIAN,
    "B02001_005E": ASIAN,
    "B02001_006E": NHPI,
    "B03003_003E": HISPANIC,
}


def canonical_from_fbi_race(label: str) -> str | None:
    """Map an FBI arrestee-race label to a canonical category, or None if unmapped."""
    return FBI_RACE_TO_CANONICAL.get(str(label).strip().lower())


def canonical_from_acs_variable(variable: str) -> str | None:
    """Map a Census ACS variable code to a canonical category, or None if unmapped."""
    return ACS_VARIABLE_TO_CANONICAL.get(str(variable).strip())
