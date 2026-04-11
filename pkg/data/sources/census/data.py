from click.utils import R
from pydantic import BaseModel, Field
import time
import pandas as pd
import re
import requests

us_state_mapping: dict[int, str] = {
    1: "Alabama",
    2: "Alaska",
    4: "Arizona",
    5: "Arkansas",
    6: "California",
    8: "Colorado",
    9: "Connecticut",
    10: "Delaware",
    11: "District of Columbia",
    12: "Florida",
    13: "Georgia",
    15: "Hawaii",
    16: "Idaho",
    17: "Illinois",
    18: "Indiana",
    19: "Iowa",
    20: "Kansas",
    21: "Kentucky",
    22: "Louisiana",
    23: "Maine",
    24: "Maryland",
    25: "Massachusetts",
    26: "Michigan",
    27: "Minnesota",
    28: "Mississippi",
    29: "Missouri",
    30: "Montana",
    31: "Nebraska",
    32: "Nevada",
    33: "New Hampshire",
    34: "New Jersey",
    35: "New Mexico",
    36: "New York",
    37: "North Carolina",
    38: "North Dakota",
    39: "Ohio",
    40: "Oklahoma",
    41: "Oregon",
    42: "Pennsylvania",
    44: "Rhode Island",
    45: "South Carolina",
    46: "South Dakota",
    47: "Tennessee",
    48: "Texas",
    49: "Utah",
    50: "Vermont",
    51: "Virginia",
    53: "Washington",
    54: "West Virginia",
    55: "Wisconsin",
    56: "Wyoming",
    72: "Puerto Rico",
}

us_race_mapping: dict[int, str] = {
    1000: "White",
    2790: "Hispanic or Latino",
    3000: "Black or African American",
    4790: "Asian",
    5000: "American Indian or Alaska Native",
    7805: "Native Hawaiian or Other Pacific Islander",
    8000: "Some Other Race",
}


class State(BaseModel):
    code: int
    name: str


class County(BaseModel):
    code: int
    name: str
    state: State


class Race(BaseModel):
    code: int
    name: str


class Request(BaseModel):
    url: str
    params: dict | None = None
    request_headers: dict | None = None
    response_headers: dict | None = None


class FailedRequest(BaseModel):
    url: str
    status_code: int
    reason: str
    timestamp: float = Field(default_factory=time.time)


def _get_county_codes() -> list[County]:
    counties = []
    data = requests.get("https://api.census.gov/data/2024/acs/acs1/cprofile?get=NAME&for=county:*")
    if data.status_code == 200:
        for item in data.json()[1:]:
            name, state_code, county_code = item
            county_name, state_name = name.split(",")
            state = State(code=int(state_code), name=state_name.strip())
            county = County(code=int(county_code), name=county_name.strip(), state=state)
            counties.append(county)
    return counties


def _get_state_codes() -> list[State]:
    states = []
    date = requests.get("https://api.census.gov/data/2024/acs/acs1/cprofile?get=NAME&for=state:*")
    if date.status_code == 200:
        for item in date.json()[1:]:
            name, state_code = item
            state = State(code=int(state_code), name=name.strip())
            states.append(state)
    return states


# def _get_region
state_codes = _get_state_codes()
county_codes = _get_county_codes()


class CensusData(BaseModel):
    # states: list[State] = [State(code=code, name=name) for code, name in us_state_mapping.items()]
    # races: list[Race] = [Race(code=code, name=name) for code, name in us_race_mapping.items()]
    states: list[State] = state_codes
    counties: list[County] = county_codes

    def get_race_by_name(self, name: str) -> Race | None:
        for race in self.races:
            if race.name.lower() == name.lower():
                return race
        return None

    def get_race_by_code(self, code: int) -> Race | None:
        for race in self.races:
            if race.code == code:
                return race
        return None

    def get_state_by_name(self, name: str) -> State | None:
        for state in self.states:
            if state.name.lower() == name.lower():
                return state
        return None

    def get_state_by_code(self, code: int) -> State | None:
        for state in self.states:
            if state.code == code:
                return state
        return None
