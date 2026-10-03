#!/usr/bin/env python3
"""Fetches 2023 state-level reported victim counts for all four NIBRS
Group A sex offense categories from the FBI's Crime Data Explorer public
NIBRS-detail API and writes data/fbi_cde_state_offense_types_2023.csv.

NIBRS splits what UCR's old Summary Reporting System lumped into one
"forcible rape" category into four distinct offenses:
  11A Rape, 11B Sodomy, 11C Sexual Assault With An Object, 11D Fondling
("Criminal Sexual Contact"). There is no separate NIBRS category for
generic "sexual harassment" -- that isn't tracked as a Group A crime the
same way, so it's not included here.

Unlike fetch_cde_trend.py (which uses the /summarized/ endpoint and its
crime-trend rollup codes like RPE), the four individual offense codes are
only queryable via the /nibrs/ endpoint, which returns raw victim counts
rather than a population-adjusted rate -- there's no state-population
denominator in this response. We use victim counts (not rates) here and
present the breakdown as each offense's share of the four-category total,
which doesn't need population normalization. No API key required.
"""
import csv
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/fbi_cde_state_offense_types_2023.csv"

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL",
          "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
          "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
          "TN","TX","UT","VT","VA","WA","WV","WI","WY"]

OFFENSES = {
    "11A": "Rape",
    "11B": "Sodomy",
    "11C": "Sexual Assault With An Object",
    "11D": "Fondling",
}

SOURCE_URL = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend"
SOURCE_NAME = "FBI Crime Data Explorer, NIBRS Group A sex offenses (11A-11D), state summarized monthly rates summed to annual"


FIELDNAMES = ["state_abbr", "offense_code", "offense_label", "victim_count_2023", "source_url", "source_name", "pulled_date"]


def fetch_offense_count(abbr, code):
    # The /summarized/ endpoint only accepts the crime-trend rollup codes
    # (e.g. RPE for all rape). The four individual NIBRS offense codes
    # (11A-11D) are only queryable via /nibrs/, which returns full
    # victim/offense/offender breakdowns rather than a population rate --
    # we use the victim-age-bucket sum as the total victim count for that
    # offense/state/year, since every NIBRS victim record has an age field
    # (possibly "Unknown", but counted).
    url = f"https://cde.ucr.cjis.gov/LATEST/nibrs/state/{abbr}/{code}?from=01-2023&to=12-2023&type=totals"
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                d = json.load(r)
            age = d.get("victim", {}).get("age", {})
            return sum(v for v in age.values() if v is not None)
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
    raise last_err


def already_done():
    done = set()
    if OUT.exists():
        with open(OUT, newline="") as f:
            for row in csv.DictReader(f):
                done.add((row["state_abbr"], row["offense_code"]))
    return done


def main():
    done = already_done()
    is_new = not OUT.exists()
    f = open(OUT, "a", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if is_new:
        w.writeheader()
        f.flush()

    n_written = 0
    n_skipped = 0
    for abbr in STATES:
        for code, label in OFFENSES.items():
            if (abbr, code) in done:
                n_skipped += 1
                continue
            count = fetch_offense_count(abbr, code)
            w.writerow({
                "state_abbr": abbr,
                "offense_code": code,
                "offense_label": label,
                "victim_count_2023": count,
                "source_url": SOURCE_URL,
                "source_name": SOURCE_NAME,
                "pulled_date": time.strftime("%Y-%m-%d"),
            })
            f.flush()
            n_written += 1
            time.sleep(0.05)
        print(f"done: {abbr} ({n_written} written, {n_skipped} already had)", flush=True)

    f.close()
    print(f"Finished: wrote {n_written} new rows, skipped {n_skipped} already-present rows, to {OUT}")


if __name__ == "__main__":
    main()
