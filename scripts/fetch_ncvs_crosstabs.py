#!/usr/bin/env python3
"""Computes rape/sexual assault cross-tabs that BJS doesn't publish in its
reports, from the NCVS Select public-use API, and writes
data/ncvs_select_rsa_crosstabs.json.

  - rate per 1,000 persons per year by household income (hincome2, 2017-2024)
  - percent reported to police by victim race/Hispanic origin (2015-2024)
  - offender sex distribution for female and male victims (2015-2024)

Method follows BJS's NCVS Select guidance: victimizations are summed with
the series-adjusted weight (newwgt); populations with the person weight
(wgtpercy). Years are pooled because a single year has only ~80-190
rape/sexual assault sample cases. Validation (printed on every run): the
same method reproduces BJS's published 2023 and 2024 totals, rates, and
percent reported (Criminal Victimization 2024, Tables 1 and 4).

The Select files don't carry the survey's design variables, so standard
errors can't be computed here. Each cell carries its unweighted case count;
the page suppresses cells under 30 cases and flags cells under 50.
"""
import json
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/ncvs_select_rsa_crosstabs.json"
VICT = "https://api.ojp.gov/bjsdataset/v1/gcuy-rt5g.json"
POP = "https://api.ojp.gov/bjsdataset/v1/r4j4-fdwx.json"

INCOME = {"1": "Less than $25,000", "2": "$25,000–$49,999", "3": "$50,000–$99,999",
          "4": "$100,000–$199,999", "5": "$200,000 or more"}
RACE = {"1": "Non-Hispanic white", "2": "Non-Hispanic Black", "3": "Non-Hispanic American Indian/Alaska Native",
        "4": "Non-Hispanic Asian/Native Hawaiian/Other Pacific Islander", "5": "Non-Hispanic more than one race",
        "6": "Hispanic"}
OFFSEX = {"1": "Male", "2": "Female", "3": "Both male and female", "4": "Unknown", "98": "Residue"}


def get(url, params):
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{q}", timeout=120) as r:
        return json.load(r)


def wsum(rows):
    return sum(float(r["newwgt"]) for r in rows)


def main():
    vict = get(VICT, {"$where": "newoff='1'", "$limit": 50000})
    pop_year = {r["year"]: float(r["pop"]) for r in get(POP, {
        "$select": "year, sum(wgtpercy::number) as pop", "$group": "year", "$limit": 100})}
    pop_inc = {r["hincome2"]: float(r["pop"]) for r in get(POP, {
        "$select": "hincome2, sum(wgtpercy::number) as pop", "$where": "year >= '2017'",
        "$group": "hincome2", "$limit": 100})}

    validation = {}
    for y in ("2023", "2024"):
        rows = [r for r in vict if r["year"] == y]
        w = wsum(rows)
        validation[y] = {
            "victimizations": round(w), "rate_per_1000": round(1000 * w / pop_year[y], 2),
            "pct_reported": round(100 * wsum([r for r in rows if r["notify"] == "1"]) / w, 1),
            "cases": len(rows),
        }
    print("validation vs BJS Criminal Victimization 2024 (2023: 481,020 / 1.7 / 46.0%; 2024: 560,890 / 2.0 / 23.6%):")
    print(json.dumps(validation, indent=1))

    v17 = [r for r in vict if int(r["year"]) >= 2017]
    income = [{"code": k, "label": lab, "cases": len(rows := [r for r in v17 if r["hincome2"] == k]),
               "rate_per_1000": round(1000 * wsum(rows) / pop_inc[k], 2)} for k, lab in INCOME.items()]

    v15 = [r for r in vict if int(r["year"]) >= 2015]
    race = []
    for k, lab in RACE.items():
        rows = [r for r in v15 if r["race_ethnicity"] == k]
        if rows:
            race.append({"code": k, "label": lab, "cases": len(rows),
                         "pct_reported": round(100 * wsum([r for r in rows if r["notify"] == "1"]) / wsum(rows), 1)})

    offender_sex = {}
    for sx, name in (("2", "female_victims"), ("1", "male_victims")):
        rows = [r for r in v15 if r["sex"] == sx]
        tot = wsum(rows)
        offender_sex[name] = [{"code": k, "label": lab, "cases": len(rr := [r for r in rows if r["offendersex"] == k]),
                               "pct": round(100 * wsum(rr) / tot, 1)} for k, lab in OFFSEX.items()]

    out = {
        "source": "BJS NCVS Select (Personal Victimization gcuy-rt5g, Personal Population r4j4-fdwx), via api.ojp.gov",
        "offense": "Rape/sexual assault (newoff = 1)",
        "validation": validation,
        "income_rate_2017_2024": income,
        "race_pct_reported_2015_2024": race,
        "offender_sex_2015_2024": offender_sex,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
