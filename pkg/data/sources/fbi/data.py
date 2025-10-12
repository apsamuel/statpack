from os import nice
# from pydantic import BaseModel

offense_codes = {
    11: "Murder and Nonnegligent Manslaughter",
    12: "Manslaughter by Negligence",
    23: "Rape",
    30: "Robbery",
    55: "Simple Assault",
    70: "Larceny - Theft",
    90: "Motor Vehicle Theft",
    110: "Arson",
    150: "Drug Abuse Violations",
    152: "Drug Sale and Manufacturing - Opium, Cocaine or Their Derivatives",
    153: "Drug Sale and Manufacturing - Marijuana",
    155: "Drug Sale and Manufacturing - Dangerous Nonnarcotic Drugs",
    157: "Drug Possession - Opium, Cocaine or Their Derivatives",
    158: "Drug Possession - Marijuana",
    159: "Drug Possession - Synthetic Narcotics",
    160: "Drug Possession - Dangerous Nonnarcotic Drugs",
    180: "Forgery and Counterfeiting",
    190: "Fraud",
    200: "Embezzlement",
    240: "Sex Offenses (Except Rape and Prostitution and Commercialized Vice)",
    280: "Drunkenness",
    310: "All Other Offenses (Except Traffic)",
}
united_states_territories = {
    "AL": {"name": "Alabama"},
    "AK": {"name": "Alaska"},
    "AZ": {"name": "Arizona"},
    "AR": {"name": "Arkansas"},
    "CA": {"name": "California"},
    "CO": {"name": "Colorado"},
    "CT": {"name": "Connecticut"},
    "DE": {"name": "Delaware"},
    "FL": {"name": "Florida"},
    "GA": {"name": "Georgia"},
    "HI": {"name": "Hawaii"},
    "ID": {"name": "Idaho"},
    "IL": {"name": "Illinois"},
    "IN": {"name": "Indiana"},
    "IA": {"name": "Iowa"},
    "KS": {"name": "Kansas"},
    "KY": {"name": "Kentucky"},
    "LA": {"name": "Louisiana"},
    "ME": {"name": "Maine"},
    "MD": {"name": "Maryland"},
    "MA": {"name": "Massachusetts"},
    "MI": {"name": "Michigan"},
    "MN": {"name": "Minnesota"},
    "MS": {"name": "Mississippi"},
    "MO": {"name": "Missouri"},
    "MT": {"name": "Montana"},
    "NE": {"name": "Nebraska"},
    "NV": {"name": "Nevada"},
    "NH": {"name": "New Hampshire"},
    "NJ": {"name": "New Jersey"},
    "NM": {"name": "New Mexico"},
    "NY": {"name": "New York"},
    "NC": {"name": "North Carolina"},
    "ND": {"name": "North Dakota"},
    "OH": {"name": "Ohio"},
    "OK": {"name": "Oklahoma"},
    "OR": {"name": "Oregon"},
    "PA": {"name": "Pennsylvania"},
    "RI": {"name": "Rhode Island"},
    "SC": {"name": "South Carolina"},
    "SD": {"name": "South Dakota"},
    "TN": {"name": "Tennessee"},
    "TX": {"name": "Texas"},
    "UT": {"name": "Utah"},
    "VT": {"name": "Vermont"},
    "VA": {"name": "Virginia"},
    "WA": {"name": "Washington"},
    "WV": {"name": "West Virginia"},
    "WI": {"name": "Wisconsin"},
    "WY": {"name": "Wyoming"},
    "DC": {"name": "District of Columbia"},
    "AS": {"name": "American Samoa"},
    "GU": {"name": "Guam"},
    "MP": {"name": "Northern Mariana Islands"},
    "PR": {"name": "Puerto Rico"},
    "VI": {"name": "U.S. Virgin Islands"},
}


# class Origin(BaseModel):
#     ori: str
#     counties: str
#     is_nibrs: bool
#     latitude: float | None
#     longitude: float | None
#     state_abbr: str
#     state_name: str
#     agency_name: str
#     agency_type_name: str | None
#     nibrs_start_date: str | None