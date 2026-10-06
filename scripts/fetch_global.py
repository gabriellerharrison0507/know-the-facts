#!/usr/bin/env python3
"""Builds data/global_countries.csv for the Global tab: one row per country
with modeled prevalence estimates of violence against women and the World
Bank's coding of each country's laws on it.

Sources:
  - Prevalence: UN Inter-Agency Working Group on Violence Against Women
    Estimation and Data (WHO, UN Women, UNICEF, UNSD, UNFPA, UNODC),
    "Violence against women prevalence estimates, 2023" (WHO, Nov. 2025),
    as published in the World Bank Gender Statistics API:
      SG.VAW.NPSV.15PL.LT.ME.ZS  non-partner sexual violence since age 15
                                 (% of all women 15+)
      SG.VAW.15PL.LT.ME.ZS       physical and/or sexual intimate partner
                                 violence, lifetime (% of ever-partnered
                                 women 15+)
      SG.VAW.15PL.ME.ZS          same, past 12 months
  - Laws: World Bank, Women, Business and the Law 2026, Safety topic,
    Legal Frameworks pillar (data as of Feb. 2026). Each "Yes"/"No" is the
    World Bank's coding of the law in the economy's main business city.

Region aggregates are dropped (kept: economies in the World Bank country
list) except "World" (WLD), which is written as the final row.
Requires openpyxl.
"""
import csv
import io
import json
import pathlib
import urllib.request

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/global_countries.csv"
WBL = "https://wbl.worldbank.org/content/dam/sites/wbl/documents/2026/2026-02-18-WBL26-1-Safety-Data.xlsx"
API = "https://api.worldbank.org/v2"
PREV = {"npsv_lifetime_pct": "SG.VAW.NPSV.15PL.LT.ME.ZS",
        "ipv_lifetime_pct": "SG.VAW.15PL.LT.ME.ZS",
        "ipv_12m_pct": "SG.VAW.15PL.ME.ZS"}
# WBL column code (row 2 of the "1. Safety" sheet) -> output column
LAW = {
    "Saf_Law_DomViolLaw": "dv_law",
    "Saf_Law_DomViol_CrimPen": "dv_criminal_penalties",
    "Saf_Law_DomViol_ProtOrd": "dv_protection_orders",
    "Saf_Law_DomViol_SexualMR": "dv_covers_sexual_incl_marital_rape",
    "Saf_Law_DomViol_SexualMR_LB": "dv_covers_sexual_incl_marital_rape_basis",
    "Saf_Law_SexHar_EplCpCr": "harassment_employment",
    "Saf_Law_SexHar_EduCpCr": "harassment_education",
    "Saf_Law_SexHar_PubCpCr": "harassment_public_places",
    "Saf_Law_SexHar_CybCpCr": "harassment_cyber",
    "Saf_Law_ChildMarr_Age": "marriage_age_18",
    "Saf_Law_ChildMarr_ParEx18": "marriage_no_parental_exception_under_18",
    "Saf_Law_FemicideCr": "femicide_crime",
    "Saf_Law_FemicideAP": "femicide_aggravated_penalties",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def api(path):
    return json.loads(get(f"{API}/{path}{'&' if '?' in path else '?'}format=json&per_page=20000"))


def main():
    countries = {c["id"]: c for c in api("country")[1]}
    economies = {k: c for k, c in countries.items() if c["region"]["id"] != "NA"}

    prev = {}
    for col, ind in PREV.items():
        for x in api(f"country/all/indicator/{ind}?date=2023")[1]:
            # Kosovo comes back with an empty iso3 code; its id is XK
            iso = x["countryiso3code"] or {"XK": "XKX"}.get(x["country"]["id"], "")
            if x["value"] is not None and (iso in economies or iso == "WLD"):
                prev.setdefault(iso, {})[col] = x["value"]

    wb = openpyxl.load_workbook(io.BytesIO(get(WBL)), read_only=True, data_only=True)
    rows = list(wb["1. Safety"].iter_rows(values_only=True))
    codes = rows[1]
    law = {}
    for r in rows[3:]:
        if not r[2]:
            continue
        rec = dict(zip(codes, r))
        iso = {"KSV": "XKX"}.get(r[2], r[2])  # WBL codes Kosovo KSV; the API uses XKX
        law[iso] = {out: (rec[code] or "").strip() for code, out in LAW.items()}
        if iso not in economies:
            # Taiwan is in WBL but not in the API's country list
            economies[iso] = {"name": r[0], "region": {"value": r[3]}}

    isos = sorted(set(law) | (set(prev) - {"WLD"}), key=lambda i: economies[i]["name"])
    fields = ["iso3", "name", "region", *PREV, *LAW.values()]
    out = []
    for iso in isos + ["WLD"]:
        c = economies.get(iso) or countries[iso]
        out.append({"iso3": iso, "name": c["name"].strip(), "region": c["region"]["value"].strip(),
                    **{k: prev.get(iso, {}).get(k, "") for k in PREV},
                    **{k: law.get(iso, {}).get(k, "") for k in LAW.values()}})
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"Wrote {OUT}: {len(out) - 1} countries ({len(law)} with WBL law data, "
          f"{sum(1 for i in isos if 'npsv_lifetime_pct' in prev.get(i, {}))} with non-partner SV estimates); "
          f"World: {prev.get('WLD')}")


if __name__ == "__main__":
    main()
