# SA Law & Stats Resource — Project Plan

**Goal:** a public resource with (1) a clickable US map routing to state-specific pages covering SA law + state stats, and (2) a separate national stats page — built on real, cited data, with a clear "not legal advice" disclaimer throughout.

**v1 scope:** Colorado, New York, Arkansas (chosen as the state with the highest *reported* 2023 FBI rape rate — see note on reported-vs-survey rates below), plus national-level stats. Architecture built so adding the other 47 states later is just "more rows," not a redesign.

---

## Data layer (SQL/Python practice, same lineage-tracking pattern as the 14ers project)

Every table carries `source_url`, `last_verified_date`, and `verified` (boolean) — nothing goes on the public site without a traceable citation.

### Legal tables (hand-curated, like the 14er death data — no clean API exists)

- **`dim_state`** (state_code, state_name)
- **`fact_state_consent_law`** — how consent is legally defined, incapacitation/intoxication rule, age of consent, spousal exemption status (historically significant — worth noting if/when abolished), statute citation, source_url, verified
- **`fact_state_statute_limitations`** — criminal SOL, civil SOL (these differ and matter a lot for survivors deciding whether to pursue anything), source_url, verified
- **`fact_state_mandatory_reporting`** — who's legally required to report (relevant especially for minors), source_url, verified

### Stats tables

- **`fact_state_reported_rate`** — FBI UCR/NIBRS reported rape rate per 100k, by state/year, source_url
- **`fact_state_survey_rate`** — NISVS/NCVS survey-based prevalence, *where state-level data actually exists* (likely only larger states — need to check per state)
- **`fact_national_stats`** — flexible metric/value table for national-level numbers (lifetime prevalence, past-year prevalence, reporting-to-police rate, perpetrator studies, demographic breakdowns), each row tagged with its specific source, survey year, and a `methodology_note` field

### Why two different stats tables, not one

Same reasoning as the 14er project's "don't blend confidence levels" rule: a **reported rate** (FBI) and a **survey-based prevalence rate** (NISVS/NCVS) answer different questions and can't be averaged or compared directly — mixing them into one table would hide that distinction. The site should show both, side by side, with the difference explained, not pick one as "the" number.

---

## Content concepts to source — confirm before heavy research begins

**Per state (CO, NY, AR):**
1. Legal definition of consent + incapacitation rule (your own NY example — can someone legally consent while intoxicated, where's the line)
2. Age of consent
3. Statute of limitations — criminal and civil, separately
4. Mandatory reporting requirements
5. FBI reported rate (2023, primary source)
6. State-level NISVS/NCVS data, if it exists for that state (will check)

**National stats page:**
1. NISVS/NCVS lifetime and past-year prevalence estimates
2. **Behaviorally-specific categories** (NISVS doesn't just ask "were you raped" — it separately asks about specific experiences: completed/attempted rape, sexual coercion, unwanted sexual contact, non-contact unwanted experiences). This directly answers your own question from our conversation — childhood molestation by a relative falls under NISVS's "sexual assault" umbrella as unwanted sexual contact, distinct from (but not lesser than) the narrower "rape" category. Showing this breakdown, not just one blended number, is one of the more useful things the site can do.
3. Reporting-to-police rate (addresses the "most assaults go unreported" claim with an actual number)
4. Perpetrator-rate studies — **shown as a range across studies with methodology notes**, not one cherry-picked number, given how contested this specific stat is
5. Demographic breakdowns (gender, age at first victimization, etc. — as available)

---

## Site layer (after data layer is populated)

- Clickable US map (choropleth-style) — likely prototyped as an Artifact first for fast iteration, before deciding on real hosting/domain
- Per-state page: law summary (with citations) + state stats (with the reported-vs-survey distinction shown clearly)
- National stats page: charts + methodology notes
- Disclaimer on every legal page: informational only, not legal advice, "as of [date]," encourage consulting a local attorney or advocate for an actual legal question

---

## Status
- [x] Repo + folder created at `~/Documents/sa-law-stats-resource/`
- [x] States chosen: CO, NY, AR
- [ ] Confirm content scope (above) before research begins
- [ ] Research + hand-curate legal data for 3 states
- [ ] Research + source stats data (state + national)
- [ ] Build schema.sql + load scripts
- [ ] SQL practice pass (similar ladder to 14ers project, if still useful for interview prep)
- [ ] Build map + state pages + national stats page
