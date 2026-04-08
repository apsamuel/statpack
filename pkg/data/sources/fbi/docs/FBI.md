# 🔍 FBI Crime Data Explorer (CDE)

**Source:** [FBI Crime Data API](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi)
**Base URL:** `https://api.usa.gov/crime/fbi/cde/`
**Auth:** `API_KEY` query param — [get a key](https://api.data.gov/signup/)
**Format:** JSON (default) or CSV — read-only

---

## 📡 Reporting Systems

| System | Description |
|--------|-------------|
| **SRS** | Summary Reporting System — legacy, aggregated offense counts by location |
| **NIBRS** | National Incident-Based Reporting System — incident-level detail: time, offender/victim demographics, relationships, and circumstance |

> ⚠️ Neither system includes PII. Data should **not** be used to rank or compare jurisdictions — comparing a city → state → national level is acceptable.

---

## 🗂️ API Domains

| Domain | Description |
|--------|-------------|
| 🏢 **Agency** | Law enforcement agencies that have submitted UCR data, queryable by state abbreviation |
| 🚔 **Arrest** | Arrest, citation, and summons counts by offense — national, regional, state, and agency (ORI) level |
| 💀 **Expanded Homicide** | SHR homicide data with circumstances, weapon, victim/offender relationship, and demographics |
| 🏠 **Expanded Property** | Supplemental property crime detail — weapon type, item value, and more |
| 🎯 **Hate Crime** | NIBRS + SRS hate crime incidents with bias motivation and offense type |
| 👮 **Law Enforcement Employees** | Officer/civilian staffing counts reported by agencies |
| 🪦 **LESDC** | Law Enforcement Suicide Data Collection — officer suicide incidents and context |
| 📋 **NIBRS** | Incident-based offense data with offender demographics; counts multiply for multi-offense incidents |
| 📊 **NIBRS Estimations** | Estimated national/regional NIBRS totals extrapolated from participating agencies |
| 📈 **Summarized** | Estimated UCR summary data for all violent and property crime categories, state/region/national |
| ⚡ **Use of Force** | Deaths, serious injuries, and firearm discharges by law enforcement per incident |

---

## 🛠️ Implemented Functions

```python
from pkg.data.sources.fbi import (
    get_reporting_agencies,            # 🏢 all UCR-reporting agencies, all states
    get_arrest_counts_by_state,        # 🚔 arrest rates + totals by state/offense, with demographics
    get_arrest_totals_by_state,        # 🚔 aggregate arrest totals by state/offense
    get_arrest_counts_by_origin,       # 🔦 arrest counts by agency ORI code
    get_arrest_totals_by_origin,       # 🔦 arrest totals by agency ORI code
    get_nibrs_totals_by_state,         # 📋 NIBRS incident totals by state + offense code
    get_summarized_by_state,           # 📈 UCR summarized offense data (rates, actuals, population)
    get_expanded_homicide_counts_by_state,  # 💀 SHR homicide totals by state
)
```

All functions return a **pandas DataFrame** by default, or `list[dict]` when `raw=True`.

---

## 📅 Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | `str` | `MM-YYYY` — start of date range (default: `01-2020`) |
| `end_date` | `str` | `MM-YYYY` — end of date range (default: `12-2020`) |
| `state_abbr` | `str` | Two-letter state abbreviation; `None` = all states |
| `offense_code` | `int/str` | FBI/UCR offense code; `"all"` = all offenses |
| `nibrs_code` | `int` | NIBRS offense code |
| `origin_code` | `str` | Agency ORI code (e.g. `AL0430200`) |
| `raw` | `bool` | Return raw `list[dict]` instead of DataFrame |
| `debug` | `bool` | Print request/response diagnostics |

---

## 🔢 Supported Offense Codes (Summarized)

| Code | Offense |
|------|---------|
| `V` | All Violent Crimes |
| `ASS` | Aggravated Assault |
| `HOM` | Homicide |
| `RPE` | Rape |
| `ROB` | Robbery |
| `P` | All Property Crimes |
| `ARS` | Arson |
| `LAR` | Larceny-Theft |
| `MVT` | Motor Vehicle Theft |

---

## 🌐 Environment Variables

```bash
export GOV_API_BASE_URL="https://api.usa.gov"
export GOV_API_KEY="your_key_here"   # https://api.data.gov/signup/
```

---

## 🔗 Resources

- [API Docs](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi)
- [Data Explorer](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend)
- [NIBRS Offense Codes](https://ucr.fbi.gov/nibrs/2011/resources/nibrs-offense-codes)
- [Downloads](https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/downloads)
