-- Migration: grade-submission retention (persist every /api/grade, saved or not)
-- Session 107 — per docs/technical/GRADE_RETENTION_SPEC.md
--
-- One row per grade. Images live in R2 at grade_submissions/{id}/{label}.jpg;
-- the `photos` jsonb maps label -> R2 key. Retention window is 90 days (privacy.html);
-- `images_purge_after` is the day-90 marker the (deferred) auto-purge job will use,
-- and `pinned` is the feedback-pin exception that exempts a row from that purge.

CREATE TABLE IF NOT EXISTS grade_submissions (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id),
    created_at          TIMESTAMP DEFAULT (now() AT TIME ZONE 'utc'),

    -- Identified comic (from extraction, carried into grade)
    title               VARCHAR(255),
    issue               VARCHAR(50),
    year                INTEGER,
    publisher           VARCHAR(255),

    -- Assigned grade
    grade               NUMERIC,        -- snapped CGC overall grade
    grade_label         VARCHAR(50),
    raw_grade           NUMERIC,        -- unsnapped weighted average (calibration)
    category_scores     JSONB,          -- the 8 subgrades (cover_front/spine/corners/edges/cover_back/color_gloss/structural/interior)
    limiting_factor     VARCHAR(50),
    confidence          INTEGER,        -- the {1:65,2:78,3:88,4:94} photo-count map
    photos_used         INTEGER,
    defects             JSONB,

    -- Submission + provenance
    photo_labels        JSONB,          -- ["front","back","spine","centerfold"]
    photos              JSONB,          -- { "front": "grade_submissions/{id}/front.jpg", ... } (R2 keys)
    model               VARCHAR(100),
    run_count           INTEGER,
    grade_reasoning     TEXT,
    reread_fired        BOOLEAN,        -- N/A today: no 180-degree re-read exists in the grading path (always NULL)

    -- Lifecycle
    saved_collection_id INTEGER,        -- NULL = not saved to a collection (backlink-on-save is a follow-up)
    pinned              BOOLEAN DEFAULT FALSE,   -- feedback-pin: exempt from the 90-day purge
    images_purge_after  TIMESTAMP       -- created_at + 90 days; the deferred purge job acts on this
);

CREATE INDEX IF NOT EXISTS idx_grade_submissions_user    ON grade_submissions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_grade_submissions_created ON grade_submissions(created_at DESC);
-- Purge job lookup: unpinned rows past their purge time
CREATE INDEX IF NOT EXISTS idx_grade_submissions_purge   ON grade_submissions(images_purge_after) WHERE pinned = FALSE;
