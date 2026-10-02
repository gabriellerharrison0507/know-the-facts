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
    )
    remaining = [tok for tok in ("__FRAUNCES_B64__", "__PUBLICSANS_B64__", "__RANKS_DATA__", "__SA_STATE_DATA__", "__STATE_PATHS__", "__STATE_TREND_DATA__", "__STATE_CLEARANCE_DATA__") if tok in out]
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
