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
    )
    remaining = [tok for tok in ("__FRAUNCES_B64__", "__PUBLICSANS_B64__", "__RANKS_DATA__", "__SA_STATE_DATA__", "__STATE_PATHS__", "__STATE_TREND_DATA__", "__STATE_CLEARANCE_DATA__", "__STATE_OFFENSE_TYPES_DATA__", "__STATE_VICTIM_AGE_DATA__", "__STATE_VICTIM_SEX_DATA__", "__STATE_VICTIM_RACE_DATA__", "__STATE_VICTIM_ETHNICITY_DATA__", "__STATE_VICTIM_RELATIONSHIP_DATA__") if tok in out]
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
