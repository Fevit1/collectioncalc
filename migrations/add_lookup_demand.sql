-- Lookup-demand instrumentation
-- One row per valuation lookup so ~28K lookups/month become a DEMAND-RANKED
-- backfill list: which titles do real users search that return NO or THIN data?
--
-- Purely additive. Rows are written fire-and-forget on a background thread from
-- routes/sales_valuation.py (see lookup_demand.py) — a write failure can never
-- break or slow a valuation response. No FK on user_id ON PURPOSE: (a) a logging
-- insert must never fail on a constraint/race, and (b) anonymous lookups (e.g.
-- the Whatnot extension hitting /api/sales/fmv with no token) store NULL.
-- Test/admin exclusion is done at QUERY time via user_id -> users (see below),
-- with is_internal as a cheap pre-filter for admin lookups.

CREATE TABLE IF NOT EXISTS lookup_demand (
    id              SERIAL PRIMARY KEY,
    endpoint        TEXT,                  -- 'valuation' | 'fmv'
    title           TEXT,                  -- raw requested title
    canonical_title TEXT,                  -- compose_qualified_title(title, issue_type) — grouping key
    issue           TEXT,
    issue_type      TEXT,                  -- series qualifier (Giant-Size / Annual / Special / '')
    requested_grade NUMERIC,               -- grade param (valuation requires it; fmv optional)
    comp_count      INTEGER,               -- total comps that backed the answer (graded+raw, or len(all_sales))
    graded_count    INTEGER,               -- graded comps found  (valuation only; NULL for fmv)
    exact_count     INTEGER,               -- exact-grade comps   (valuation only; NULL for fmv)
    fmv_method      TEXT,                  -- exact|blended|exact_thin|interpolated|estimated|... (valuation); tier (fmv)
    estimated       BOOLEAN DEFAULT FALSE, -- fell back to an estimate (thin/absent data)
    no_data         BOOLEAN DEFAULT FALSE, -- comp_count = 0
    user_id         INTEGER,               -- from JWT (g.user_id); NULL = anonymous (extension fmv)
    is_internal     BOOLEAN DEFAULT FALSE, -- TRUE for admin lookups (cheap pre-filter; test accts excluded by user_id)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Ranking-query indexes. 28K/mo is small, but these keep the analytics snappy
-- and are essentially free at this volume.
CREATE INDEX IF NOT EXISTS idx_lookup_demand_canon   ON lookup_demand (canonical_title);
CREATE INDEX IF NOT EXISTS idx_lookup_demand_created ON lookup_demand (created_at);
-- Partial index for the "where are we blind / thin?" queries (the whole point):
CREATE INDEX IF NOT EXISTS idx_lookup_demand_thin    ON lookup_demand (canonical_title)
    WHERE estimated = TRUE OR no_data = TRUE OR comp_count < 3;
