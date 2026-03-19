-- =============================================================================
-- Migration: Add 57 new creators to reach 100 total
-- File: migrations/add_57_new_creators.sql
--
-- Safe to run multiple times (WHERE NOT EXISTS guards every INSERT).
-- Run against your Render PostgreSQL instance.
--
-- Existing DB: ~43 creators (41 seeded + 2 admin-added)
-- After this:  ~100 creators
--
-- Selection criteria (weighted):
--   1. Market value — signed books command premium at auction
--   2. Signature distinctiveness — helps AI matching accuracy
--   3. Era/publisher coverage — Golden through Modern age
--   4. Collection prevalence — common in collector portfolios
--   5. Convention signing frequency — more signed books in circulation
--
-- Confusion risk pairs flagged in notes field.
-- =============================================================================


-- =============================================================================
-- TIER 1: HIGH MARKET VALUE ARTISTS (15)
-- =============================================================================

-- 1. Walt Simonson — Thor/Fantastic Four legend, frequent convention signer
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Walt Simonson', 'artist', 1980, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Thor/FF legend. Frequent convention signer. Distinctive flowing sig often with "WS" monogram.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Walt Simonson');

-- 2. Marc Silvestri — X-Men, Top Cow founder, Image co-founder
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Marc Silvestri', 'artist', 1986, NULL, ARRAY['MARVEL','IMAGE','TOP COW'], 'stylized', true,
       'X-Men #256-269 run. Top Cow/Image co-founder. Very active convention signer.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Marc Silvestri');

-- 3. David Finch — Batman, New Avengers, very popular convention artist
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'David Finch', 'artist', 1995, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Batman, Dark Knight, Ultimatum. High volume con signer.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'David Finch');

-- 4. Adam Kubert — X-Men, Wolverine
-- CONFUSION RISK: Brother Andy Kubert. Both cursive, both X-Men/Marvel.
-- Mitigation: Different letterforms, Adam's is more compact. Publisher overlap is high.
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Adam Kubert', 'artist', 1990, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Wolverine, X-Men. CONFUSION PAIR: Brother Andy Kubert — similar name+era but different letterforms.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Adam Kubert');

-- 5. Andy Kubert — Batman, X-Men
-- CONFUSION RISK: Brother Adam Kubert (see above)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Andy Kubert', 'artist', 1988, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Batman, X-Men. CONFUSION PAIR: Brother Adam Kubert — similar name+era but different letterforms.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Andy Kubert');

-- 6. Frank Cho — Hulk, Liberty Meadows, distinctive print-style sig
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Frank Cho', 'artist', 1996, NULL, ARRAY['MARVEL','DC','IMAGE'], 'print', true,
       'Liberty Meadows, Hulk. Often adds character sketches with signature. CONFUSION NOTE: shares "Frank" with Frank Miller (existing) but completely different styles.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Frank Cho');

-- 7. Joe Quesada — former Marvel EIC, Daredevil artist
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Joe Quesada', 'artist', 1990, NULL, ARRAY['MARVEL'], 'stylized', true,
       'Former Marvel Editor-in-Chief. Daredevil artist. Stylized "JQ" monogram common.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Joe Quesada');

-- 8. Jim Cheung — Infinity Wars, Young Avengers
-- CONFUSION NOTE: "Jim" first name shared with Jim Lee, Jim Steranko, Jim Starlin
-- Mitigation: Different signature style, different era focus
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Jim Cheung', 'artist', 1995, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Young Avengers, Infinity Wars. CONFUSION NOTE: shares "Jim" with Lee/Steranko/Starlin but distinct letterforms.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Jim Cheung');

-- 9. Ed McGuinness — Superman/Batman, Hulk, bold clean style
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Ed McGuinness', 'artist', 1996, NULL, ARRAY['MARVEL','DC'], 'print', true,
       'Superman/Batman, Hulk. Bold clean print-style signature.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Ed McGuinness');

-- 10. Kevin Eastman — TMNT co-creator, extremely valuable signatures
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Kevin Eastman', 'creator', 1984, NULL, ARRAY['MIRAGE','IDW'], 'stylized', true,
       'TMNT co-creator. Extremely valuable signatures. Often adds Turtle sketches. Very active con circuit.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Kevin Eastman');

-- 11. Bill Sienkiewicz — New Mutants, Elektra: Assassin, very distinctive style
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Bill Sienkiewicz', 'artist', 1980, NULL, ARRAY['MARVEL','DC'], 'stylized', true,
       'New Mutants #87 (1st Cable), Elektra: Assassin. Highly distinctive abstract signature. CONFUSION NOTE: shares "Bill" with Bill Finger (existing) but completely different eras/styles.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Bill Sienkiewicz');

-- 12. Mike Zeck — Secret Wars, Captain America, Punisher
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Mike Zeck', 'artist', 1974, NULL, ARRAY['MARVEL'], 'cursive', true,
       'Secret Wars (1984), Captain America, Punisher. CONFUSION NOTE: shares "Mike" with Mike Mignola (existing) but different era.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Mike Zeck');

-- 13. Whilce Portacio — X-Men, Image co-founder
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Whilce Portacio', 'artist', 1986, NULL, ARRAY['MARVEL','IMAGE'], 'cursive', true,
       'Uncanny X-Men, Image co-founder. Bishop creator.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Whilce Portacio');

-- 14. Erik Larsen — Spider-Man, Savage Dragon, Image co-founder
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Erik Larsen', 'artist', 1986, NULL, ARRAY['MARVEL','IMAGE'], 'cursive', true,
       'Amazing Spider-Man run, Savage Dragon creator, Image co-founder.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Erik Larsen');

-- 15. Michael Turner — Fathom, Witchblade (deceased 2008, extremely valuable)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Michael Turner', 'artist', 1996, 2008, ARRAY['TOP COW','DC','ASPEN'], 'cursive', true,
       'Fathom, Witchblade creator. Deceased 2008. EXTREMELY valuable signatures due to limited supply.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Michael Turner');


-- =============================================================================
-- TIER 2: STRONG CONVENTION PRESENCE + MODERN ARTISTS (15)
-- =============================================================================

-- 16. Ryan Stegman — Venom, Superior Spider-Man
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Ryan Stegman', 'artist', 2009, NULL, ARRAY['MARVEL'], 'cursive', true,
       'Venom (King in Black), Superior Spider-Man. CONFUSION NOTE: shares "Ryan" with Ryan Ottley but different publishers/styles.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Ryan Stegman');

-- 17. Terry Dodson — X-Men, Wonder Woman
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Terry Dodson', 'artist', 1993, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'X-Men, Wonder Woman. Often signs with wife Rachel Dodson.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Terry Dodson');

-- 18. Sean Murphy — Batman: White Knight
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Sean Murphy', 'artist', 2005, NULL, ARRAY['DC','IMAGE'], 'cursive', true,
       'Batman: White Knight series. Writer/artist.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Sean Murphy');

-- 19. Patrick Gleason — Batman, Superman
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Patrick Gleason', 'artist', 1998, NULL, ARRAY['DC','MARVEL'], 'cursive', true,
       'Batman, Superman Rebirth, Green Lantern Corps.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Patrick Gleason');

-- 20. Gary Frank — Superman, Doomsday Clock
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Gary Frank', 'artist', 1991, NULL, ARRAY['DC','MARVEL'], 'cursive', true,
       'Superman: Secret Origin, Doomsday Clock. CONFUSION NOTE: shares "Frank" surname with Frank Miller/Frank Cho but different first/last arrangement.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Gary Frank');

-- 21. Mark Bagley — Ultimate Spider-Man marathon signer
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Mark Bagley', 'artist', 1984, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Ultimate Spider-Man (111-issue run with Bendis), Thunderbolts. Prolific con signer. CONFUSION NOTE: "Mark B" overlap with Mark Brooks (cover artist).'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Mark Bagley');

-- 22. Humberto Ramos — Spider-Man, very distinctive style
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Humberto Ramos', 'artist', 1994, NULL, ARRAY['MARVEL','DC'], 'stylized', true,
       'Spider-Man, Crimson, Impulse. Very distinctive angular/stylized signature.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Humberto Ramos');

-- 23. Leinil Francis Yu — Wolverine, Avengers
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Leinil Francis Yu', 'artist', 1994, NULL, ARRAY['MARVEL'], 'cursive', true,
       'Wolverine, New Avengers, Secret Invasion.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Leinil Francis Yu');

-- 24. Ryan Ottley — Invincible, Amazing Spider-Man
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Ryan Ottley', 'artist', 2003, NULL, ARRAY['IMAGE','MARVEL'], 'cursive', true,
       'Invincible (with Kirkman), Amazing Spider-Man. CONFUSION NOTE: shares "Ryan" with Ryan Stegman.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Ryan Ottley');

-- 25. Jorge Jimenez — Batman, Justice League (modern DC star)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Jorge Jimenez', 'artist', 2016, NULL, ARRAY['DC'], 'cursive', true,
       'Batman, Justice League, Super Sons. Rising DC star.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Jorge Jimenez');

-- 26. Dan Mora — Batman/Superman: World''s Finest
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Dan Mora', 'artist', 2016, NULL, ARRAY['DC','BOOM'], 'cursive', true,
       'Batman/Superman: World''s Finest, Power Rangers. Incredibly prolific.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Dan Mora');

-- 27. Olivier Coipel — House of M, Thor
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Olivier Coipel', 'artist', 2000, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'House of M, Thor, Legion of Super-Heroes.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Olivier Coipel');

-- 28. Esad Ribic — Secret Wars (2015), Thor: God of Thunder
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Esad Ribic', 'artist', 1997, NULL, ARRAY['MARVEL'], 'cursive', true,
       'Secret Wars (2015), Thor: God of Thunder, Eternals.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Esad Ribic');

-- 29. Lee Bermejo — Joker, Batman: Damned
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Lee Bermejo', 'artist', 2003, NULL, ARRAY['DC'], 'stylized', true,
       'Joker (OGN), Batman: Damned, Lex Luthor: Man of Steel.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Lee Bermejo');

-- 30. Daniel Warren Johnson — Transformers, Wonder Woman: Dead Earth
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Daniel Warren Johnson', 'artist', 2014, NULL, ARRAY['DC','IMAGE','SKYBOUND'], 'stylized', true,
       'Transformers, Wonder Woman: Dead Earth, Murder Falcon. Writer/artist.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Daniel Warren Johnson');


-- =============================================================================
-- TIER 3: DECEASED/LEGACY — HIGH VALUE SIGNATURES (5)
-- =============================================================================

-- 31. Bernie Wrightson — Swamp Thing creator (deceased 2017)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Bernie Wrightson', 'artist', 1968, 2017, ARRAY['DC','MARVEL'], 'cursive', true,
       'Swamp Thing co-creator, Frankenstein illustrator. Deceased 2017. Very valuable signatures.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Bernie Wrightson');

-- 32. Tim Sale — Batman: The Long Halloween (deceased 2022)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Tim Sale', 'artist', 1983, 2022, ARRAY['DC','MARVEL'], 'cursive', true,
       'Batman: Long Halloween/Dark Victory/Haunted Knight, Superman for All Seasons. Deceased 2022.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Tim Sale');

-- 33. Darwyn Cooke — DC: The New Frontier (deceased 2016)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Darwyn Cooke', 'artist', 1985, 2016, ARRAY['DC','MARVEL','IDW'], 'stylized', true,
       'DC: The New Frontier, Catwoman. Deceased 2016. Distinctive retro-style signature.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Darwyn Cooke');

-- 34. Mike Wieringo — Flash, Fantastic Four (deceased 2007)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Mike Wieringo', 'artist', 1989, 2007, ARRAY['MARVEL','DC'], 'cursive', true,
       'Flash (with Waid), Fantastic Four, Tellos. Deceased 2007. CONFUSION NOTE: shares "Mike" with Mignola/Zeck.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Mike Wieringo');

-- 35. Herb Trimpe — First Wolverine appearance (deceased 2015)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Herb Trimpe', 'artist', 1966, 2015, ARRAY['MARVEL'], 'cursive', true,
       'Incredible Hulk #181 (1st Wolverine). Deceased 2015. Signatures very valuable on Hulk/Wolverine books.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Herb Trimpe');


-- =============================================================================
-- TIER 4: HIGH VALUE WRITERS (10)
-- =============================================================================

-- 36. Mark Waid — Flash, Kingdom Come
-- CONFUSION RISK: Name overlap with Mark Millar (existing). Both "Mark M..." writers, both cursive.
-- Mitigation: Different letterforms. Waid = DC-heavy, Millar = Marvel/Image-heavy.
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Mark Waid', 'writer', 1987, NULL, ARRAY['DC','MARVEL'], 'cursive', true,
       'Flash, Kingdom Come, Daredevil. CONFUSION PAIR: Mark Millar — similar name but different letterforms and publisher emphasis.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Mark Waid');

-- 37. Peter David — Incredible Hulk 12-year run
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Peter David', 'writer', 1985, NULL, ARRAY['MARVEL','DC'], 'cursive', true,
       'Incredible Hulk (12-year run), X-Factor, Spider-Man 2099. Prolific convention signer.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Peter David');

-- 38. Robert Kirkman — Walking Dead, Invincible
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Robert Kirkman', 'writer', 2000, NULL, ARRAY['IMAGE','SKYBOUND','MARVEL'], 'cursive', true,
       'Walking Dead, Invincible creator. Image partner. Extremely high market value for signed books.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Robert Kirkman');

-- 39. Jason Aaron — Thor, Avengers
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Jason Aaron', 'writer', 2007, NULL, ARRAY['MARVEL','DC','IMAGE'], 'cursive', true,
       'Thor: God of Thunder, Avengers, Southern Bastards.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Jason Aaron');

-- 40. Garth Ennis — Preacher, Punisher
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Garth Ennis', 'writer', 1991, NULL, ARRAY['DC','MARVEL','IMAGE','DYNAMITE'], 'cursive', true,
       'Preacher, Punisher MAX, The Boys creator.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Garth Ennis');

-- 41. Warren Ellis — Authority, Planetary
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Warren Ellis', 'writer', 1994, NULL, ARRAY['MARVEL','DC','IMAGE','WILDSTORM'], 'print', true,
       'Authority, Planetary, Transmetropolitan, Iron Man: Extremis.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Warren Ellis');

-- 42. Donny Cates — Venom, Thor (modern hot writer)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Donny Cates', 'writer', 2014, NULL, ARRAY['MARVEL','IMAGE'], 'print', true,
       'Venom (King in Black), Thor, God Country. Very active convention signer.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Donny Cates');

-- 43. Chip Zdarsky — Batman, Daredevil
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Chip Zdarsky', 'writer', 2014, NULL, ARRAY['MARVEL','DC','IMAGE'], 'cursive', true,
       'Batman, Daredevil, Sex Criminals. Writer/artist.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Chip Zdarsky');

-- 44. Matt Fraction — Hawkeye, Iron Man
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Matt Fraction', 'writer', 2001, NULL, ARRAY['MARVEL','IMAGE'], 'cursive', true,
       'Hawkeye (with Aja), Invincible Iron Man, Sex Criminals.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Matt Fraction');

-- 45. Larry Hama — G.I. Joe (prolific signer)
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Larry Hama', 'writer', 1969, NULL, ARRAY['MARVEL','IDW'], 'cursive', true,
       'G.I. Joe: A Real American Hero (155-issue run). Wolverine. One of the most prolific con signers.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Larry Hama');


-- =============================================================================
-- TIER 5: COVER ARTISTS — MODERN VARIANT MARKET (7)
-- =============================================================================

-- 46. Mark Brooks — Marvel variant cover king
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Mark Brooks', 'cover_artist', 2002, NULL, ARRAY['MARVEL'], 'cursive', true,
       'Premier Marvel variant cover artist. Connecting covers specialist. CONFUSION NOTE: "Mark B" overlap with Mark Bagley.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Mark Brooks');

-- 47. Skottie Young — Baby variant covers, I Hate Fairyland
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Skottie Young', 'cover_artist', 2003, NULL, ARRAY['MARVEL','IMAGE'], 'stylized', true,
       'Baby variant covers, I Hate Fairyland, Oz adaptations. Very distinctive stylized signature.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Skottie Young');

-- 48. Jenny Frison — DC/Image variant covers
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Jenny Frison', 'cover_artist', 2007, NULL, ARRAY['DC','IMAGE'], 'cursive', true,
       'Wonder Woman, Catwoman variant covers. Rising market value. CONFUSION NOTE: shares "Jen" prefix with Jen Bartel but different full names.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Jenny Frison');

-- 49. Jen Bartel — Marvel/DC variant covers
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Jen Bartel', 'cover_artist', 2017, NULL, ARRAY['MARVEL','DC'], 'stylized', true,
       'Women of Marvel covers, Blackbird. CONFUSION NOTE: shares "Jen" prefix with Jenny Frison but different full names.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Jen Bartel');

-- 50. Derrick Chew — Modern variant cover artist
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Derrick Chew', 'cover_artist', 2019, NULL, ARRAY['MARVEL','DC'], 'stylized', true,
       'Variant cover artist. Rising market value in modern era.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Derrick Chew');

-- 51. Clayton Crain — Carnage, X-Force, distinctive painted style
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Clayton Crain', 'cover_artist', 2003, NULL, ARRAY['MARVEL'], 'stylized', true,
       'Carnage, X-Force, Ghost Rider. Distinctive digital painting style.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Clayton Crain');

-- 52. Rafael Albuquerque — American Vampire
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Rafael Albuquerque', 'artist', 2005, NULL, ARRAY['DC','IMAGE'], 'stylized', true,
       'American Vampire (with Snyder), Blue Beetle, Batgirl variant covers.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Rafael Albuquerque');


-- =============================================================================
-- TIER 6: ERA/PUBLISHER COVERAGE + RISING STARS (5)
-- =============================================================================

-- 53. Kieron Gillen — Immortal X-Men, DIE
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Kieron Gillen', 'writer', 2006, NULL, ARRAY['MARVEL','DC','IMAGE'], 'cursive', true,
       'Immortal X-Men, DIE, Young Avengers, The Wicked + The Divine.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Kieron Gillen');

-- 54. Joshua Williamson — Flash, Dark Crisis
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Joshua Williamson', 'writer', 2011, NULL, ARRAY['DC','IMAGE'], 'cursive', true,
       'The Flash (5-year run), Dark Crisis, Nailbiter.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Joshua Williamson');

-- 55. Sara Pichelli — Miles Morales Spider-Man creator
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Sara Pichelli', 'artist', 2008, NULL, ARRAY['MARVEL'], 'cursive', true,
       'Ultimate Spider-Man (Miles Morales co-creator with Bendis). Guardians of the Galaxy.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Sara Pichelli');

-- 56. Pepe Larraz — House of X, X-Men
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Pepe Larraz', 'artist', 2011, NULL, ARRAY['MARVEL'], 'cursive', true,
       'House of X (Hickman era X-Men launch), Avengers. Premier modern Marvel artist.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Pepe Larraz');

-- 57. Mitch Gerads — Mister Miracle, Batman
INSERT INTO creator_signatures (creator_name, role, career_start, career_end, publisher_affiliations, signature_style, active, notes)
SELECT 'Mitch Gerads', 'artist', 2011, NULL, ARRAY['DC','IMAGE'], 'print', true,
       'Mister Miracle (with Tom King), Batman. Eisner Award winner.'
WHERE NOT EXISTS (SELECT 1 FROM creator_signatures WHERE creator_name = 'Mitch Gerads');


-- =============================================================================
-- CONFUSION RISK SUMMARY
-- =============================================================================
-- The following confusion pairs are flagged in the notes field for each creator.
-- The orchestrator pre-filter uses publisher_affiliations + career_years to help
-- disambiguate. Reference images are the primary differentiator.
--
-- HIGH RISK (same last name, same era/publishers):
--   Adam Kubert ↔ Andy Kubert (brothers)
--
-- MEDIUM RISK (same first name, overlapping publishers):
--   Jim Cheung ↔ Jim Lee / Jim Steranko / Jim Starlin
--   Mark Waid ↔ Mark Millar (existing)
--   Mark Bagley ↔ Mark Brooks
--   Ryan Stegman ↔ Ryan Ottley
--   Mike Zeck ↔ Mike Mignola (existing) / Mike Wieringo
--   Frank Cho ↔ Frank Miller (existing) — surname vs first name, no real risk
--   Bill Sienkiewicz ↔ Bill Finger (existing) — different eras, no real risk
--
-- LOW RISK (partial name overlap only):
--   Jenny Frison ↔ Jen Bartel (Jen prefix only)
--   Gary Frank ↔ Frank Miller/Frank Cho — surname vs first name, minimal risk
--
-- =============================================================================


-- =============================================================================
-- VERIFICATION: Count total creators after migration
-- =============================================================================
-- Run this after the migration to verify:
-- SELECT COUNT(*) AS total_creators FROM creator_signatures WHERE active = true;
-- Expected: ~100 (43 existing + 57 new)
--
-- SELECT creator_name, career_start, career_end, publisher_affiliations, signature_style
-- FROM creator_signatures
-- ORDER BY creator_name;
-- =============================================================================
