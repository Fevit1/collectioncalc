"""
eBay Sales Title Normalization Migration
=========================================
Adds normalized columns to ebay_sales without modifying original data.

New columns:
  - canonical_title: Standardized series name (e.g., "The Incredible Hulk")
  - is_facsimile: Boolean - facsimile edition
  - is_reprint: Boolean - reprint/milestone/legends/true believers
  - is_variant: Boolean - variant cover, newsstand, exclusive
  - is_signed: Boolean - signed/SS/signature series
  - is_lot: Boolean - lot/bundle/set
  - grade_from_title: Numeric grade extracted from title text
  - grading_company: CGC/CBCS/PGX if mentioned in title
  - title_notes: Everything stripped out, preserved as text

Usage:
  python db_migrate_normalize_titles.py              # Run full migration
  python db_migrate_normalize_titles.py --dry-run    # Preview without writing
  python db_migrate_normalize_titles.py --sample 50  # Process only 50 records
"""

import os
import re
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# CANONICAL TITLES DATABASE
# Format: canonical_name -> [search patterns]
# Patterns are checked against lowercase cleaned title
# Order matters: longer/more specific patterns first
# ============================================================

CANONICAL_TITLES = {
    # === MARVEL - Spider-Man Family ===
    "The Amazing Spider-Man": ["amazing spider-man", "amazing spiderman", "asm"],
    "Peter Parker, The Spectacular Spider-Man": ["spectacular spider-man", "spectacular spiderman"],
    "Web of Spider-Man": ["web of spider-man", "web of spiderman"],
    "Spider-Man": ["spider-man", "spiderman"],  # Generic catch-all, keep last in spider family
    "Spider-Man 2099": ["spider-man 2099", "spiderman 2099"],
    "Miles Morales: Spider-Man": ["miles morales"],
    "Spider-Gwen": ["spider-gwen"],
    "Spider-Woman": ["spider-woman"],
    "Superior Spider-Man": ["superior spider-man"],
    "Symbiote Spider-Man": ["symbiote spider-man"],
    "Amazing Fantasy": ["amazing fantasy"],

    # === MARVEL - X-Men Family ===
    "The Uncanny X-Men": ["uncanny x-men"],
    "X-Men": ["x-men"],
    "New Mutants": ["new mutants"],
    "X-Force": ["x-force"],
    "Wolverine": ["wolverine"],
    "Cable": ["cable"],
    "Deadpool": ["deadpool"],
    "X-Factor": ["x-factor"],
    "Excalibur": ["excalibur"],
    "Generation X": ["generation x"],
    "Giant-Size X-Men": ["giant-size x-men", "giant size x-men"],

    # === MARVEL - Avengers Family ===
    "The Avengers": ["the avengers", "avengers"],
    "The Invincible Iron Man": ["invincible iron man"],
    "Iron Man": ["iron man"],
    "Captain America": ["captain america"],
    "The Mighty Thor": ["mighty thor"],
    "Thor": ["thor"],
    "The Incredible Hulk": ["incredible hulk"],
    "Hulk": ["hulk"],
    "Hawkeye": ["hawkeye"],
    "Black Widow": ["black widow"],
    "Ant-Man": ["ant-man"],
    "West Coast Avengers": ["west coast avengers"],
    "New Avengers": ["new avengers"],
    "Secret Avengers": ["secret avengers"],

    # === MARVEL - Fantastic Four ===
    "Fantastic Four": ["fantastic four"],
    "Silver Surfer": ["silver surfer"],
    "The Thing": ["the thing"],

    # === MARVEL - Other Major ===
    "Daredevil": ["daredevil"],
    "The Punisher": ["punisher"],
    "Ghost Rider": ["ghost rider"],
    "Doctor Strange": ["doctor strange", "dr. strange", "dr strange"],
    "Moon Knight": ["moon knight"],
    "Black Panther": ["black panther"],
    "Luke Cage": ["luke cage", "power man"],
    "Iron Fist": ["iron fist"],
    "She-Hulk": ["she-hulk"],
    "Captain Marvel": ["captain marvel"],
    "Ms. Marvel": ["ms. marvel", "ms marvel"],
    "Alpha Flight": ["alpha flight"],
    "The Defenders": ["defenders"],
    "Marvel Team-Up": ["marvel team-up", "marvel team up"],
    "Marvel Two-In-One": ["marvel two-in-one", "marvel two in one"],
    "Marvel Super Heroes Secret Wars": ["secret wars"],
    "The Infinity Gauntlet": ["infinity gauntlet"],
    "Venom": ["venom"],
    "Carnage": ["carnage"],
    "Morbius": ["morbius"],
    "Blade": ["blade"],
    "Eternals": ["eternals"],
    "Shang-Chi": ["shang-chi", "shang chi"],
    "The Invaders": ["the invaders", "invaders"],

    # === MARVEL - Cosmic/Events ===
    "Guardians of the Galaxy": ["guardians of the galaxy"],
    "Star Wars": ["star wars"],
    "Darth Vader": ["darth vader"],
    "Conan the Barbarian": ["conan the barbarian", "conan"],
    "Tomb of Dracula": ["tomb of dracula"],
    "Werewolf by Night": ["werewolf by night"],
    "Marvel Spotlight": ["marvel spotlight"],
    "Marvel Premiere": ["marvel premiere"],
    "Tales of Suspense": ["tales of suspense"],
    "Tales to Astonish": ["tales to astonish"],
    "Journey into Mystery": ["journey into mystery"],
    "Strange Tales": ["strange tales"],

    # === DC - Batman Family ===
    "Batman": ["batman"],
    "Detective Comics": ["detective comics", "'tec"],
    "Batman: The Dark Knight Returns": ["dark knight returns"],
    "Batman: The Killing Joke": ["killing joke"],
    "Batgirl": ["batgirl"],
    "Batwoman": ["batwoman"],
    "Robin": ["robin"],
    "Nightwing": ["nightwing"],
    "Catwoman": ["catwoman"],
    "Harley Quinn": ["harley quinn"],
    "Batman Beyond": ["batman beyond"],
    "Batman: Legends of the Dark Knight": ["legends of the dark knight"],
    "Shadow of the Bat": ["shadow of the bat"],

    # === DC - Superman Family ===
    "Superman": ["superman"],
    "Action Comics": ["action comics"],
    "Superman's Pal Jimmy Olsen": ["jimmy olsen"],
    "Supergirl": ["supergirl"],
    "Superboy": ["superboy"],

    # === DC - Justice League ===
    "Justice League of America": ["justice league"],
    "Wonder Woman": ["wonder woman"],
    "The Flash": ["the flash", "flash"],
    "Green Lantern": ["green lantern"],
    "Aquaman": ["aquaman"],
    "Green Arrow": ["green arrow"],
    "Hawkman": ["hawkman"],
    "Teen Titans": ["teen titans"],
    "New Teen Titans": ["new teen titans"],
    "The New Titans": ["new titans"],

    # === DC - Other Major ===
    "Swamp Thing": ["swamp thing"],
    "The Sandman": ["sandman"],
    "Watchmen": ["watchmen"],
    "Crisis on Infinite Earths": ["crisis on infinite earths"],
    "Saga of the Swamp Thing": ["saga of the swamp thing"],
    "John Constantine, Hellblazer": ["hellblazer", "constantine"],
    "Doom Patrol": ["doom patrol"],
    "Suicide Squad": ["suicide squad"],
    "Deathstroke": ["deathstroke"],
    "Lobo": ["lobo"],
    "Preacher": ["preacher"],
    "Transmetropolitan": ["transmetropolitan"],
    "Fables": ["fables"],
    "Y: The Last Man": ["y the last man"],
    "100 Bullets": ["100 bullets"],
    "Absolute Batman": ["absolute batman"],

    # === IMAGE ===
    "Spawn": ["spawn"],
    "The Walking Dead": ["walking dead"],
    "Invincible": ["invincible"],
    "Saga": ["saga"],
    "Savage Dragon": ["savage dragon"],
    "Witchblade": ["witchblade"],
    "The Darkness": ["the darkness"],
    "Youngblood": ["youngblood"],
    "Radiant Black": ["radiant black"],
    "Ice Cream Man": ["ice cream man"],
    "Something is Killing the Children": ["something is killing the children"],
    "Department of Truth": ["department of truth"],
    "Bone": ["bone"],
    "Deadly Class": ["deadly class"],
    "Monstress": ["monstress"],
    "East of West": ["east of west"],
    "Nocterra": ["nocterra"],
    "Void Rivals": ["void rivals"],
    "Transformers": ["transformers"],
    "G.I. Joe": ["g.i. joe", "gi joe"],

    # === DARK HORSE ===
    "Hellboy": ["hellboy"],
    "Sin City": ["sin city"],
    "300": ["300"],
    "The Mask": ["the mask"],
    "Aliens": ["aliens"],
    "Predator": ["predator"],
    "Usagi Yojimbo": ["usagi yojimbo"],
    "Black Hammer": ["black hammer"],

    # === IDW ===
    "Teenage Mutant Ninja Turtles": ["teenage mutant ninja turtles", "tmnt"],
    "Locke & Key": ["locke & key", "locke and key"],

    # === VALIANT ===
    "X-O Manowar": ["x-o manowar"],
    "Harbinger": ["harbinger"],
    "Bloodshot": ["bloodshot"],
    "Ninjak": ["ninjak"],
    "Rai": ["rai"],

    # === OTHER PUBLISHERS ===
    "Archie": ["archie"],
    "Teenage Mutant Ninja Turtles Adventures": ["tmnt adventures"],
    "Cerebus": ["cerebus"],
    "Groo the Wanderer": ["groo"],
    "Elfquest": ["elfquest"],
    "Red Sonja": ["red sonja"],
    "Vampirella": ["vampirella"],
    "The Boys": ["the boys"],
}

# ============================================================
# REGEX PATTERNS FOR METADATA EXTRACTION
# ============================================================

# Facsimile detection
FACSIMILE_PATTERNS = [
    r'\bfacsimile\b', r'\bfascimile\b',  # common misspelling
]

# Reprint detection (non-facsimile)
REPRINT_PATTERNS = [
    r'\breprint\b', r'\bmilestone edition\b', r'\btrue believers\b',
    r'\bmarvel legends\b.*\breprint\b', r'\bmarvel legends\b.*\bvariant\b.*\btoy.?biz\b',
    r'\bsony pictures reprint\b', r'\bclassics\b.*\breprint\b',
]

# Variant detection
VARIANT_PATTERNS = [
    r'\bvariant\b', r'\bnewsstand\b', r'\bdirect\b(?:\s+edition)?',
    r'\bexclusive\b', r'\bfoil\b', r'\bchase\b', r'\bvirgin\b',
    r'\bhomage\b', r'\bincentive\b', r'\bsketch\b', r'\bblank\b',
    r'\b1:\d+\b',  # ratio variants like 1:25
    r'\bcover [b-z]\b',  # Cover B, Cover C, etc.
    r'\bunknown\s+(?:comics?\s+)?(?:variant|exclusive)\b',
    r'\bloot crate\b',
]

# Signed detection
SIGNED_PATTERNS = [
    r'\bsigned\b', r'\bsignature\s+series\b', r'\b(?:^|\s)ss\b',
    r'\bstan lee\b.*\bsign', r'\bautograph\b',
]

# Lot detection
LOT_PATTERNS = [
    r'\blot\s+of\b', r'\bbundle\b', r'\bset\s+of\b',
    r'\bcombine\s+ship\b', r'\bfree\s+combine\b',
    r'\bargain\s+books?\b', r'\bbargain\b',
]

# Grade extraction from title
GRADE_PATTERN = r'\b(?:cgc|cbcs|pgx)\s+(?:graded?\s+)?(\d+\.?\d*)\b'
GRADE_PATTERN_ALT = r'\bgrade\s+(\d+\.?\d*)\b'

# Grading company extraction
GRADING_COMPANY_PATTERN = r'\b(cgc|cbcs|pgx)\b'

# Noise to strip for canonical matching
NOISE_PATTERNS = [
    r'\bcgc\b.*?(?=\s|$)', r'\bcbcs\b.*?(?=\s|$)', r'\bpgx\b.*?(?=\s|$)',
    r'\bgrade\s+\d+\.?\d*\b', r'\bgraded\b',
    r'\bfacsimile\b', r'\bfascimile\b', r'\breprint\b',
    r'\bmilestone\s+edition\b', r'\btrue\s+believers?\b',
    r'\bvariant\b', r'\bnewsstand\b', r'\bdirect\b',
    r'\bexclusive\b', r'\bfoil\b', r'\bvirgin\b',
    r'\b(?:1st|first)\s+(?:app(?:earance)?|print(?:ing)?)\b',
    r'\bkey\b', r'\bgrail\b', r'\bhot\b', r'\brare\b',
    r'\bwhite\s+pages?\b', r'\bow\s+to\s+white\b', r'\boff.?white\b',
    r'\bfree\s+ship\w*\b', r'\bships?\s+free\b',
    r'\bsold\s+out\b', r'\bno\s+reserve\b',
    r'\bcond(?:ition)?\b', r'\bquality\b',
    r'[\U0001f300-\U0001f9ff]',  # emojis
    r'[🔥🔑🎯📦💥⭐️✨]',  # common eBay emojis
    r'\(\s*\)', r'\[\s*\]',  # empty parens/brackets
    r'\bmarvel\s+comics?\b', r'\bdc\s+comics?\b', r'\bimage\s+comics?\b',
    r'\bdark\s+horse\s+comics?\b', r'\bidw\b', r'\bboom\b',
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b',  # dates
    r'\(\s*(?:marvel|dc|image)\s*(?:,\s*\d{4}\s*)?\)',  # (Marvel, 2019)
    r'\b\d{10,13}\b',  # UPC/ISBN numbers
    r'\bw/\s*\w+', r'\b/\s*$',  # trailing slashes and w/ notes
    r'\bor\s+better\b',
    r'\bcomic\s+book\b', r'\bcomic\b',
    r'\bmarvel\b', r'\bdc\b',
    r'\b(?:very\s+)?(?:fine|good|poor|mint|near)\b',
    r'[+/()]',
]


def extract_flags(title):
    """Extract boolean flags from a parsed title."""
    lower = title.lower()

    is_facsimile = any(re.search(p, lower) for p in FACSIMILE_PATTERNS)
    is_reprint = is_facsimile or any(re.search(p, lower) for p in REPRINT_PATTERNS)
    is_variant = any(re.search(p, lower) for p in VARIANT_PATTERNS)
    is_signed = any(re.search(p, lower) for p in SIGNED_PATTERNS)
    is_lot = any(re.search(p, lower) for p in LOT_PATTERNS)

    # Grade from title
    grade_match = re.search(GRADE_PATTERN, lower)
    if not grade_match:
        grade_match = re.search(GRADE_PATTERN_ALT, lower)
    grade_from_title = float(grade_match.group(1)) if grade_match else None
    if grade_from_title and (grade_from_title > 10 or grade_from_title < 0.5):
        grade_from_title = None  # Invalid grade

    # Grading company
    company_match = re.search(GRADING_COMPANY_PATTERN, lower)
    grading_company = company_match.group(1).upper() if company_match else None

    return {
        'is_facsimile': is_facsimile,
        'is_reprint': is_reprint,
        'is_variant': is_variant,
        'is_signed': is_signed,
        'is_lot': is_lot,
        'grade_from_title': grade_from_title,
        'grading_company': grading_company,
    }


def clean_title_for_matching(title):
    """Strip noise from title to improve canonical matching."""
    cleaned = title.lower()
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Remove leading/trailing punctuation
    cleaned = re.sub(r'^[\s\-:,]+|[\s\-:,]+$', '', cleaned)
    return cleaned


def match_canonical_title(parsed_title):
    """Match a parsed title to a canonical title."""
    cleaned = clean_title_for_matching(parsed_title)
    lower_original = parsed_title.lower()

    best_match = None
    best_score = 0

    for canonical, patterns in CANONICAL_TITLES.items():
        for pattern in patterns:
            # Check against both original and cleaned
            if pattern in lower_original or pattern in cleaned:
                # Score by pattern length (longer = more specific = better)
                score = len(pattern)
                if score > best_score:
                    best_score = score
                    best_match = canonical

    return best_match


def build_title_notes(parsed_title, flags):
    """Build a notes string from extracted metadata."""
    notes = []
    if flags['is_facsimile']:
        notes.append('facsimile')
    if flags['is_reprint'] and not flags['is_facsimile']:
        notes.append('reprint')
    if flags['is_variant']:
        notes.append('variant')
    if flags['is_signed']:
        notes.append('signed')
    if flags['is_lot']:
        notes.append('lot/bundle')
    if flags['grading_company']:
        grade_str = f"{flags['grading_company']}"
        if flags['grade_from_title']:
            grade_str += f" {flags['grade_from_title']}"
        notes.append(grade_str)
    return '; '.join(notes) if notes else None


def run_migration(dry_run=False, sample_size=None):
    """Run the title normalization migration."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    # Step 1: Add columns if they don't exist
    if not dry_run:
        print("Step 1: Adding new columns...")
        alter_statements = [
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS canonical_title TEXT",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS is_facsimile BOOLEAN DEFAULT FALSE",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS is_reprint BOOLEAN DEFAULT FALSE",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS is_variant BOOLEAN DEFAULT FALSE",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS is_signed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS is_lot BOOLEAN DEFAULT FALSE",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS grade_from_title DECIMAL(3,1)",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS grading_company VARCHAR(10)",
            "ALTER TABLE ebay_sales ADD COLUMN IF NOT EXISTS title_notes TEXT",
        ]
        for stmt in alter_statements:
            cur.execute(stmt)
        conn.commit()
        print("  Columns added.")

    # Step 2: Fetch all records
    print("Step 2: Fetching records...")
    query = "SELECT id, parsed_title FROM ebay_sales WHERE parsed_title IS NOT NULL"
    if sample_size:
        query += f" LIMIT {sample_size}"
    cur.execute(query)
    records = cur.fetchall()
    print(f"  Found {len(records)} records to process.")

    # Step 3: Process each record
    print("Step 3: Processing titles...")
    stats = {
        'total': len(records),
        'matched': 0,
        'unmatched': 0,
        'facsimile': 0,
        'reprint': 0,
        'variant': 0,
        'signed': 0,
        'lot': 0,
        'has_grade': 0,
    }

    unmatched_titles = []
    updates = []

    for i, record in enumerate(records):
        parsed_title = record['parsed_title']

        # Extract flags
        flags = extract_flags(parsed_title)

        # Match canonical title
        canonical = match_canonical_title(parsed_title)

        # Build notes
        title_notes = build_title_notes(parsed_title, flags)

        # Track stats
        if canonical:
            stats['matched'] += 1
        else:
            stats['unmatched'] += 1
            unmatched_titles.append(parsed_title)

        if flags['is_facsimile']: stats['facsimile'] += 1
        if flags['is_reprint']: stats['reprint'] += 1
        if flags['is_variant']: stats['variant'] += 1
        if flags['is_signed']: stats['signed'] += 1
        if flags['is_lot']: stats['lot'] += 1
        if flags['grade_from_title']: stats['has_grade'] += 1

        updates.append((
            canonical,
            flags['is_facsimile'],
            flags['is_reprint'],
            flags['is_variant'],
            flags['is_signed'],
            flags['is_lot'],
            flags['grade_from_title'],
            flags['grading_company'],
            title_notes,
            record['id'],
        ))

        if (i + 1) % 2000 == 0:
            print(f"  Processed {i + 1}/{len(records)}...")

    # Step 4: Apply updates
    if not dry_run:
        print("Step 4: Writing updates to database...")
        update_sql = """
            UPDATE ebay_sales SET
                canonical_title = %s,
                is_facsimile = %s,
                is_reprint = %s,
                is_variant = %s,
                is_signed = %s,
                is_lot = %s,
                grade_from_title = %s,
                grading_company = %s,
                title_notes = %s
            WHERE id = %s
        """
        # Batch update
        batch_size = 500
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            cur.executemany(update_sql, batch)
            conn.commit()
            print(f"  Written {min(i + batch_size, len(updates))}/{len(updates)}...")

        # Add index on canonical_title for fast FMV lookups
        print("Step 5: Creating index...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ebay_sales_canonical_title ON ebay_sales(canonical_title)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ebay_sales_is_reprint ON ebay_sales(is_reprint)")
        conn.commit()
        print("  Indexes created.")
    else:
        print("Step 4: DRY RUN - no database writes.")

    # Print results
    print("\n" + "=" * 60)
    print("NORMALIZATION RESULTS")
    print("=" * 60)
    print(f"Total records:     {stats['total']:,}")
    print(f"Matched canonical: {stats['matched']:,} ({100*stats['matched']/stats['total']:.1f}%)")
    print(f"Unmatched:         {stats['unmatched']:,} ({100*stats['unmatched']/stats['total']:.1f}%)")
    print(f"")
    print(f"Flags extracted:")
    print(f"  Facsimile:       {stats['facsimile']:,}")
    print(f"  Reprint:         {stats['reprint']:,}")
    print(f"  Variant:         {stats['variant']:,}")
    print(f"  Signed:          {stats['signed']:,}")
    print(f"  Lot/Bundle:      {stats['lot']:,}")
    print(f"  Grade in title:  {stats['has_grade']:,}")

    # Show top unmatched titles (grouped by first few words)
    if unmatched_titles:
        print(f"\nTop 30 unmatched titles (sample):")
        for t in unmatched_titles[:30]:
            print(f"  - {t[:80]}")

    cur.close()
    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    sample_size = None
    for arg in sys.argv:
        if arg.startswith('--sample'):
            try:
                sample_size = int(sys.argv[sys.argv.index(arg) + 1])
            except (ValueError, IndexError):
                sample_size = 100

    run_migration(dry_run=dry_run, sample_size=sample_size)
