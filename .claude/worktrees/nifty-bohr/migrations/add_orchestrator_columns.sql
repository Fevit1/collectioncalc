-- =============================================================================
-- Migration: Add orchestrator columns to creator_signatures + signature_images
-- File: migrations/add_orchestrator_columns.sql
--
-- Safe to run multiple times (all ADD COLUMN IF NOT EXISTS).
-- Run AFTER add_signature_identification_log.sql.
-- Run against your Render PostgreSQL instance.
-- =============================================================================


-- =============================================================================
-- PART 1: creator_signatures — add metadata columns for pre-filtering
-- =============================================================================

-- Year the creator began their professional comic career
-- Used to narrow candidate pool by comic era (e.g. 1990s book → deprioritize
-- creators who debuted after 2000)
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS career_start INTEGER;

-- Year the creator stopped (NULL = still active)
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS career_end INTEGER;

-- Array of publisher abbreviations this creator is associated with
-- e.g. ARRAY['MARVEL', 'DC', 'IMAGE']
-- Used to weight candidates when publisher is known from comic context
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS publisher_affiliations TEXT[] DEFAULT '{}';

-- Signature visual style — helps group similar signatures for disambiguation
-- Values: 'initials' | 'cursive' | 'stylized' | 'print' | 'mixed' | NULL
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS signature_style TEXT;

-- Cached count of reference images for this creator
-- Used for ORDER BY in pre-filter query (more images = higher confidence creator)
-- Kept in sync by the trigger below
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS reference_image_count INTEGER NOT NULL DEFAULT 0;

-- Soft-delete / active flag (may already exist — IF NOT EXISTS handles it)
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT true;

-- Free-text notes field for internal use (confusion pairs, era notes, etc.)
ALTER TABLE creator_signatures
    ADD COLUMN IF NOT EXISTS notes TEXT;


-- =============================================================================
-- PART 2: signature_images — ensure expected columns exist
-- =============================================================================

-- R2 object key — primary storage reference
-- Naming: signatures/{creator_slug}/{1..4}.jpg
-- Add IF NOT EXISTS in case your existing column is named differently
ALTER TABLE signature_images
    ADD COLUMN IF NOT EXISTS r2_key TEXT;

-- Display/selection order within a creator's reference set (1-4)
ALTER TABLE signature_images
    ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 1;

-- Optional: image source URL (where you found this signature on the web)
ALTER TABLE signature_images
    ADD COLUMN IF NOT EXISTS source_url TEXT;

-- Optional: rough year this signature was signed (helps era disambiguation)
ALTER TABLE signature_images
    ADD COLUMN IF NOT EXISTS approximate_year INTEGER;

-- Optional: notes about this specific reference image
ALTER TABLE signature_images
    ADD COLUMN IF NOT EXISTS image_notes TEXT;


-- =============================================================================
-- PART 3: Indexes for pre-filter query performance
-- =============================================================================

-- Pre-filter queries filter on active + reference_image_count
CREATE INDEX IF NOT EXISTS idx_creator_sigs_active_count
    ON creator_signatures (active, reference_image_count DESC)
    WHERE active = true;

-- Pre-filter queries filter on career years
CREATE INDEX IF NOT EXISTS idx_creator_sigs_career_years
    ON creator_signatures (career_start, career_end)
    WHERE active = true;

-- Pre-filter queries use GIN index for array containment on publisher_affiliations
CREATE INDEX IF NOT EXISTS idx_creator_sigs_publishers
    ON creator_signatures USING GIN (publisher_affiliations)
    WHERE active = true;

-- Signature images: lookup by creator_id + sort_order
CREATE INDEX IF NOT EXISTS idx_sig_images_creator_order
    ON signature_images (creator_id, sort_order);


-- =============================================================================
-- PART 4: Trigger to auto-update reference_image_count
-- Keeps the cached count in sync whenever signature_images changes
-- =============================================================================

CREATE OR REPLACE FUNCTION update_reference_image_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE creator_signatures
        SET reference_image_count = (
            SELECT COUNT(*) FROM signature_images
            WHERE creator_id = OLD.creator_id
        )
        WHERE id = OLD.creator_id;
        RETURN OLD;
    ELSE
        UPDATE creator_signatures
        SET reference_image_count = (
            SELECT COUNT(*) FROM signature_images
            WHERE creator_id = NEW.creator_id
        )
        WHERE id = NEW.creator_id;
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Drop and recreate trigger (idempotent)
DROP TRIGGER IF EXISTS trg_update_image_count ON signature_images;

CREATE TRIGGER trg_update_image_count
AFTER INSERT OR UPDATE OR DELETE ON signature_images
FOR EACH ROW EXECUTE FUNCTION update_reference_image_count();


-- =============================================================================
-- PART 5: Backfill reference_image_count for existing rows
-- Run this once after adding the trigger to sync existing data
-- =============================================================================

UPDATE creator_signatures cs
SET reference_image_count = (
    SELECT COUNT(*) FROM signature_images si
    WHERE si.creator_id = cs.id
);


-- =============================================================================
-- PART 6: Validation view — confirm schema looks right after migration
-- Drop this view after you've confirmed everything looks good
-- =============================================================================

CREATE OR REPLACE VIEW migration_validation AS
SELECT
    cs.id,
    cs.creator_name,
    cs.active,
    cs.career_start,
    cs.career_end,
    cs.publisher_affiliations,
    cs.signature_style,
    cs.reference_image_count,
    COUNT(si.id) AS actual_image_count,
    CASE
        WHEN cs.reference_image_count = COUNT(si.id) THEN 'OK'
        ELSE 'COUNT MISMATCH'
    END AS count_check
FROM creator_signatures cs
LEFT JOIN signature_images si ON si.creator_id = cs.id
GROUP BY cs.id, cs.creator_name, cs.active, cs.career_start,
         cs.career_end, cs.publisher_affiliations, cs.signature_style,
         cs.reference_image_count
ORDER BY cs.creator_name;

-- To validate after running: SELECT * FROM migration_validation;
-- All rows should show count_check = 'OK'


-- =============================================================================
-- PART 7: Seed data helpers — update your 43 existing creators
-- =============================================================================
-- These are example UPDATE statements. Fill in your actual creator slugs.
-- Run these manually or via a Python seed script after the migration.
--
-- Pattern:
--   UPDATE creator_signatures
--   SET career_start = XXXX,
--       career_end   = NULL,   -- or year if retired
--       publisher_affiliations = ARRAY['MARVEL','DC'],
--       signature_style = 'cursive'  -- initials|cursive|stylized|print|mixed
--   WHERE slug = 'your-creator-slug';
--
-- Example for a few well-known creators (fill in your actual slugs):
--
-- UPDATE creator_signatures SET
--     career_start = 1961, career_end = 2018,
--     publisher_affiliations = ARRAY['MARVEL'],
--     signature_style = 'cursive'
-- WHERE slug = 'stan-lee';
--
-- UPDATE creator_signatures SET
--     career_start = 1987, career_end = NULL,
--     publisher_affiliations = ARRAY['DC','IMAGE','MARVEL'],
--     signature_style = 'initials'
-- WHERE slug = 'jim-lee';
--
-- UPDATE creator_signatures SET
--     career_start = 1988, career_end = NULL,
--     publisher_affiliations = ARRAY['IMAGE','MARVEL'],
--     signature_style = 'stylized'
-- WHERE slug = 'todd-mcfarlane';
-- =============================================================================
