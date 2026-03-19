-- =============================================================================
-- Verification Query: Confirm 100 creators after expansion migration
-- File: migrations/verify_100_creators.sql
--
-- Run this AFTER add_57_new_creators.sql to verify everything inserted correctly.
-- =============================================================================

-- 1. Total count (expect ~100)
SELECT COUNT(*) AS total_active_creators
FROM creator_signatures
WHERE active = true;

-- 2. Breakdown by role
SELECT role, COUNT(*) AS count
FROM creator_signatures
WHERE active = true
GROUP BY role
ORDER BY count DESC;

-- 3. Breakdown by signature style
SELECT signature_style, COUNT(*) AS count
FROM creator_signatures
WHERE active = true
GROUP BY signature_style
ORDER BY count DESC;

-- 4. Era coverage (decade buckets)
SELECT
    CASE
        WHEN career_start < 1940 THEN '1930s (Golden Age)'
        WHEN career_start < 1960 THEN '1940s-50s (Golden/Silver)'
        WHEN career_start < 1970 THEN '1960s (Silver Age)'
        WHEN career_start < 1980 THEN '1970s (Bronze Age)'
        WHEN career_start < 1990 THEN '1980s (Copper Age)'
        WHEN career_start < 2000 THEN '1990s (Modern begins)'
        WHEN career_start < 2010 THEN '2000s'
        WHEN career_start < 2020 THEN '2010s'
        ELSE '2020s'
    END AS era,
    COUNT(*) AS count
FROM creator_signatures
WHERE active = true AND career_start IS NOT NULL
GROUP BY era
ORDER BY MIN(career_start);

-- 5. Publisher coverage
SELECT unnest(publisher_affiliations) AS publisher, COUNT(*) AS creator_count
FROM creator_signatures
WHERE active = true
GROUP BY publisher
ORDER BY creator_count DESC;

-- 6. Creators WITH reference images (can be matched today)
SELECT
    cs.creator_name,
    cs.reference_image_count,
    cs.career_start,
    cs.signature_style
FROM creator_signatures cs
WHERE cs.active = true AND cs.reference_image_count > 0
ORDER BY cs.reference_image_count DESC, cs.creator_name;

-- 7. Creators WITHOUT reference images (need uploads)
SELECT
    cs.creator_name,
    cs.role,
    cs.career_start,
    cs.signature_style
FROM creator_signatures cs
WHERE cs.active = true AND cs.reference_image_count = 0
ORDER BY cs.creator_name;

-- 8. The 57 new creators specifically (added by this migration)
-- These will have reference_image_count = 0 and career_start IS NOT NULL
SELECT
    cs.creator_name,
    cs.role,
    cs.career_start,
    cs.career_end,
    array_to_string(cs.publisher_affiliations, ', ') AS publishers,
    cs.signature_style,
    cs.reference_image_count AS images,
    cs.notes
FROM creator_signatures cs
WHERE cs.active = true
  AND cs.creator_name IN (
    'Walt Simonson', 'Marc Silvestri', 'David Finch', 'Adam Kubert', 'Andy Kubert',
    'Frank Cho', 'Joe Quesada', 'Jim Cheung', 'Ed McGuinness', 'Kevin Eastman',
    'Bill Sienkiewicz', 'Mike Zeck', 'Whilce Portacio', 'Erik Larsen', 'Michael Turner',
    'Ryan Stegman', 'Terry Dodson', 'Sean Murphy', 'Patrick Gleason', 'Gary Frank',
    'Mark Bagley', 'Humberto Ramos', 'Leinil Francis Yu', 'Ryan Ottley', 'Jorge Jimenez',
    'Dan Mora', 'Olivier Coipel', 'Esad Ribic', 'Lee Bermejo', 'Daniel Warren Johnson',
    'Bernie Wrightson', 'Tim Sale', 'Darwyn Cooke', 'Mike Wieringo', 'Herb Trimpe',
    'Mark Waid', 'Peter David', 'Robert Kirkman', 'Jason Aaron', 'Garth Ennis',
    'Warren Ellis', 'Donny Cates', 'Chip Zdarsky', 'Matt Fraction', 'Larry Hama',
    'Mark Brooks', 'Skottie Young', 'Jenny Frison', 'Jen Bartel', 'Derrick Chew',
    'Clayton Crain', 'Rafael Albuquerque', 'Kieron Gillen', 'Joshua Williamson',
    'Sara Pichelli', 'Pepe Larraz', 'Mitch Gerads'
  )
ORDER BY cs.creator_name;

-- 9. Confusion pair check — verify flagged pairs exist
SELECT
    cs.creator_name,
    cs.notes
FROM creator_signatures cs
WHERE cs.active = true
  AND cs.notes LIKE '%CONFUSION%'
ORDER BY cs.creator_name;

-- 10. Summary dashboard
SELECT
    COUNT(*) FILTER (WHERE active = true) AS total_active,
    COUNT(*) FILTER (WHERE active = true AND reference_image_count > 0) AS with_images,
    COUNT(*) FILTER (WHERE active = true AND reference_image_count = 0) AS needs_images,
    COUNT(*) FILTER (WHERE active = true AND career_end IS NOT NULL) AS deceased_or_retired,
    COUNT(*) FILTER (WHERE active = true AND career_end IS NULL) AS still_active,
    SUM(reference_image_count) FILTER (WHERE active = true) AS total_reference_images
FROM creator_signatures;
