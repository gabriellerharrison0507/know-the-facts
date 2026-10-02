#!/usr/bin/env python3
"""Fetches 2014-2023 annual state-level reported-rape rates (and clearance
rates) from the FBI's Crime Data Explorer (CDE) public summarized-crime API
and writes data/fbi_cde_state_rape_trend_2014_2023.csv and
data/fbi_cde_state_rape_clearance_2014_2023.csv.

CDE's "summarized" endpoint returns one rate-per-100k value per *month*
(incidents that month / population * 100,000) -- not an annual or rolling
rate -- for both "Offenses" and "Clearances" (cases cleared by arrest or
exception). We sum the 12 monthly values for each calendar year to get an
annual rate. Clearance rate (the standard criminology stat -- percent of
reported cases cleared by arrest) is clearances/offenses: since both are
rates over the same population denominator, that ratio is a true
percentage and the population term cancels out.

No API key is required for this endpoint (confirmed empirically -- it's the
same endpoint CDE's own web app calls). Re-run this script to refresh the
CSVs if CDE later finalizes/revises a year's data.
"""
import csv
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/fbi_cde_state_rape_trend_2014_2023.csv"
OUT_CLEARANCE = ROOT / "data/fbi_cde_state_rape_clearance_2014_2023.csv"

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL",
          "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
          "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
          "TN","TX","UT","VT","VA","WA","WV","WI","WY"]

SOURCE_URL = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend"
SOURCE_NAME = "FBI Crime Data Explorer, Rape (NIBRS offense 11A), state summarized monthly rates summed to annual"


def _annual_sum(monthly):
    annual = {}
    for mk, v in monthly.items():
        if v is None:
            continue
        _, yr = mk.split("-")
        annual.setdefault(yr, 0.0)
        annual[yr] += v
    return {yr: val for yr, val in sorted(annual.items())}


def fetch_state(abbr):
    url = f"https://cde.ucr.cjis.gov/LATEST/summarized/state/{abbr}/RPE?from=01-2014&to=12-2023&type=rates"
    with urllib.request.urlopen(url, timeout=20) as r:
        d = json.load(r)
    rates = d["offenses"]["rates"]
    off_key = next((k for k in rates if "Offenses" in k and "Clearances" not in k), None)
    clr_key = next((k for k in rates if "Clearances" in k), None)
    if not off_key or not clr_key:
        raise RuntimeError(f"{abbr}: missing offenses/clearances key, got {list(rates.keys())}")
    offenses = _annual_sum(rates[off_key])
    clearances = _annual_sum(rates[clr_key])
    return offenses, clearances


def main():
    rate_rows = []
    clearance_rows = []
    for abbr in STATES:
        offenses, clearances = fetch_state(abbr)
        for yr, rate in offenses.items():
            rate_rows.append({
                "state_abbr": abbr,
                "year": yr,
                "rate_per_100k": round(rate, 2),
                "source_url": SOURCE_URL,
                "source_name": SOURCE_NAME,
                "pulled_date": time.strftime("%Y-%m-%d"),
            })
        for yr, off_v in offenses.items():
            clr_v = clearances.get(yr)
            if clr_v is None or off_v == 0:
                continue
            clearance_rows.append({
                "state_abbr": abbr,
                "year": yr,
                "clearance_rate_pct": round(100 * clr_v / off_v, 1),
                "source_url": SOURCE_URL,
                "source_name": SOURCE_NAME,
                "pulled_date": time.strftime("%Y-%m-%d"),
            })
        time.sleep(0.05)

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["state_abbr", "year", "rate_per_100k", "source_url", "source_name", "pulled_date"])
        w.writeheader()
        w.writerows(rate_rows)
    print(f"Wrote {len(rate_rows)} rows to {OUT}")

    with open(OUT_CLEARANCE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["state_abbr", "year", "clearance_rate_pct", "source_url", "source_name", "pulled_date"])
        w.writeheader()
        w.writerows(clearance_rows)
    print(f"Wrote {len(clearance_rows)} rows to {OUT_CLEARANCE}")


if __name__ == "__main__":
    main()
