# from os import nice
from pydantic import BaseModel, Field
import pandas as pd


class FBIOffense(BaseModel):
    code: int = Field(..., description="FBI Offense Code")
    name: str = Field(..., description="FBI Offense Name")
    category: str = Field(..., description="FBI Offense Category")
    short_name: str = Field(..., description="FBI Offense Short Name")


class NIBRSOffense(BaseModel):
    code: str = Field(..., description="NIBRS Offense Code")
    name: str = Field(..., description="NIBRS Offense Name")
    category: str = Field(..., description="NIBRS Offense Category")
    short_name: str = Field(..., description="NIBRS Offense Short Name")


class State(BaseModel):
    fips: str = Field(..., description="FIPS Code")
    abbr: str = Field(..., description="State Abbreviation")
    name: str = Field(..., description="State Name")
    region: str = Field(..., description="State Region")


us_offense_mapping: dict[int, str] = {
    11: {
        "name": "Murder and Nonnegligent Manslaughter",
        "category": "Violent Crime",
        "short_name": "Murder",
    },
    12: {
        "name": "Manslaughter by Negligence",
        "category": "Violent Crime",
        "short_name": "Manslaughter",
    },
    23: {"name": "Rape", "category": "Violent Crime", "short_name": "Rape"},
    30: {"name": "Robbery", "category": "Violent Crime", "short_name": "Robbery"},
    55: {
        "name": "Simple Assault",
        "category": "Violent Crime",
        "short_name": "Assault",
    },
    70: {
        "name": "Larceny - Theft",
        "category": "Property Crime",
        "short_name": "Theft",
    },
    90: {
        "name": "Motor Vehicle Theft",
        "category": "Property Crime",
        "short_name": "Motor Vehicle Theft",
    },
    110: {"name": "Arson", "category": "Property Crime", "short_name": "Arson"},
    150: {
        "name": "Drug Abuse Violations",
        "category": "Drug Crime",
        "short_name": "Drug Abuse",
    },
    152: {
        "name": "Drug Sale and Manufacturing - Opium, Cocaine or Their Derivatives",
        "category": "Drug Crime",
        "short_name": "Drug Sale - Opium/Cocaine",
    },
    153: {
        "name": "Drug Sale and Manufacturing - Marijuana",
        "category": "Drug Crime",
        "short_name": "Drug Sale - Marijuana",
    },
    155: {
        "name": "Drug Sale and Manufacturing - Dangerous Nonnarcotic Drugs",
        "category": "Drug Crime",
        "short_name": "Drug Sale - Dangerous Nonnarcotic Drugs",
    },
    157: {
        "name": "Drug Possession - Opium, Cocaine or Their Derivatives",
        "category": "Drug Crime",
        "short_name": "Drug Possession - Opium/Cocaine",
    },
    158: {
        "name": "Drug Possession - Marijuana",
        "category": "Drug Crime",
        "short_name": "Drug Possession - Marijuana",
    },
    159: {
        "name": "Drug Possession - Synthetic Narcotics",
        "category": "Drug Crime",
        "short_name": "Drug Possession - Synthetic Narcotics",
    },
    160: {
        "name": "Drug Possession - Dangerous Nonnarcotic Drugs",
        "category": "Drug Crime",
        "short_name": "Drug Possession - Dangerous Nonnarcotic Drugs",
    },
    180: {
        "name": "Forgery and Counterfeiting",
        "category": "Property Crime",
        "short_name": "Forgery",
    },
    190: {"name": "Fraud", "category": "Property Crime", "short_name": "Fraud"},
    200: {
        "name": "Embezzlement",
        "category": "Property Crime",
        "short_name": "Embezzlement",
    },
    240: {
        "name": "Sex Offenses (Except Rape and Prostitution and Commercialized Vice)",
        "category": "Sex Crime",
        "short_name": "Sex Offenses",
    },
    280: {
        "name": "Drunkenness",
        "category": "Public Order Crime",
        "short_name": "Drunkenness",
    },
    310: {
        "name": "All Other Offenses (Except Traffic)",
        "category": "Other",
        "short_name": "All Other Offenses",
    },
}

nibrs_offense_mapping: dict[str, dict[str, str]] = {
    "ASS": {
        "name": "Aggravated Assault",
        "category": "Violent Crime",
        "short_name": "Aggravated Assault",
    },
    "13A": {
        "name": "Aggravated Assault",
        "category": "Violent Crime",
        "short_name": "Aggravated Assault",
    },
    "HOM": {"name": "Homicide", "category": "Violent Crime", "short_name": "Homicide"},
    "RPE": {"name": "Rape", "category": "Violent Crime", "short_name": "Rape"},
    "ROB": {"name": "Robbery", "category": "Violent Crime", "short_name": "Robbery"},
    "120": {
        "name": "Robbery",
        "category": "Violent Crime",
        "short_name": "Robbery",
    },
    "ARS": {"name": "Arson", "category": "Property Crime", "short_name": "Arson"},
    "200": {
        "name": "Arson",
        "category": "Property Crime",
        "short_name": "Arson",
    },
    "BUR": {"name": "Burglary", "category": "Property Crime", "short_name": "Burglary"},
    "220": {
        "name": "Burglary/Breaking & Entering",
        "category": "Property Crime",
        "short_name": "Burglary",
    },
    "LAR": {
        "name": "Larceny-theft",
        "category": "Property Crime",
        "short_name": "Larceny",
    },
    "MVT": {
        "name": "Motor Vehicle Theft",
        "category": "Property Crime",
        "short_name": "Motor Vehicle Theft",
    },
    "240": {
        "name": "Motor Vehicle Theft",
        "category": "Property Crime",
        "short_name": "Motor Vehicle Theft",
    },
    "23H": {
        "name": "All Other Larceny",
        "category": "Property Crime",
        "short_name": "Other Larceny",
    },
    "720": {
        "name": "Animal Cruelty",
        "category": "Public Order Crime",
        "short_name": "Animal Cruelty",
    },
    "40B": {
        "name": "Assisting or Promoting Prostitution",
        "category": "Sex Crime",
        "short_name": "Promoting Prostitution",
    },
    "39A": {
        "name": "Betting/Wagering",
        "category": "Public Order Crime",
        "short_name": "Betting/Wagering",
    },
    "510": {
        "name": "Bribery",
        "category": "White Collar Crime",
        "short_name": "Bribery",
    },
    "250": {
        "name": "Counterfeiting/Forgery",
        "category": "White Collar Crime",
        "short_name": "Counterfeiting/Forgery",
    },
    "26B": {
        "name": "Credit Card/Automated Teller Machine Fraud",
        "category": "White Collar Crime",
        "short_name": "Credit Card Fraud",
    },
    "11A": {
        "name": "Rape",
        "category": "Sex Crime",
        "short_name": "Rape",
    },
    "11B": {
        "name": "Sodomy",
        "category": "Sex Crime",
        "short_name": "Sodomy",
    },
    "11C": {
        "name": "Sexual Assault With An Object",
        "category": "Sex Crime",
        "short_name": "Sexual Assault With Object",
    },
    "11D": {
        "name": "Criminal Sexual Contact",
        "category": "Sex Crime",
        "short_name": "Criminal Sexual Contact",
    },
    "290": {
        "name": "Destruction/Damage/Vandalism of Property",
        "category": "Property Crime",
        "short_name": "Vandalism",
    },
    "35B": {
        "name": "Drug Equipment Violations",
        "category": "Drug Crime",
        "short_name": "Drug Equipment",
    },
    "35A": {
        "name": "Drug/Narcotic Violations",
        "category": "Drug Crime",
        "short_name": "Drug Violations",
    },
    "270": {
        "name": "Embezzlement",
        "category": "White Collar Crime",
        "short_name": "Embezzlement",
    },
    "103": {
        "name": "Espionage",
        "category": "National Security",
        "short_name": "Espionage",
    },
    "526": {
        "name": "Explosives Violation",
        "category": "Public Order Crime",
        "short_name": "Explosives Violation",
    },
    "58B": {
        "name": "Export Violations",
        "category": "White Collar Crime",
        "short_name": "Export Violations",
    },
    "210": {
        "name": "Extortion/Blackmail",
        "category": "White Collar Crime",
        "short_name": "Extortion/Blackmail",
    },
    "360": {
        "name": "Failure to Register as a Sex Offender",
        "category": "Sex Crime",
        "short_name": "Failure to Register",
    },
    "30B": {
        "name": "False Citizenship",
        "category": "Public Order Crime",
        "short_name": "False Citizenship",
    },
    "26A": {
        "name": "False Pretenses/Swindle/Confidence Game",
        "category": "White Collar Crime",
        "short_name": "Fraud/Swindle",
    },
    "61A": {
        "name": "Federal Liquor Offenses",
        "category": "Public Order Crime",
        "short_name": "Federal Liquor Offense",
    },
    "61B": {
        "name": "Federal Tobacco Offenses",
        "category": "Public Order Crime",
        "short_name": "Federal Tobacco Offense",
    },
    "49C": {
        "name": "Flight to Avoid Deportation",
        "category": "Public Order Crime",
        "short_name": "Flight to Avoid Deportation",
    },
    "49B": {
        "name": "Flight to Avoid Prosecution",
        "category": "Public Order Crime",
        "short_name": "Flight to Avoid Prosecution",
    },
    "39C": {
        "name": "Gambling Equipment Violation",
        "category": "Public Order Crime",
        "short_name": "Gambling Equipment",
    },
    "26G": {
        "name": "Hacking/Computer Invasion",
        "category": "Cybercrime",
        "short_name": "Hacking",
    },
    "49A": {
        "name": "Harboring Escapee/Concealing from Arrest",
        "category": "Public Order Crime",
        "short_name": "Harboring Escapee",
    },
    "64A": {
        "name": "Human Trafficking, Commercial Sex Acts",
        "category": "Sex Crime",
        "short_name": "Human Trafficking (Sex)",
    },
    "64B": {
        "name": "Human Trafficking, Involuntary Servitude",
        "category": "Violent Crime",
        "short_name": "Human Trafficking (Labor)",
    },
    "26F": {
        "name": "Identity Theft",
        "category": "White Collar Crime",
        "short_name": "Identity Theft",
    },
    "30A": {
        "name": "Illegal Entry into the United States",
        "category": "Public Order Crime",
        "short_name": "Illegal Entry",
    },
    "26C": {
        "name": "Impersonation",
        "category": "White Collar Crime",
        "short_name": "Impersonation",
    },
    "58A": {
        "name": "Import Violations",
        "category": "White Collar Crime",
        "short_name": "Import Violations",
    },
    "36A": {"name": "Incest", "category": "Sex Crime", "short_name": "Incest"},
    "13C": {
        "name": "Intimidation",
        "category": "Violent Crime",
        "short_name": "Intimidation",
    },
    "09C": {
        "name": "Justifiable Homicide",
        "category": "Other",
        "short_name": "Justifiable Homicide",
    },
    "100": {
        "name": "Kidnapping/Abduction",
        "category": "Violent Crime",
        "short_name": "Kidnapping",
    },
    "26H": {
        "name": "Money Laundering",
        "category": "White Collar Crime",
        "short_name": "Money Laundering",
    },
    "09A": {
        "name": "Murder and Nonnegligent Manslaughter",
        "category": "Violent Crime",
        "short_name": "Murder",
    },
    "09B": {
        "name": "Negligent Manslaughter",
        "category": "Violent Crime",
        "short_name": "Manslaughter",
    },
    "23*": {
        "name": "Not Specified",
        "category": "Other",
        "short_name": "Not Specified",
    },
    "39B": {
        "name": "Operating/Promoting/Assisting Gambling",
        "category": "Public Order Crime",
        "short_name": "Promoting Gambling",
    },
    "23A": {
        "name": "Pocket-picking",
        "category": "Property Crime",
        "short_name": "Pocket-picking",
    },
    "370": {
        "name": "Pornography/Obscene Material",
        "category": "Sex Crime",
        "short_name": "Pornography",
    },
    "40A": {
        "name": "Prostitution",
        "category": "Sex Crime",
        "short_name": "Prostitution",
    },
    "40C": {
        "name": "Purchasing Prostitution",
        "category": "Sex Crime",
        "short_name": "Purchasing Prostitution",
    },
    "23B": {
        "name": "Purse-snatching",
        "category": "Property Crime",
        "short_name": "Purse-snatching",
    },
    "30D": {
        "name": "Re-entry after Deportation",
        "category": "Public Order Crime",
        "short_name": "Re-entry After Deportation",
    },
    "23C": {
        "name": "Shoplifting",
        "category": "Property Crime",
        "short_name": "Shoplifting",
    },
    "13B": {
        "name": "Simple Assault",
        "category": "Violent Crime",
        "short_name": "Simple Assault",
    },
    "30C": {
        "name": "Smuggling Aliens",
        "category": "Public Order Crime",
        "short_name": "Smuggling Aliens",
    },
    "39D": {
        "name": "Sports Tampering",
        "category": "White Collar Crime",
        "short_name": "Sports Tampering",
    },
    "36B": {
        "name": "Statutory Rape",
        "category": "Sex Crime",
        "short_name": "Statutory Rape",
    },
    "280": {
        "name": "Stolen Property Offenses",
        "category": "Property Crime",
        "short_name": "Stolen Property",
    },
    "23D": {
        "name": "Theft From Building",
        "category": "Property Crime",
        "short_name": "Theft From Building",
    },
    "23E": {
        "name": "Theft From Coin-Operated Machine or Device",
        "category": "Property Crime",
        "short_name": "Theft From Machine",
    },
    "23F": {
        "name": "Theft From Motor Vehicle",
        "category": "Property Crime",
        "short_name": "Theft From Vehicle",
    },
    "23G": {
        "name": "Theft of Motor Vehicle Parts or Accessories",
        "category": "Property Crime",
        "short_name": "Theft of Vehicle Parts",
    },
    "101": {
        "name": "Treason",
        "category": "National Security",
        "short_name": "Treason",
    },
    "521": {
        "name": "Violation of National Firearm Act of 1934",
        "category": "Weapons Crime",
        "short_name": "Firearm Act Violation",
    },
    "520": {
        "name": "Weapon Law Violations",
        "category": "Weapons Crime",
        "short_name": "Weapon Law Violations",
    },
    "522": {
        "name": "Weapons of Mass Destruction",
        "category": "National Security",
        "short_name": "WMD",
    },
    "26D": {
        "name": "Welfare Fraud",
        "category": "White Collar Crime",
        "short_name": "Welfare Fraud",
    },
    "620": {
        "name": "Wildlife Trafficking",
        "category": "Public Order Crime",
        "short_name": "Wildlife Trafficking",
    },
    "26E": {
        "name": "Wire Fraud",
        "category": "White Collar Crime",
        "short_name": "Wire Fraud",
    },
}

legacy_offense_codes = [
    FBIOffense(code=code, **info) for code, info in us_offense_mapping.items()
]

nibrs_offense_codes = [
    NIBRSOffense(code=code, **info) for code, info in nibrs_offense_mapping.items()
]


def get_offense_from_code(code: int) -> str:
    return us_offense_mapping.get(code, {}).get("name", None)


def get_code_from_offense(name: str) -> int:
    for code, info in us_offense_mapping.items():
        if info.get("name", "").lower() == name.lower():
            return code
    return None


us_territory_mapping: dict[str, dict[str, str]] = {
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


def get_state_from_abbr(abbr):
    return us_territory_mapping.get(abbr, {}).get("name", None)


def get_abbr_from_state(name):
    for abbr, info in us_territory_mapping.items():
        if info.get("name", "").lower() == name.lower():
            return abbr
    return None
