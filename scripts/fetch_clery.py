#!/usr/bin/env python3
"""Summarizes college-reported rapes per state from the U.S. Department of
Education's Campus Safety and Security (Clery Act) data and writes
data/clery_state_rape_2022_2024.csv (per state) and
data/clery_institutions_2022_2024.csv (per institution, 1,000+ students).

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

  - Each institution's share of students enrolled exclusively online comes
    from IPEDS Fall 2023 distance-education enrollment (EF2023A_DIST, all
    students), and its student-housing capacity from IPEDS Institutional
    Characteristics 2023-24 (IC2023, revised file, ROOMCAP), so the page's
    list of large schools reporting zero can be limited to residential
    four-year schools rather than commuter or mostly online ones.

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
OUT_INST = ROOT / "data/clery_institutions_2022_2024.csv"
IPEDS_DIST = "https://nces.ed.gov/ipeds/datacenter/data/EF2023A_DIST.zip"
IPEDS_IC = "https://nces.ed.gov/ipeds/datacenter/data/IC2023.zip"
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


def fetch_zip(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return zipfile.ZipFile(io.BytesIO(r.read()))


def online_share():
    """UNITID -> share of all students enrolled exclusively in distance ed."""
    zf = fetch_zip(IPEDS_DIST)
    name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    out = {}
    for r in csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8-sig")):
        r = {k.strip(): v.strip() for k, v in r.items()}
        if r["EFDELEV"] == "1" and r["EFDETOT"] and int(r["EFDETOT"]) > 0:
            out[int(r["UNITID"])] = int(r["EFDEEXC"] or 0) / int(r["EFDETOT"])
    return out


def housing_capacity():
    """UNITID -> institutionally controlled housing capacity (0 if none)."""
    zf = fetch_zip(IPEDS_IC)
    names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    name = next((n for n in names if "_rv" in n.lower()), names[0])
    out = {}
    for r in csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8-sig", errors="replace")):
        r = {k.strip(): v.strip() for k, v in r.items()}
        cap = r.get("ROOMCAP", "")
        out[int(r["UNITID"])] = int(cap) if cap.lstrip("-").isdigit() and int(cap) > 0 else 0
    return out


def main():
    zf = fetch_zip(URL)
    online = online_share()
    housing = housing_capacity()

    inst = {}
    for name in FILES:
        for r in rows(zf, name):
            uid = int(r["UNITID_P"]) // 1000
            i = inst.setdefault(uid, {"state": r["State"].strip(), "name": r["INSTNM"].strip(),
                                      "sector": r["Sector_desc"].strip(), "enroll": 0.0,
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

    inst_rows = sorted(
        ({"unitid": uid, "name": i["name"], "state_abbr": i["state"], "enrollment": int(i["enroll"]),
          "sector": i["sector"],
          "pct_exclusively_online": round(100 * online[uid], 1) if uid in online else "",
          "housing_capacity": housing.get(uid, ""),
          **{f"rape_20{y}": int(i[f"RAPE{y}"]) for y in YEARS}}
         for uid, i in inst.items() if i["state"] in STATES and i["enroll"] >= 1000),
        key=lambda r: (r["state_abbr"], r["name"]))
    with open(OUT_INST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inst_rows[0]))
        w.writeheader()
        w.writerows(inst_rows)
    print(f"Wrote {OUT_INST} ({len(inst_rows)} institutions; "
          f"{sum(1 for r in inst_rows if r['pct_exclusively_online'] == '')} without IPEDS online share)")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
