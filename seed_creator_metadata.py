"""
Seed script: Populate career_start, career_end, publisher_affiliations, and signature_style
for all creators in the creator_signatures table.

Run AFTER migrations:
  1. migrations/add_orchestrator_columns.sql
  2. migrations/add_signature_identification_log.sql

Usage:
    python seed_creator_metadata.py                  # uses DATABASE_URL env var
    python seed_creator_metadata.py <DATABASE_URL>   # explicit URL

This script is idempotent — safe to run multiple times.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# ---------------------------------------------------------------------------
# Creator metadata for all ~43 creators in the production database
# Sources: Wikipedia, Grand Comics Database, convention signing records
#
# Fields:
#   career_start: Year of first professional comic work
#   career_end:   Year of last work (None = still active)
#   publishers:   List of major publisher affiliations (uppercase)
#   style:        Signature visual style category
#                 Values: initials | cursive | stylized | print | mixed
# ---------------------------------------------------------------------------

CREATOR_METADATA = {
    # === ARTISTS (20) ===
    "Jim Lee": {
        "career_start": 1987,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE", "WILDSTORM"],
        "style": "stylized",
    },
    "Todd McFarlane": {
        "career_start": 1984,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "stylized",
    },
    "Rob Liefeld": {
        "career_start": 1988,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "print",
    },
    "John Romita Jr.": {
        "career_start": 1977,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "John Romita Sr.": {
        "career_start": 1949,
        "career_end": 2023,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Neal Adams": {
        "career_start": 1959,
        "career_end": 2022,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Frank Miller": {
        "career_start": 1978,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "DARK HORSE"],
        "style": "stylized",
    },
    "George Perez": {
        "career_start": 1974,
        "career_end": 2022,
        "publishers": ["MARVEL", "DC", "CROSSGEN"],
        "style": "cursive",
    },
    "Jim Steranko": {
        "career_start": 1966,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "stylized",
    },
    "Jack Kirby": {
        "career_start": 1937,
        "career_end": 1994,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Steve Ditko": {
        "career_start": 1953,
        "career_end": 2018,
        "publishers": ["MARVEL", "DC", "CHARLTON"],
        "style": "print",
    },
    "John Byrne": {
        "career_start": 1975,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "DARK HORSE", "IDW"],
        "style": "print",
    },
    "Art Adams": {
        "career_start": 1985,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "DARK HORSE", "IMAGE"],
        "style": "cursive",
    },
    "Alex Ross": {
        "career_start": 1993,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "J. Scott Campbell": {
        "career_start": 1994,
        "career_end": None,
        "publishers": ["IMAGE", "MARVEL", "DC"],
        "style": "cursive",
    },
    "Adam Hughes": {
        "career_start": 1989,
        "career_end": None,
        "publishers": ["DC", "MARVEL", "DARK HORSE"],
        "style": "initials",
    },
    "Mike Mignola": {
        "career_start": 1982,
        "career_end": None,
        "publishers": ["DARK HORSE", "MARVEL", "DC"],
        "style": "print",
    },
    "Jae Lee": {
        "career_start": 1990,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "stylized",
    },
    "Greg Capullo": {
        "career_start": 1988,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "Ivan Reis": {
        "career_start": 1994,
        "career_end": None,
        "publishers": ["DC", "MARVEL"],
        "style": "print",
    },

    # === WRITERS (13) ===
    "Stan Lee": {
        "career_start": 1939,
        "career_end": 2018,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Chris Claremont": {
        "career_start": 1969,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Brian Michael Bendis": {
        "career_start": 1993,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE", "DARK HORSE"],
        "style": "stylized",
    },
    "Geoff Johns": {
        "career_start": 1999,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "cursive",
    },
    "Grant Morrison": {
        "career_start": 1978,
        "career_end": None,
        "publishers": ["DC", "MARVEL", "IMAGE"],
        "style": "stylized",
    },
    "Alan Moore": {
        "career_start": 1979,
        "career_end": 2019,
        "publishers": ["DC", "IMAGE", "WILDSTORM"],
        "style": "cursive",
    },
    "Neil Gaiman": {
        "career_start": 1987,
        "career_end": None,
        "publishers": ["DC", "MARVEL", "DARK HORSE"],
        "style": "cursive",
    },
    "Jonathan Hickman": {
        "career_start": 2006,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE"],
        "style": "print",
    },
    "Scott Snyder": {
        "career_start": 2009,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "cursive",
    },
    "Mark Millar": {
        "career_start": 1994,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "Ed Brubaker": {
        "career_start": 1993,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "Tom King": {
        "career_start": 2014,
        "career_end": None,
        "publishers": ["DC", "MARVEL"],
        "style": "print",
    },
    "James Tynion IV": {
        "career_start": 2012,
        "career_end": None,
        "publishers": ["DC", "BOOM"],
        "style": "stylized",
    },

    # === COVER ARTISTS (3) ===
    "Stanley \"Artgerm\" Lau": {
        "career_start": 2005,
        "career_end": None,
        "publishers": ["DC", "MARVEL"],
        "style": "print",
    },
    "Gabriele Dell'Otto": {
        "career_start": 2002,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "stylized",
    },
    "Peach Momoko": {
        "career_start": 2019,
        "career_end": None,
        "publishers": ["MARVEL", "BOOM"],
        "style": "mixed",
    },

    # === LEGENDS / CREATORS (4) ===
    "Bob Kane": {
        "career_start": 1936,
        "career_end": 1998,
        "publishers": ["DC"],
        "style": "print",
    },
    "Bill Finger": {
        "career_start": 1938,
        "career_end": 1974,
        "publishers": ["DC"],
        "style": "cursive",
    },
    "Jerry Siegel": {
        "career_start": 1933,
        "career_end": 1996,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Joe Shuster": {
        "career_start": 1933,
        "career_end": 1992,
        "publishers": ["DC"],
        "style": "cursive",
    },

    # === ADDITIONAL CREATORS (if added via admin) ===
    # Jim Starlin (writer/artist)
    "Jim Starlin": {
        "career_start": 1972,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
}


def seed_metadata():
    """Update all creators with career_start, career_end, publisher_affiliations, signature_style."""
    database_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        print("Usage: python seed_creator_metadata.py <DATABASE_URL>")
        print("   Or: set DATABASE_URL environment variable")
        sys.exit(1)

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    try:
        # Get all creators from DB
        cur.execute("SELECT id, creator_name FROM creator_signatures ORDER BY creator_name")
        db_creators = cur.fetchall()
        print(f"Found {len(db_creators)} creators in database\n")

        updated = 0
        skipped = 0
        not_found = []

        for row in db_creators:
            db_name = row['creator_name']
            creator_id = row['id']

            # Try exact match first, then case-insensitive
            meta = CREATOR_METADATA.get(db_name)
            if not meta:
                # Try case-insensitive match
                for key, val in CREATOR_METADATA.items():
                    if key.lower() == db_name.lower():
                        meta = val
                        break

            # Handle George Perez / George Perez accent mismatch
            if not meta and 'perez' in db_name.lower():
                meta = CREATOR_METADATA.get("George Perez")

            if not meta:
                not_found.append(db_name)
                skipped += 1
                continue

            cur.execute("""
                UPDATE creator_signatures
                SET career_start = %s,
                    career_end = %s,
                    publisher_affiliations = %s,
                    signature_style = %s,
                    active = true
                WHERE id = %s
            """, [
                meta["career_start"],
                meta["career_end"],
                meta["publishers"],
                meta["style"],
                creator_id,
            ])
            updated += 1
            career = f"{meta['career_start']}-{'present' if meta['career_end'] is None else meta['career_end']}"
            pubs = ', '.join(meta['publishers'])
            print(f"  Updated: {db_name:30s} | {career:15s} | {pubs:40s} | {meta['style']}")

        conn.commit()

        print(f"\n{'='*80}")
        print(f"Updated: {updated}")
        print(f"Skipped: {skipped}")
        if not_found:
            print(f"\nCreators NOT in seed data (need manual metadata):")
            for name in not_found:
                print(f"  - {name}")
        print(f"\nDone! Run 'SELECT * FROM migration_validation;' to verify.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    seed_metadata()
