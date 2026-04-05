# examples

```sh
curl -X 'GET' \
  'https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/NY?API_KEY=iiHnOKfno2Mgkt5AynpvPpUQTEyxE77jo1RU8PIv' \
  -H 'accept: application/json'
```

```json
{
  "ERIE": [
    {
      "ori": "NY214UC00",
      "counties": "ERIE",
      "is_nibrs": true,
      "latitude": 42.752759,
      "longitude": -78.778192,
      "state_abbr": "NY",
      "state_name": "New York",
      "agency_name": "State University of New York Police: Buffalo State College",
      "agency_type_name": "University or College",
      "nibrs_start_date": "2021-01-01"
    },
    {
      "ori": "NY0142900",
      "counties": "ERIE",
      "is_nibrs": false,
      "latitude": 42.79794,
      "longitude": -78.8298,
      "state_abbr": "NY",
      "state_name": "New York",
      "agency_name": "Blasdell Village Police Department",
      "agency_type_name": "City",
      "nibrs_start_date": null
    },
    {
      "ori": "NY0143000",
      "counties": "ERIE",
      "is_nibrs": true,
      "latitude": 42.71606,
      "longitude": -78.83262,
      "state_abbr": "NY",
      "state_name": "New York",
      "agency_name": "Hamburg Village Police Department",
      "agency_type_name": "City",
      "nibrs_start_date": "2023-01-01"
    },
    ...
  ]
}
```

```sh
curl -X 'GET' \
  'https://api.usa.gov/crime/fbi/cde/shr/state/PA?type=totals&from=01-2025&to=05-2025&API_KEY=FBI_API_KEY' \
  -H 'accept: */*'
```

```json
{
  "victim": {
    "age": {
      "0-9": 7,
      "10-19": 20,
      "20-29": 61,
      "30-39": 45,
      "40-49": 36,
      "50-59": 19,
      "60-69": 11,
      "70-79": 3,
      "80-89": 2,
      "Unknown": 0,
      "90-Older": 0
    },
    "sex": {
      "Male": 151,
      "Female": 53,
      "Unknown": 0,
      "Not Specified": 0
    },
    "race": {
      "Asian": 1,
      "White": 84,
      "Unknown": 0,
      "Multiple": 0,
      "Not Specified": 0,
      "Black or African American": 119,
      "American Indian or Alaska Native": 0,
      "Native Hawaiian or Other Pacific Islander": 0,
      "Asian, Native Hawaiian, or Other Pacific Islander": 0
    },
    "ethnicity": {
      "Unknown": 7,
      "Multiple": 0,
      "Not Specified": 2,
      "Hispanic or Latino": 25,
      "Not Hispanic or Latino": 170
    }
  },
  "offense": {
    "weapons": {
      "Other": 2,
      "Rifle": 8,
      "Poison": 1,
      "Firearm": 24,
      "Handgun": 132,
      "Shotgun": 1,
      "Drowning": 0,
      "Explosives": 0,
      "Asphyxiation": 2,
      "Blunt Object": 3,
      "Other Firearm": 0,
      "Personal Weapons": 7,
      "Motor Vehicle/Vessel": 0,
      "Fire/Incendiary Device": 6,
      "Knife/Cutting Instrument": 14,
      "Pushed or Thrown Out Window": 0,
      "Drugs/Narcotics/Sleeping Pills": 4,
      "Strangulation - Include Hanging": 0
    },
    "circumstance": {
      "Rape": 0,
      "Arson": 1,
      "Other": 33,
      "Larceny": 0,
      "Robbery": 10,
      "Abortion": 0,
      "Burglary": 0,
      "Gambling": 2,
      "Sniper Attack": 0,
      "Other Arguments": 58,
      "Domestic Violence": 8,
      "Gangland Killings": 1,
      "Narcotic Drug Laws": 16,
      "Other Sex Offenses": 0,
      "Motor Vehicle Theft": 0,
      "Other - not specified": 6,
      "Institutional Killings": 1,
      "Juvenile Gang Killings": 0,
      "All Suspected Felony Type": 3,
      "Child Killed by Babysitter": 1,
      "Argument of Money or Property": 1,
      "Brawl Due to Influence of Alcohol": 0,
      "Brawl Due to Influence of Narcotics": 0,
      "Prostitution and Commercialized Vice": 0,
      "Human Trafficking/Commersical Sex Acts": 0,
      "Human Trafficking/Involuntary Servitude": 0,
      "All instances where the facts provided do not permit determination of circumstances": 63
    },
    "relationship": {
      "Son": 2,
      "Wife": 6,
      "Father": 1,
      "Friend": 2,
      "In-Law": 0,
      "Mother": 1,
      "Sister": 0,
      "Brother": 2,
      "Ex-Wife": 0,
      "Husband": 5,
      "Stepson": 1,
      "Unknown": 121,
      "Daughter": 4,
      "Employee": 0,
      "Employer": 0,
      "Neighbor": 1,
      "Stranger": 17,
      "Boyfriend": 3,
      "Ex-Husband": 0,
      "Girlfriend": 9,
      "Stepfather": 0,
      "Stepmother": 0,
      "Acquaintance": 35,
      "Other Family": 2,
      "Stepdaugther": 0,
      "Common-Law Wife": 0,
      "Common-Law Husband": 0,
      "Homosexual Relationship": 0,
      "Other - known to victim": 34
    }
  },
  "offender": {
    "age": {
      "0-9": 0,
      "10-19": 27,
      "20-29": 53,
      "30-39": 51,
      "40-49": 23,
      "50-59": 13,
      "60-69": 6,
      "70-79": 2,
      "80-89": 1,
      "Unknown": 17,
      "90-Older": 0
    },
    "sex": {
      "Male": 152,
      "Female": 25,
      "Unknown": 16,
      "Not Specified": 38
    },
    "race": {
      "Asian": 0,
      "White": 76,
      "Unknown": 16,
      "Multiple": 0,
      "Not Specified": 38,
      "Black or African American": 101,
      "American Indian or Alaska Native": 0,
      "Native Hawaiian or Other Pacific Islander": 0,
      "Asian, Native Hawaiian, or Other Pacific Islander": 0
    },
    "ethnicity": {
      "Unknown": 21,
      "Multiple": 0,
      "Not Specified": 40,
      "Hispanic or Latino": 20,
      "Not Hispanic or Latino": 150
    }
  },
  "cde_properties": {
    "max_data_date": {
      "UCR": "03/2026"
    },
    "last_refresh_date": {
      "UCR": "03/15/2026"
    }
  }
}
```
