-- SA Law & Stats Resource -- schema
-- Every fact table carries source_url + verified so nothing reaches the
-- public site without a traceable citation. Legal tables are hand-curated
-- (no clean API exists); the FBI rate table is loaded from a real primary
-- source (BJS "Crime Known to Law Enforcement, 2023", NCJ 310188, Table 3).

-- ============================================================
-- DIMENSION
-- ============================================================

CREATE TABLE dim_state (
    state_name      VARCHAR PRIMARY KEY,
    state_abbr      VARCHAR
);

-- ============================================================
-- LEGAL FACTS (hand-curated, v1 = Colorado, New York, Arkansas)
-- ============================================================

-- Grain: one row per state. How consent is legally defined there.
CREATE TABLE fact_state_consent_law (
    state_name              VARCHAR REFERENCES dim_state(state_name),
    consent_definition      TEXT,       -- how the statute defines consent
    incapacitation_rule     TEXT,       -- what makes someone unable to consent (intoxication threshold, unconsciousness, etc.)
    age_of_consent          INTEGER,
    close_in_age_exemption  TEXT,       -- "Romeo and Juliet" style exemptions, if any
    spousal_exemption_note  TEXT,       -- historically significant; note current status
    statute_citation        VARCHAR,    -- e.g. "C.R.S. 18-3-401"
    source_url               VARCHAR,
    last_verified_date       DATE,
    verified                  BOOLEAN DEFAULT FALSE
);

-- Grain: one row per (state, offense category, SOL type). SOL varies by
-- degree of offense and by criminal vs civil -- a flat per-state column
-- would lose that, so this is deliberately long/narrow, not wide.
CREATE TABLE fact_state_statute_limitations (
    state_name          VARCHAR REFERENCES dim_state(state_name),
    sol_type             VARCHAR,   -- 'criminal' or 'civil'
    offense_category     VARCHAR,   -- e.g. 'first-degree', 'felony sex offense', 'child sexual abuse'
    limitation_description TEXT,     -- e.g. "no limit", "20 years from age 18", "3 years from discovery"
    recent_law_change_note TEXT,     -- e.g. NY's Adult Survivors Act lookback window, now closed
    source_url            VARCHAR,
    last_verified_date     DATE,
    verified                BOOLEAN DEFAULT FALSE
);

-- Grain: one row per (state, reporter category). Who's legally required to report.
CREATE TABLE fact_state_mandatory_reporting (
    state_name        VARCHAR REFERENCES dim_state(state_name),
    reporter_category  VARCHAR,   -- e.g. 'teachers', 'medical professionals', 'clergy'
    requirement_note   TEXT,
    source_url         VARCHAR,
    last_verified_date  DATE,
    verified             BOOLEAN DEFAULT FALSE
);

-- ============================================================
-- STATS FACTS
-- ============================================================

-- Grain: one row per state, 2023. FBI/BJS REPORTED rate -- not survey-based
-- prevalence. reliable_estimate=FALSE means BJS itself declined to publish
-- a number for that state (NIBRS participation gap), not that the rate is
-- zero or low -- the map/UI must treat these states as "data not available,"
-- never as "0" or omit the distinction silently.
CREATE TABLE fact_state_reported_rate (
    state_name            VARCHAR REFERENCES dim_state(state_name),
    year                   INTEGER,
    rape_count             INTEGER,
    rape_rate_per_100k     DOUBLE,
    reliable_estimate      BOOLEAN,
    unreliable_reason_note TEXT,     -- e.g. "low NIBRS agency participation"
    source_url             VARCHAR,
    source_name            VARCHAR,
    report_date            VARCHAR,
    verified                BOOLEAN DEFAULT FALSE
);

-- Grain: one row per (state, survey, metric). NISVS/NCVS SURVEY-based
-- prevalence -- only exists for states where the survey sample was large
-- enough. Kept separate from fact_state_reported_rate on purpose (same
-- "don't blend confidence levels" rule as the 14er project) -- a reported
-- rate and a survey-based prevalence rate answer different questions.
CREATE TABLE fact_state_survey_rate (
    state_name      VARCHAR REFERENCES dim_state(state_name),
    survey_name      VARCHAR,   -- 'NISVS' or 'NCVS'
    survey_years      VARCHAR,
    metric_name       VARCHAR,   -- e.g. 'lifetime rape prevalence, women'
    value_pct         DOUBLE,
    source_url        VARCHAR,
    verified            BOOLEAN DEFAULT FALSE
);

-- Grain: one row per (metric, population group, source). Flexible
-- metric/value table for national-level numbers -- lifetime prevalence,
-- past-year prevalence, reporting-to-police rate, perpetration-rate
-- studies (deliberately stored as MULTIPLE rows across different studies,
-- not collapsed into one number, given how contested that specific stat is).
CREATE TABLE fact_national_stats (
    metric_name        VARCHAR,
    population_group    VARCHAR,   -- e.g. 'women', 'men', 'college men'
    value_pct           DOUBLE,
    value_description    VARCHAR,   -- for non-simple values, e.g. "6% to 14.9%"
    survey_or_study_name VARCHAR,
    study_year           VARCHAR,
    methodology_note      TEXT,      -- why this number might differ from others on the same topic
    source_url            VARCHAR,
    verified                BOOLEAN DEFAULT FALSE
);

-- ============================================================
-- MART -- the rank table (built via SQL practice, not hand-computed)
-- ============================================================

-- Grain: one row per state. Rank is computed from fact_state_reported_rate
-- via RANK() -- states with reliable_estimate=FALSE get NULL rank, not 0
-- or a fabricated low rank.
CREATE TABLE mart_state_rate_rank (
    state_name         VARCHAR,
    rape_rate_per_100k  DOUBLE,
    reported_rate_rank   INTEGER,   -- NULL if no reliable estimate
    reliable_estimate     BOOLEAN
);
