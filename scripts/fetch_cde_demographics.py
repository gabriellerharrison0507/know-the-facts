#!/usr/bin/env python3
"""Fetches 2023 state-level victim demographics and victim/offender
relationship data for NIBRS offense 11A (Rape) from the FBI's Crime Data
Explorer public NIBRS-detail API, and writes five long-format CSVs under
data/: fbi_cde_state_victim_age_2023.csv, _sex_, _race_, _ethnicity_, and
_relationship_2023.csv.

Scoped to Rape (11A) only, not all four sex-offense categories combined --
victim profiles plausibly differ by offense type, and blending them would
hide that rather than reveal it. (See fetch_cde_offense_types.py for the
four-category breakdown by volume.)

NIBRS's victim/offender relationship field has ~29 raw categories, far too
granular to show directly -- RELATIONSHIP_GROUPS below collapses them into
five standard criminology buckets (stranger / intimate partner / other
family member / acquaintance-friend / unknown), matching how BJS's own
NCVS reporting typically groups this. The collapsing happens here, once,
in a reviewable place, rather than scattered in page-render logic.

Same endpoint and no-API-key situation as fetch_cde_offense_types.py.
"""
import csv
import json
import pathlib
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL",
          "IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE",
          "NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD",
          "TN","TX","UT","VT","VA","WA","WV","WI","WY"]

SOURCE_URL = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend"
SOURCE_NAME = "FBI Crime Data Explorer, NIBRS offense 11A (Rape), state victim demographics, 2023"

AGE_GROUPS = {
    "0-9": "0-9", "10-19": "10-19", "20-29": "20-29", "30-39": "30-39",
    "40-49": "40-49", "50-59": "50+", "60-69": "50+", "70-79": "50+",
    "80-89": "50+", "90-Older": "50+", "Unknown": "Unknown",
}

SEX_GROUPS = {
    "Male": "Male", "Female": "Female",
    "Unknown": "Unknown/Not Specified", "Not Specified": "Unknown/Not Specified",
}

RACE_GROUPS = {
    "White": "White",
    "Black or African American": "Black or African American",
    "American Indian or Alaska Native": "American Indian / Alaska Native",
    "Asian": "Asian / Pacific Islander",
    "Native Hawaiian or Other Pacific Islander": "Asian / Pacific Islander",
    "Asian, Native Hawaiian, or Other Pacific Islander": "Asian / Pacific Islander",
    "Multiple": "Multiracial",
    "Unknown": "Unknown", "Not Specified": "Unknown",
}

ETHNICITY_GROUPS = {
    "Hispanic or Latino": "Hispanic or Latino",
    "Not Hispanic or Latino": "Not Hispanic or Latino",
    "Unknown": "Unknown", "Multiple": "Unknown", "Not Specified": "Unknown",
}

# NIBRS's raw relationship field, collapsed into five standard buckets.
RELATIONSHIP_GROUPS = {
    "Stranger": "Stranger",
    "Spouse": "Intimate partner", "Common-Law Spouse": "Intimate partner",
    "Boyfriend/Girlfriend": "Intimate partner", "Ex-Spouse": "Intimate partner",
    "Ex-Relationship (Ex-Boyfriend/Girlfriend)": "Intimate partner",
    "Homosexual Relationship": "Intimate partner",
    "Cohabitant (non-intimate relationship)": "Intimate partner",
    "Child": "Other family member", "Parent": "Other family member",
    "Sibling": "Other family member", "Grandchild": "Other family member",
    "Grandparent": "Other family member", "Stepchild": "Other family member",
    "Stepparent": "Other family member", "Stepsibling": "Other family member",
    "In-law": "Other family member", "Other Family Member": "Other family member",
    "Foster Child": "Other family member", "Foster Parent": "Other family member",
    "Child of Boyfriend or Girlfriend": "Other family member",
    "Babysittee": "Other family member",
    "Friend": "Acquaintance / friend", "Acquaintance": "Acquaintance / friend",
    "Neighbor": "Acquaintance / friend", "Otherwise Known": "Acquaintance / friend",
    "Employee": "Acquaintance / friend", "Employer": "Acquaintance / friend",
    "Relationship Unknown": "Unknown", "Offender": "Unknown",
}


def fetch_state(abbr):
    url = f"https://cde.ucr.cjis.gov/LATEST/nibrs/state/{abbr}/11A?from=01-2023&to=12-2023&type=totals"
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return json.load(r)
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
    raise last_err


def collapse(raw, group_map):
    out = {}
    for k, v in raw.items():
        if v is None:
            continue
        bucket = group_map.get(k, "Unknown")
        out[bucket] = out.get(bucket, 0) + v
    return out


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def main():
    age_rows, sex_rows, race_rows, eth_rows, rel_rows = [], [], [], [], []
    pulled = time.strftime("%Y-%m-%d")

    for abbr in STATES:
        d = fetch_state(abbr)
        v = d.get("victim", {})

        for bucket, n in collapse(v.get("age", {}), AGE_GROUPS).items():
            age_rows.append({"state_abbr": abbr, "age_group": bucket, "victim_count_2023": n})
        for bucket, n in collapse(v.get("sex", {}), SEX_GROUPS).items():
            sex_rows.append({"state_abbr": abbr, "sex": bucket, "victim_count_2023": n})
        for bucket, n in collapse(v.get("race", {}), RACE_GROUPS).items():
            race_rows.append({"state_abbr": abbr, "race": bucket, "victim_count_2023": n})
        for bucket, n in collapse(v.get("ethnicity", {}), ETHNICITY_GROUPS).items():
            eth_rows.append({"state_abbr": abbr, "ethnicity": bucket, "victim_count_2023": n})
        for bucket, n in collapse(v.get("relationship", {}), RELATIONSHIP_GROUPS).items():
            rel_rows.append({"state_abbr": abbr, "relationship_group": bucket, "victim_count_2023": n})

        print(f"done: {abbr}", flush=True)
        time.sleep(0.05)

    common = {"source_url": SOURCE_URL, "source_name": SOURCE_NAME, "pulled_date": pulled}
    for rows in (age_rows, sex_rows, race_rows, eth_rows, rel_rows):
        for row in rows:
            row.update(common)

    write_csv(ROOT / "data/fbi_cde_state_victim_age_2023.csv",
               ["state_abbr", "age_group", "victim_count_2023", "source_url", "source_name", "pulled_date"], age_rows)
    write_csv(ROOT / "data/fbi_cde_state_victim_sex_2023.csv",
               ["state_abbr", "sex", "victim_count_2023", "source_url", "source_name", "pulled_date"], sex_rows)
    write_csv(ROOT / "data/fbi_cde_state_victim_race_2023.csv",
               ["state_abbr", "race", "victim_count_2023", "source_url", "source_name", "pulled_date"], race_rows)
    write_csv(ROOT / "data/fbi_cde_state_victim_ethnicity_2023.csv",
               ["state_abbr", "ethnicity", "victim_count_2023", "source_url", "source_name", "pulled_date"], eth_rows)
    write_csv(ROOT / "data/fbi_cde_state_victim_relationship_2023.csv",
               ["state_abbr", "relationship_group", "victim_count_2023", "source_url", "source_name", "pulled_date"], rel_rows)


if __name__ == "__main__":
    main()
