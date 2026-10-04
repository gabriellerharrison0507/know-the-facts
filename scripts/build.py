#!/usr/bin/env python3
"""Builds index.html from site/index.template.html by substituting fonts and data literals."""
import base64
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def b64(path):
    return base64.b64encode((ROOT / path).read_bytes()).decode("ascii")


def ranks_data_literal():
    ranks = json.loads((ROOT / "data/state_ranks.json").read_text())
    parts = []
    for r in ranks:
        v = "true" if r["reliable_estimate"] else "false"
        rate = r["rape_rate_per_100k"] if r["rape_rate_per_100k"] is not None else "null"
        rank = r["rank"] if r["rank"] is not None else "null"
        parts.append(f"{{n:'{r['state_name']}',r:{rate},k:{rank},v:{v}}}")
    return ",".join(parts)


def sa_state_data_literal():
    parts = []
    with open(ROOT / "data/nisvs_2023_2024_state.csv", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("state"):
                continue
            w = row["women_contact_sv_pct"]
            m = row["men_contact_sv_pct"].strip()
            m_lit = m if m else "null"
            parts.append(f"{{n:'{row['state']}',w:{w},m:{m_lit}}}")
    return ",".join(parts)


def state_paths_literal():
    data = json.loads((ROOT / "assets/map/us-states-paths.json").read_text())
    return json.dumps(data, separators=(",", ":"))


def _state_year_literal(csv_path, value_col):
    by_state = {}
    with open(ROOT / csv_path, newline="") as f:
        for row in csv.DictReader(f):
            by_state.setdefault(row["state_abbr"], []).append(
                {"year": int(row["year"]), "v": float(row[value_col])}
            )
    parts = []
    for abbr, pts in by_state.items():
        pts.sort(key=lambda p: p["year"])
        pts_lit = ",".join(f"{{year:{p['year']},v:{p['v']}}}" for p in pts)
        parts.append(f"{abbr}:[{pts_lit}]")
    return "{" + ",".join(parts) + "}"


def state_trend_literal():
    return _state_year_literal("data/fbi_cde_state_rape_trend_2014_2023.csv", "rate_per_100k")


def state_clearance_literal():
    return _state_year_literal("data/fbi_cde_state_rape_clearance_2014_2023.csv", "clearance_rate_pct")


def state_offense_types_literal():
    by_state = {}
    with open(ROOT / "data/fbi_cde_state_offense_types_2023.csv", newline="") as f:
        for row in csv.DictReader(f):
            by_state.setdefault(row["state_abbr"], []).append(
                {"label": row["offense_label"], "n": int(row["victim_count_2023"])}
            )
    order = {"Rape": 0, "Sodomy": 1, "Sexual Assault With An Object": 2, "Fondling": 3}
    parts = []
    for abbr, items in by_state.items():
        items.sort(key=lambda it: order[it["label"]])
        items_lit = ",".join(f"{{label:'{it['label']}',n:{it['n']}}}" for it in items)
        parts.append(f"{abbr}:[{items_lit}]")
    return "{" + ",".join(parts) + "}"


def _state_category_literal(csv_path, label_col, value_col, order):
    by_state = {}
    with open(ROOT / csv_path, newline="") as f:
        for row in csv.DictReader(f):
            by_state.setdefault(row["state_abbr"], []).append(
                {"label": row[label_col], "n": int(row[value_col])}
            )
    parts = []
    for abbr, items in by_state.items():
        items.sort(key=lambda it: order.index(it["label"]) if it["label"] in order else len(order))
        items_lit = ",".join(f"{{label:'{it['label']}',n:{it['n']}}}" for it in items)
        parts.append(f"{abbr}:[{items_lit}]")
    return "{" + ",".join(parts) + "}"


AGE_ORDER = ["0-9", "10-19", "20-29", "30-39", "40-49", "50+", "Unknown"]
SEX_ORDER = ["Female", "Male", "Unknown/Not Specified"]
RACE_ORDER = ["White", "Black or African American", "American Indian / Alaska Native",
              "Asian / Pacific Islander", "Multiracial", "Unknown"]
ETHNICITY_ORDER = ["Hispanic or Latino", "Not Hispanic or Latino", "Unknown"]
RELATIONSHIP_ORDER = ["Stranger", "Intimate partner", "Other family member", "Acquaintance / friend", "Unknown"]


def state_victim_age_literal():
    return _state_category_literal("data/fbi_cde_state_victim_age_2023.csv", "age_group", "victim_count_2023", AGE_ORDER)


def state_victim_sex_literal():
    return _state_category_literal("data/fbi_cde_state_victim_sex_2023.csv", "sex", "victim_count_2023", SEX_ORDER)


def state_victim_race_literal():
    return _state_category_literal("data/fbi_cde_state_victim_race_2023.csv", "race", "victim_count_2023", RACE_ORDER)


def state_victim_ethnicity_literal():
    return _state_category_literal("data/fbi_cde_state_victim_ethnicity_2023.csv", "ethnicity", "victim_count_2023", ETHNICITY_ORDER)


def state_victim_relationship_literal():
    return _state_category_literal("data/fbi_cde_state_victim_relationship_2023.csv", "relationship_group", "victim_count_2023", RELATIONSHIP_ORDER)


STATE_ABBR = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}
KIT_PILLARS = ["Statewide Inventory", "Test Backlogged Kits", "Test New Kits", "Implement Tracking System",
               "Victim's Right To Know", "Fund Reform"]


def state_kits_literal():
    """End the Backlog's per-state rape kit reform tracker (scraped from each
    state page into data/end_the_backlog_states_raw.json) -> compact JS."""
    import re
    raw = json.loads((ROOT / "data/end_the_backlog_states_raw.json").read_text())

    def status(v):
        v = (v or "").lower()
        if v.startswith("yes"):
            return "yes"
        if v.startswith("in-process") or v.startswith("in process"):
            return "progress"
        if v.startswith("no"):
            return "no"
        return "unknown"

    def count(v):
        n = re.sub(r"[^0-9]", "", v or "")
        return int(n) if n else None

    out = {}
    for name, v in raw.items():
        years = {n["mark"]: n["year"] for n in (v.get("notes") or [])}
        ta = re.search(r"(\d+)\s*days", v.get("turnaround") or "")
        slug = "washington-d-c" if name == "District of Columbia" else name.lower().replace(" ", "-")
        out[STATE_ABBR[name]] = {
            "p": [status(v["pillars"].get(k)) for k in KIT_PILLARS],
            "now": count(v.get("now")), "nowYear": years.get("*"),
            "then": count(v.get("then")), "thenYear": years.get("**"),
            "testing": v.get("testing"), "reform": v.get("reform"),
            "turnaround": int(ta.group(1)) if ta else None, "slug": slug,
        }
    assert len(out) == 51, len(out)
    return json.dumps(out, separators=(",", ":"))


def clery_literal():
    """Per-state college-reported rapes (Clery Act, 2022-2024), plus a "US"
    row; produced by scripts/fetch_clery.py."""
    out = {}
    with open(ROOT / "data/clery_state_rape_2022_2024.csv", newline="") as f:
        for r in csv.DictReader(f):
            out[r["state_abbr"]] = {
                "inst": int(r["institutions"]), "big": int(r["institutions_1000plus"]),
                "years": [int(r["rape_2022"]), int(r["rape_2023"]), int(r["rape_2024"])],
                "fondl": int(r["fondling_2024"]),
                "zeroAll": float(r["pct_all_zero_rape_2024"]),
                "zeroBig": float(r["pct_1000plus_zero_rape_2024"]) if r["pct_1000plus_zero_rape_2024"] else None,
                "top": r["top_institution_2024"], "topN": int(r["top_institution_rape_2024"]),
            }
    assert len(out) == 52, len(out)
    return json.dumps(out, separators=(",", ":"), ensure_ascii=False)


def is_major_university(r):
    """Residential four-year school with 10,000+ students: 1,000+ beds of
    school-controlled housing, under half its students exclusively online."""
    return (int(r["enrollment"]) >= 10000 and "4-year" in r["sector"]
            and int(r["housing_capacity"] or 0) >= 1000 and float(r["pct_exclusively_online"] or 100) < 50)


def clery_schools_literal():
    """Named schools for the campus sections: per state, the three schools
    with the most 2024 reports and every major university; nationally, the
    top 10 and the zero-report comparison. From data/clery_institutions_2022_2024.csv."""
    rows = list(csv.DictReader(open(ROOT / "data/clery_institutions_2022_2024.csv", newline="")))
    for r in rows:
        r["y"] = [int(r["rape_2022"]), int(r["rape_2023"]), int(r["rape_2024"])]
    item = lambda r: {"n": r["name"], "s": int(r["enrollment"]), "y": r["y"]}
    by_state = {}
    for r in rows:
        by_state.setdefault(r["state_abbr"], []).append(r)
    out = {}
    for st, L in by_state.items():
        top = sorted((r for r in L if r["y"][2] > 0), key=lambda r: (-r["y"][2], r["name"]))[:3]
        major = sorted((r for r in L if is_major_university(r)), key=lambda r: -int(r["enrollment"]))
        out[st] = {"top": [item(r) for r in top], "major": [item(r) for r in major]}
    major = [r for r in rows if is_major_university(r)]
    cc = [r for r in rows if int(r["enrollment"]) >= 10000 and r["sector"].endswith("2-year")]
    zero3 = lambda r: sum(r["y"]) == 0
    out["US"] = {
        "top": [dict(item(r), st=r["state_abbr"]) for r in sorted(rows, key=lambda r: -r["y"][2])[:10]],
        "majorN": len(major), "majorZero": [r["name"] for r in major if zero3(r)],
        "ccN": len(cc), "ccZeroN": sum(1 for r in cc if zero3(r)),
    }
    return json.dumps(out, separators=(",", ":"), ensure_ascii=False)


def main():
    template = (ROOT / "site/index.template.html").read_text()
    out = (
        template
        .replace("__FRAUNCES_B64__", b64("assets/fonts/fraunces.woff2"))
        .replace("__PUBLICSANS_B64__", b64("assets/fonts/publicsans.woff2"))
        .replace("__RANKS_DATA__", ranks_data_literal())
        .replace("__SA_STATE_DATA__", sa_state_data_literal())
        .replace("__STATE_PATHS__", state_paths_literal())
        .replace("__STATE_TREND_DATA__", state_trend_literal())
        .replace("__STATE_CLEARANCE_DATA__", state_clearance_literal())
        .replace("__STATE_OFFENSE_TYPES_DATA__", state_offense_types_literal())
        .replace("__STATE_VICTIM_AGE_DATA__", state_victim_age_literal())
        .replace("__STATE_VICTIM_SEX_DATA__", state_victim_sex_literal())
        .replace("__STATE_VICTIM_RACE_DATA__", state_victim_race_literal())
        .replace("__STATE_VICTIM_ETHNICITY_DATA__", state_victim_ethnicity_literal())
        .replace("__STATE_VICTIM_RELATIONSHIP_DATA__", state_victim_relationship_literal())
        .replace("__STATE_KITS_DATA__", state_kits_literal())
        .replace("__CLERY_DATA__", clery_literal())
        .replace("__CLERY_SCHOOLS_DATA__", clery_schools_literal())
    )
    remaining = [tok for tok in ("__FRAUNCES_B64__", "__PUBLICSANS_B64__", "__RANKS_DATA__", "__SA_STATE_DATA__", "__STATE_PATHS__", "__STATE_TREND_DATA__", "__STATE_CLEARANCE_DATA__", "__STATE_OFFENSE_TYPES_DATA__", "__STATE_VICTIM_AGE_DATA__", "__STATE_VICTIM_SEX_DATA__", "__STATE_VICTIM_RACE_DATA__", "__STATE_VICTIM_ETHNICITY_DATA__", "__STATE_VICTIM_RELATIONSHIP_DATA__", "__STATE_KITS_DATA__", "__CLERY_DATA__", "__CLERY_SCHOOLS_DATA__") if tok in out]
    if remaining:
        raise SystemExit(f"Unsubstituted placeholders remain: {remaining}")

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Know The Facts — Sexual Assault Law &amp; Statistics</title>
<meta name="description" content="State-by-state sexual assault law and survey-based statistics, cited to primary sources.">
</head>
<body>
{out}
</body>
</html>
"""
    (ROOT / "index.html").write_text(document, encoding="utf-8")
    print(f"Wrote index.html ({len(document):,} bytes)")


if __name__ == "__main__":
    main()
