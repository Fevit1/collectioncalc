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
import unicodedata
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

    # =================================================================
    # === 57 NEW CREATORS (Session 86 expansion: 43 → 100) ===
    # =================================================================

    # --- TIER 1: HIGH MARKET VALUE ARTISTS (15) ---
    "Walt Simonson": {
        "career_start": 1980,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Marc Silvestri": {
        "career_start": 1986,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE", "TOP COW"],
        "style": "stylized",
    },
    "David Finch": {
        "career_start": 1995,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Adam Kubert": {
        "career_start": 1990,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Andy Kubert": {
        "career_start": 1988,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Frank Cho": {
        "career_start": 1996,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "print",
    },
    "Joe Quesada": {
        "career_start": 1990,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "stylized",
    },
    "Jim Cheung": {
        "career_start": 1995,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Ed McGuinness": {
        "career_start": 1996,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "print",
    },
    "Kevin Eastman": {
        "career_start": 1984,
        "career_end": None,
        "publishers": ["MIRAGE", "IDW"],
        "style": "stylized",
    },
    "Bill Sienkiewicz": {
        "career_start": 1980,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "stylized",
    },
    "Mike Zeck": {
        "career_start": 1974,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Whilce Portacio": {
        "career_start": 1986,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE"],
        "style": "cursive",
    },
    "Erik Larsen": {
        "career_start": 1986,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE"],
        "style": "cursive",
    },
    "Michael Turner": {
        "career_start": 1996,
        "career_end": 2008,
        "publishers": ["TOP COW", "DC", "ASPEN"],
        "style": "cursive",
    },

    # --- TIER 2: STRONG CONVENTION/MODERN ARTISTS (15) ---
    "Ryan Stegman": {
        "career_start": 2009,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Terry Dodson": {
        "career_start": 1993,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Sean Murphy": {
        "career_start": 2005,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "cursive",
    },
    "Patrick Gleason": {
        "career_start": 1998,
        "career_end": None,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Gary Frank": {
        "career_start": 1991,
        "career_end": None,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Mark Bagley": {
        "career_start": 1984,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Humberto Ramos": {
        "career_start": 1994,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "stylized",
    },
    "Leinil Francis Yu": {
        "career_start": 1994,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Ryan Ottley": {
        "career_start": 2003,
        "career_end": None,
        "publishers": ["IMAGE", "MARVEL"],
        "style": "cursive",
    },
    "Jorge Jimenez": {
        "career_start": 2016,
        "career_end": None,
        "publishers": ["DC"],
        "style": "cursive",
    },
    "Dan Mora": {
        "career_start": 2016,
        "career_end": None,
        "publishers": ["DC", "BOOM"],
        "style": "cursive",
    },
    "Olivier Coipel": {
        "career_start": 2000,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Esad Ribic": {
        "career_start": 1997,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Lee Bermejo": {
        "career_start": 2003,
        "career_end": None,
        "publishers": ["DC"],
        "style": "stylized",
    },
    "Daniel Warren Johnson": {
        "career_start": 2014,
        "career_end": None,
        "publishers": ["DC", "IMAGE", "SKYBOUND"],
        "style": "stylized",
    },

    # --- TIER 3: DECEASED/LEGACY HIGH VALUE (5) ---
    "Bernie Wrightson": {
        "career_start": 1968,
        "career_end": 2017,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Tim Sale": {
        "career_start": 1983,
        "career_end": 2022,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Darwyn Cooke": {
        "career_start": 1985,
        "career_end": 2016,
        "publishers": ["DC", "MARVEL", "IDW"],
        "style": "stylized",
    },
    "Mike Wieringo": {
        "career_start": 1989,
        "career_end": 2007,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Herb Trimpe": {
        "career_start": 1966,
        "career_end": 2015,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },

    # --- TIER 4: HIGH VALUE WRITERS (10) ---
    "Mark Waid": {
        "career_start": 1987,
        "career_end": None,
        "publishers": ["DC", "MARVEL"],
        "style": "cursive",
    },
    "Peter David": {
        "career_start": 1985,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "cursive",
    },
    "Robert Kirkman": {
        "career_start": 2000,
        "career_end": None,
        "publishers": ["IMAGE", "SKYBOUND", "MARVEL"],
        "style": "cursive",
    },
    "Jason Aaron": {
        "career_start": 2007,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "Garth Ennis": {
        "career_start": 1991,
        "career_end": None,
        "publishers": ["DC", "MARVEL", "IMAGE", "DYNAMITE"],
        "style": "cursive",
    },
    "Warren Ellis": {
        "career_start": 1994,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE", "WILDSTORM"],
        "style": "print",
    },
    "Donny Cates": {
        "career_start": 2014,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE"],
        "style": "print",
    },
    "Chip Zdarsky": {
        "career_start": 2014,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "Matt Fraction": {
        "career_start": 2001,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE"],
        "style": "cursive",
    },
    "Larry Hama": {
        "career_start": 1969,
        "career_end": None,
        "publishers": ["MARVEL", "IDW"],
        "style": "cursive",
    },

    # --- TIER 5: COVER ARTISTS / VARIANT MARKET (7) ---
    "Mark Brooks": {
        "career_start": 2002,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Skottie Young": {
        "career_start": 2003,
        "career_end": None,
        "publishers": ["MARVEL", "IMAGE"],
        "style": "stylized",
    },
    "Jenny Frison": {
        "career_start": 2007,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "cursive",
    },
    "Jen Bartel": {
        "career_start": 2017,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "stylized",
    },
    "Derrick Chew": {
        "career_start": 2019,
        "career_end": None,
        "publishers": ["MARVEL", "DC"],
        "style": "stylized",
    },
    "Clayton Crain": {
        "career_start": 2003,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "stylized",
    },
    "Rafael Albuquerque": {
        "career_start": 2005,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "stylized",
    },

    # --- TIER 6: ERA/PUBLISHER COVERAGE + RISING STARS (5) ---
    "Kieron Gillen": {
        "career_start": 2006,
        "career_end": None,
        "publishers": ["MARVEL", "DC", "IMAGE"],
        "style": "cursive",
    },
    "Joshua Williamson": {
        "career_start": 2011,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "cursive",
    },
    "Sara Pichelli": {
        "career_start": 2008,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Pepe Larraz": {
        "career_start": 2011,
        "career_end": None,
        "publishers": ["MARVEL"],
        "style": "cursive",
    },
    "Mitch Gerads": {
        "career_start": 2011,
        "career_end": None,
        "publishers": ["DC", "IMAGE"],
        "style": "print",
    },
}


# ---------------------------------------------------------------------------
# Name normalization: strip accents, collapse whitespace, lowercase
# Handles: Pérez→perez, Whilche→match via aliases, etc.
# ---------------------------------------------------------------------------
def _normalize(name: str) -> str:
    """Strip accents and lowercase for fuzzy matching."""
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_only = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_only.strip().lower()

# Known DB→seed name mappings for entries that can't be matched by normalization
NAME_ALIASES = {
    "whilche portacio": "Whilce Portacio",      # DB typo (extra 'h')
}

# ---------------------------------------------------------------------------
# Style confidence overrides — how sure we are about the signature_style value.
#
# Default: 0.6 (reasonable guess for AI-assigned styles)
# Override with specific values based on Session 86 analysis:
#   0.9 = Very confident (iconic/well-documented signature style)
#   0.7 = Fairly confident (good public documentation)
#   0.5 = Default/moderate uncertainty
#   0.3 = Genuinely uncertain (international artists, limited examples)
#
# When Mike verifies/corrects a style via the admin UI, it becomes
# style_source='admin', style_confidence=1.0 (ground truth).
#
# IMPORTANT: Sonnet was wrong on ~1/3 of original 43 styles. These
# confidence scores reflect Claude's honest uncertainty, NOT Sonnet's
# original assignments. Low confidence = "don't trust this for matching."
# ---------------------------------------------------------------------------
STYLE_CONFIDENCE = {
    # === 0.9: ICONIC / WELL-DOCUMENTED (no doubt) ===
    "Todd McFarlane": 0.9,      # stylized — one of the most famous comic sigs
    "Jim Lee": 0.9,             # stylized — iconic "JL" element
    "Stan Lee": 0.9,            # cursive — literally the most famous comic signature
    "Jack Kirby": 0.9,          # cursive — very well-documented
    "Adam Hughes": 0.9,         # initials — "AH!" is iconic
    "Kevin Eastman": 0.9,       # stylized — turtle sketches are legendary
    "Bill Sienkiewicz": 0.9,    # stylized — one of the most distinctive in comics
    "Skottie Young": 0.9,       # stylized — matches his art perfectly
    "Joe Quesada": 0.9,         # stylized — "JQ" monogram well-known
    "Marc Silvestri": 0.9,      # stylized — lots of convention footage
    "Humberto Ramos": 0.9,      # stylized — angular, distinctive
    "Frank Cho": 0.9,           # print — clean, deliberate, well-known
    "Ed McGuinness": 0.9,       # print — bold, clean
    "Mike Mignola": 0.9,        # print — well-known blocky style
    "Rob Liefeld": 0.9,         # print — well-documented
    "Greg Capullo": 0.9,        # cursive — lots of convention footage
    "Alex Ross": 0.9,           # cursive — well-documented

    # === 0.7: FAIRLY CONFIDENT (good public documentation) ===
    "Frank Miller": 0.7,        # stylized — pretty sure but varies over decades
    "Neal Adams": 0.7,          # cursive — well-known but deceased, less recent ref
    "John Byrne": 0.7,          # print — fairly well-documented
    "Steve Ditko": 0.7,         # print — limited examples but consistent
    "George Perez": 0.7,        # cursive — well-documented
    "Art Adams": 0.7,           # cursive — good convention presence
    "J. Scott Campbell": 0.7,   # cursive — lots of con footage
    "Walt Simonson": 0.7,       # cursive — "WS" monogram well-known
    "David Finch": 0.7,         # cursive — active convention signer
    "Erik Larsen": 0.7,         # cursive — Image co-founder, well-documented
    "Robert Kirkman": 0.7,      # cursive — Walking Dead signings well-documented
    "Mark Waid": 0.7,           # cursive — lots of public signings
    "Larry Hama": 0.7,          # cursive — one of the most prolific con signers
    "Darwyn Cooke": 0.7,        # stylized — retro style well-known
    "Jim Steranko": 0.7,        # stylized — artistic reputation matches
    "Bill Finger": 0.7,         # cursive — Golden Age, limited but consistent
    "Bob Kane": 0.7,            # print — well-documented historical
    "Brian Michael Bendis": 0.7, # stylized — enough public examples
    "Garth Ennis": 0.7,         # cursive — good UK convention presence
    "Mark Brooks": 0.7,         # cursive — active modern cover artist
    "Ryan Stegman": 0.7,        # cursive — active Venom-era signer
    "Terry Dodson": 0.7,        # cursive — good convention presence
    "Sean Murphy": 0.7,         # cursive — White Knight signings documented
    "Tim Sale": 0.7,            # cursive — well-known before passing
    "Bernie Wrightson": 0.7,    # cursive — horror conventions well-documented
    "Michael Turner": 0.7,      # cursive — pre-2008 signings documented

    # === 0.5: MODERATE UNCERTAINTY (default for most) ===
    # Creators not listed here get the default 0.6.
    # These are explicitly set to 0.5 because I have specific doubts:
    "Jae Lee": 0.5,             # stylized — fairly confident but limited recent ref
    "Clayton Crain": 0.5,       # stylized — digital painter, could be print
    "Rafael Albuquerque": 0.5,  # stylized — Brazilian, could be cursive
    "Jen Bartel": 0.5,          # stylized — could be cursive with flourishes
    "Mark Bagley": 0.5,         # cursive — probably right but limited verification
    "Ryan Ottley": 0.5,         # cursive — probably right but similar concern
    "Patrick Gleason": 0.5,     # cursive — limited verification
    "Gary Frank": 0.5,          # cursive — limited verification

    # === 0.3: GENUINELY UNCERTAIN (my red-flag list) ===
    "Donny Cates": 0.3,         # assigned 'print' — could easily be cursive or mixed
    "Mitch Gerads": 0.3,        # assigned 'print' — could be cursive
    "Warren Ellis": 0.3,        # assigned 'print' — could be cursive or stylized
    "Olivier Coipel": 0.3,      # assigned 'cursive' — European, could be stylized
    "Esad Ribic": 0.3,          # assigned 'cursive' — Croatian, uncertain
    "Lee Bermejo": 0.3,         # assigned 'stylized' — could be cursive
    "Dan Mora": 0.3,            # assigned 'cursive' — newer intl artist, unverified
    "Jorge Jimenez": 0.3,       # assigned 'cursive' — newer intl artist, unverified
    "Pepe Larraz": 0.3,         # assigned 'cursive' — Spanish, unverified
    "Sara Pichelli": 0.3,       # assigned 'cursive' — Italian, unverified
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

        # Pre-build normalized lookup for fuzzy matching
        normalized_lookup = {}
        for key, val in CREATOR_METADATA.items():
            normalized_lookup[_normalize(key)] = val

        for row in db_creators:
            db_name = row['creator_name']
            creator_id = row['id']

            # 1. Exact match
            meta = CREATOR_METADATA.get(db_name)

            # 2. Case-insensitive match
            if not meta:
                for key, val in CREATOR_METADATA.items():
                    if key.lower() == db_name.lower():
                        meta = val
                        break

            # 3. Accent-normalized match (handles Pérez→Perez, etc.)
            if not meta:
                norm_db = _normalize(db_name)
                meta = normalized_lookup.get(norm_db)

            # 4. Alias table (handles typos like Whilche→Whilce)
            if not meta:
                alias_target = NAME_ALIASES.get(db_name.lower())
                if alias_target:
                    meta = CREATOR_METADATA.get(alias_target)

            if not meta:
                not_found.append(db_name)
                skipped += 1
                continue

            # Look up style confidence (default 0.6 if not in overrides)
            confidence = STYLE_CONFIDENCE.get(db_name, 0.6)
            # Also try the matched key name (for accent-normalized matches)
            if confidence == 0.6:
                for key_name in STYLE_CONFIDENCE:
                    if _normalize(key_name) == _normalize(db_name):
                        confidence = STYLE_CONFIDENCE[key_name]
                        break

            cur.execute("""
                UPDATE creator_signatures
                SET career_start = %s,
                    career_end = %s,
                    publisher_affiliations = %s,
                    signature_style = %s,
                    style_confidence = CASE
                        WHEN style_source = 'admin' THEN style_confidence
                        ELSE %s
                    END,
                    style_source = COALESCE(style_source, 'ai_assigned'),
                    active = true
                WHERE id = %s
            """, [
                meta["career_start"],
                meta["career_end"],
                meta["publishers"],
                meta["style"],
                confidence,
                creator_id,
            ])
            updated += 1
            career = f"{meta['career_start']}-{'present' if meta['career_end'] is None else meta['career_end']}"
            pubs = ', '.join(meta['publishers'])
            conf_label = "★" if confidence >= 0.9 else ("●" if confidence >= 0.7 else ("○" if confidence >= 0.5 else "?"))
            print(f"  Updated: {db_name:30s} | {career:15s} | {pubs:40s} | {meta['style']:9s} | {conf_label} {confidence:.1f}")

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
