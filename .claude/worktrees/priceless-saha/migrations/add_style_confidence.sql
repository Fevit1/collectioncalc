-- =============================================================================
-- Migration: Add style confidence tracking to creator_signatures
-- File: migrations/add_style_confidence.sql
--
-- Tracks whether signature_style metadata was AI-assigned (potentially wrong)
-- or admin-verified (Mike confirmed). Confidence score (0.0-1.0) determines
-- how much weight the orchestrator gives to style when matching.
--
-- Key insight: Sonnet was wrong on ~1/3 of the original 43 creators' style
-- metadata. Rather than blindly trusting AI-assigned styles, we track
-- confidence and let the orchestrator weight accordingly.
--
-- Safe to run multiple times (IF NOT EXISTS guards).
-- =============================================================================

-- Source of the style classification
-- 'ai_assigned' = Claude assigned it (may be wrong)
-- 'admin'       = Mike verified/corrected it (ground truth)
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS style_source TEXT DEFAULT 'ai_assigned';

-- Confidence in the style classification (0.0 = no idea, 1.0 = certain)
-- Admin overrides always set this to 1.0
-- AI-assigned values range from 0.3 (uncertain) to 0.9 (high confidence)
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS style_confidence FLOAT DEFAULT 0.5;

-- Add check constraints (safe if column already exists with different constraint)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_style_source'
    ) THEN
        ALTER TABLE creator_signatures
            ADD CONSTRAINT chk_style_source
            CHECK (style_source IN ('ai_assigned', 'admin'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_style_confidence'
    ) THEN
        ALTER TABLE creator_signatures
            ADD CONSTRAINT chk_style_confidence
            CHECK (style_confidence >= 0.0 AND style_confidence <= 1.0);
    END IF;
END $$;

-- Verify
SELECT
    style_source,
    COUNT(*) AS creator_count,
    ROUND(AVG(style_confidence)::numeric, 2) AS avg_confidence
FROM creator_signatures
WHERE active = true
GROUP BY style_source
ORDER BY style_source;
