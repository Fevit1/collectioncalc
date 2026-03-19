-- Fix creator name typos/duplicates found during 100-creator expansion
-- Safe to run multiple times (idempotent)

-- 1. Fix "Whilche Portacio" typo (extra 'h') → "Whilce Portacio"
UPDATE creator_signatures
SET creator_name = 'Whilce Portacio'
WHERE creator_name = 'Whilche Portacio';

-- 2. Remove duplicate "Brian Michael Bendis - Early 2000s" if it exists
--    (Keep the canonical "Brian Michael Bendis" entry)
DELETE FROM creator_signatures
WHERE creator_name LIKE 'Brian Michael Bendis - %'
  AND EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Brian Michael Bendis');

-- 3. Verify results
SELECT creator_name FROM creator_signatures
WHERE creator_name ILIKE '%bendis%'
   OR creator_name ILIKE '%portacio%'
   OR creator_name ILIKE '%perez%'
ORDER BY creator_name;
