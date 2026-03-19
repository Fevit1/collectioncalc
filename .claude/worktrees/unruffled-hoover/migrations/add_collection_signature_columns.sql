-- Migration: Add signature_data JSONB column to collections table
-- Session 87 — Integrate signature identification into Slab Report
--
-- Format: {"creator": "Jim Lee", "confidence": 0.92, "confidence_label": "high",
--          "style": "cursive", "flags": {}, "stability": 0.95, "pass_count": 3,
--          "detected_at": "2026-03-08T..."}
-- NULL = not yet checked. Empty {} = checked, no signature found.

ALTER TABLE collections ADD COLUMN IF NOT EXISTS signature_data JSONB;

-- Index for querying signed comics (e.g., filter collection by "has signature")
CREATE INDEX IF NOT EXISTS idx_collections_signature_creator
    ON collections ((signature_data->>'creator'))
    WHERE signature_data IS NOT NULL AND signature_data->>'creator' IS NOT NULL;
