#!/usr/bin/env python3
"""Fetches 2014-2023 annual state-level reported-rape rates from the FBI's
Crime Data Explorer (CDE) public summarized-crime API and writes
data/fbi_cde_state_rape_trend_2014_2023.csv.

CDE's "summarized" endpoint returns one rate-per-100k value per *month*
(incidents that month / population * 100,000) -- not an annual or rolling
rate. We sum the 12 monthly values for each calendar year to get an annual
rate, which is the standard way to read this series.

No API key is required for this endpoint (confirmed empirically -- it's the
same endpoint CDE's own web app calls). Re-run this script to refresh the
CSV if CDE later finalizes/revises a year's data.
"""
import csv
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/fbi_cde_state_rape_trend_2014_2023.csv"

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL",
          "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
          "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
          "TN","TX","UT","VT","VA","WA","WV","WI","WY"]

SOURCE_URL = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend"
SOURCE_NAME = "FBI Crime Data Explorer, Rape (NIBRS offense 11A), state summarized monthly rates summed to annual"


def fetch_state(abbr):
    url = f"https://cde.ucr.cjis.gov/LATEST/summarized/state/{abbr}/RPE?from=01-2014&to=12-2023&type=rates"
    with urllib.request.urlopen(url, timeout=20) as r:
        d = json.load(r)
    rates = d["offenses"]["rates"]
    key = next((k for k in rates if "Offenses" in k and "Clearances" not in k), None)
    if not key:
        raise RuntimeError(f"{abbr}: no offenses key in response, got {list(rates.keys())}")
    monthly = rates[key]
    annual = {}
    for mk, v in monthly.items():
        if v is None:
            continue
        _, yr = mk.split("-")
        annual.setdefault(yr, 0.0)
        annual[yr] += v
    return {yr: round(val, 2) for yr, val in sorted(annual.items())}


def main():
    rows = []
    for abbr in STATES:
        annual = fetch_state(abbr)
        for yr, rate in annual.items():
            rows.append({
                "state_abbr": abbr,
                "year": yr,
                "rate_per_100k": rate,
                "source_url": SOURCE_URL,
                "source_name": SOURCE_NAME,
                "pulled_date": time.strftime("%Y-%m-%d"),
            })
        time.sleep(0.05)

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["state_abbr", "year", "rate_per_100k", "source_url", "source_name", "pulled_date"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows ({len(STATES)} states x up to 10 years) to {OUT}")


if __name__ == "__main__":
    main()
