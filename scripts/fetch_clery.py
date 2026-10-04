#!/usr/bin/env python3
"""Summarizes college-reported rapes per state from the U.S. Department of
Education's Campus Safety and Security (Clery Act) data and writes
data/clery_state_rape_2022_2024.csv.

Source: https://ope.ed.gov/campussafety/ -> Crime2025EXCEL.zip (calendar
years 2022-2024). Requires xlrd (pip install xlrd).

Method:
  - A college's Clery count = on-campus + noncampus + public property
    (residence-hall counts are a subset of on-campus, so they're not added).
  - Files hold one row per campus; branch campuses repeat the parent
    institution's enrollment. Rows are rolled up to the institution (IPEDS
    UNITID = UNITID_P // 1000), summing offenses across campuses and taking
    enrollment once.
  - "Zero reports" is computed per institution, among institutions with
    1,000 or more students, for 2024.
  - The institution with the most 2024 reports is recorded per state, so
    the page can note when one school drives most of a state's total.
  - Only the 50 states + DC are kept (territories dropped); a final "US"
    row summarizes all of them.

These are reports to the school or police, not a measure of how many
assaults happened; see the page's caveats.
"""
import csv
import io
import pathlib
import urllib.request
import zipfile

import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/clery_state_rape_2022_2024.csv"
URL = "https://ope.ed.gov/campussafety/api/dataFiles/file?fileName=Crime2025EXCEL.zip"
FILES = ["Oncampuscrime222324.xls", "Noncampuscrime222324.xls", "Publicpropertycrime222324.xls"]
YEARS = ("22", "23", "24")
STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())


def rows(zf, name):
    sh = xlrd.open_workbook(file_contents=zf.read(name)).sheet_by_index(0)
    head = sh.row_values(0)
    return [dict(zip(head, sh.row_values(i))) for i in range(1, sh.nrows)]


def num(v):
    return float(v) if v not in ("", None) else 0.0


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        zf = zipfile.ZipFile(io.BytesIO(r.read()))

    inst = {}
    for name in FILES:
        for r in rows(zf, name):
            uid = int(r["UNITID_P"]) // 1000
            i = inst.setdefault(uid, {"state": r["State"].strip(), "name": r["INSTNM"].strip(), "enroll": 0.0,
                                      **{f"RAPE{y}": 0.0 for y in YEARS}, "FONDL24": 0.0})
            i["enroll"] = max(i["enroll"], num(r["Total"]))
            for y in YEARS:
                i[f"RAPE{y}"] += num(r[f"RAPE{y}"])
            i["FONDL24"] += num(r["FONDL24"])

    by_state = {}
    for i in inst.values():
        if i["state"] in STATES:
            by_state.setdefault(i["state"], []).append(i)

    def summarize(abbr, L):
        big = [i for i in L if i["enroll"] >= 1000]
        enroll = sum(i["enroll"] for i in L)
        top = max(L, key=lambda i: i["RAPE24"])
        return {
            "state_abbr": abbr,
            "institutions": len(L),
            "institutions_1000plus": len(big),
            "enrollment": int(enroll),
            **{f"rape_20{y}": int(sum(i[f"RAPE{y}"] for i in L)) for y in YEARS},
            "fondling_2024": int(sum(i["FONDL24"] for i in L)),
            "rape_per_10k_students_2024": round(1e4 * sum(i["RAPE24"] for i in L) / enroll, 2) if enroll else "",
            "pct_all_zero_rape_2024": round(100 * sum(1 for i in L if i["RAPE24"] == 0) / len(L), 1),
            "pct_1000plus_zero_rape_2024": round(100 * sum(1 for i in big if i["RAPE24"] == 0) / len(big), 1) if big else "",
            # the single institution with the most 2024 reports, so the page can
            # flag a state total driven mostly by one school
            "top_institution_2024": top["name"],
            "top_institution_rape_2024": int(top["RAPE24"]),
        }

    out = [summarize(st, by_state[st]) for st in sorted(by_state)]
    assert len(out) == 51, len(out)
    out.append(summarize("US", [i for L in by_state.values() for i in L]))

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(out[-1])
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
