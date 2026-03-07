-- Migration: Add signature identification log table
-- File: migrations/add_signature_identification_log.sql
-- Run once against your PostgreSQL instance on Render

CREATE TABLE IF NOT EXISTS signature_identification_log (
    id                    SERIAL PRIMARY KEY,
    unknown_image_key     TEXT NOT NULL,
    top_creator           TEXT,
    top_confidence        FLOAT,
    top5_json             JSONB NOT NULL DEFAULT '[]',
    flags_json            JSONB NOT NULL DEFAULT '{}',
    comic_context_json    JSONB NOT NULL DEFAULT '{}',
    stability_scores_json JSONB NOT NULL DEFAULT '{}',
    pass_count            INTEGER NOT NULL DEFAULT 3,
    latency_ms            INTEGER,
    needs_review          BOOLEAN NOT NULL DEFAULT false,
    reviewed              BOOLEAN NOT NULL DEFAULT false,
    review_notes          TEXT,
    correct_creator       TEXT,      -- filled in during human review
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at           TIMESTAMPTZ
);

-- Index for review queue queries
CREATE INDEX IF NOT EXISTS idx_sig_log_needs_review
    ON signature_identification_log (needs_review, created_at DESC)
    WHERE needs_review = true AND reviewed = false;

-- Index for per-creator accuracy analysis
CREATE INDEX IF NOT EXISTS idx_sig_log_top_creator
    ON signature_identification_log (top_creator, created_at DESC);

-- Index for recent stats queries
CREATE INDEX IF NOT EXISTS idx_sig_log_created_at
    ON signature_identification_log (created_at DESC);

-- View: Review queue (unreviewed flagged items, newest first)
CREATE OR REPLACE VIEW signature_review_queue AS
SELECT
    id,
    unknown_image_key,
    top_creator,
    ROUND(top_confidence::numeric, 3) AS top_confidence,
    top5_json,
    flags_json,
    comic_context_json,
    stability_scores_json,
    pass_count,
    latency_ms,
    created_at
FROM signature_identification_log
WHERE needs_review = true
  AND reviewed = false
ORDER BY created_at DESC;

-- View: Per-creator confusion matrix (for tuning)
CREATE OR REPLACE VIEW signature_confusion_summary AS
SELECT
    top_creator,
    COUNT(*) AS total_identified,
    COUNT(*) FILTER (WHERE needs_review = true) AS flagged_count,
    ROUND(AVG(top_confidence)::numeric, 3) AS avg_confidence,
    COUNT(*) FILTER (WHERE (flags_json->>'high_confusion_pair')::boolean = true)
        AS confusion_pair_count
FROM signature_identification_log
GROUP BY top_creator
ORDER BY total_identified DESC;
