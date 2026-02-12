"""
Title Normalizer for eBay Comic Sales
Parses messy seller titles into structured data.

Philosophy: Never throw away data. Extract what we can confidently identify,
preserve everything else in title_notes.

Usage:
    from title_normalizer import normalize_title
    result = normalize_title("CGC SS 9.8~Department of Truth #0~SIGNED James Tynion")

Returns dict with:
    canonical_title, issue_number, grade_from_title, grading_company,
    is_facsimile, is_reprint, is_variant, is_signed, is_lot, is_key_issue,
    key_issue_claim, creators, title_notes
"""

import re
import json
import os
from rapidfuzz import fuzz, process

# Load known titles, creators, and title mappings
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWN_TITLES = []
KNOWN_CREATORS = []
TITLE_MAPPINGS = {}

try:
    with open(os.path.join(SCRIPT_DIR, 'known_titles.json'), 'r') as f:
        KNOWN_TITLES = json.load(f)
except FileNotFoundError:
    print("Warning: known_titles.json not found. Fuzzy matching disabled.")

try:
    with open(os.path.join(SCRIPT_DIR, 'known_creators.json'), 'r') as f:
        KNOWN_CREATORS = json.load(f)
except FileNotFoundError:
    print("Warning: known_creators.json not found. Creator extraction disabled.")

try:
    with open(os.path.join(SCRIPT_DIR, 'title_mappings.json'), 'r') as f:
        TITLE_MAPPINGS = json.load(f)
except FileNotFoundError:
    print("Warning: title_mappings.json not found. Title normalization disabled.")


def normalize_title(raw_title):
    """
    Parse a raw eBay comic listing title into structured fields.
    Returns dict with normalized fields. Never modifies or discards the raw_title.
    """
    if not raw_title:
        return _empty_result()

    title = raw_title.strip()
    notes = []

    # ── Pre-processing: normalize separators to spaces ────────────
    # Replace ~ and | with space (common eBay separators)
    # But preserve hyphens in words like "Spider-Man"
    working = re.sub(r'[~|]+', ' ', title)
    working = re.sub(r'\s+', ' ', working).strip()

    # ── Step 1: Extract grading info ──────────────────────────────
    grade_from_title = None
    grading_company = None
    is_signed = False

    # CGC/CBCS/PGX with optional SS and grade
    grade_pattern = re.compile(
        r'\b(CGC|CBCS|PGX)\s*(SS)?\s*(\d+\.?\d?)\b',
        re.IGNORECASE
    )
    grade_match = grade_pattern.search(working)
    if grade_match:
        grading_company = grade_match.group(1).upper()
        if grade_match.group(2):
            is_signed = True
            notes.append('Signature Series')
        grade_from_title = float(grade_match.group(3))
        working = working[:grade_match.start()] + working[grade_match.end():]

    # Standalone condition grades (NM, VF/NM, etc.)
    if not grade_from_title:
        condition_grades = {
            'nm+': 9.6, 'nm': 9.4, 'nm-': 9.2, 'nm/mt': 9.6,
            'vf/nm': 9.0, 'vf+': 8.5, 'vf': 8.0, 'vf-': 7.5,
            'fn/vf': 7.0, 'fn+': 6.5, 'fn': 6.0, 'fn-': 5.5,
            'vg/fn': 5.0, 'vg+': 4.5, 'vg': 4.0, 'vg-': 3.5,
            'gd/vg': 3.0, 'gd+': 2.5, 'gd': 2.0, 'gd-': 1.8,
            'fr/gd': 1.5, 'fr': 1.0, 'pr': 0.5
        }
        cond_pattern = re.compile(
            r'\b(NM\+|NM-|NM/MT|NM|VF/NM|VF\+|VF-|VF|FN/VF|FN\+|FN-|FN|'
            r'VG/FN|VG\+|VG-|VG|GD/VG|GD\+|GD-|GD|FR/GD|FR|PR)\b'
            r'(?:\s*condition)?',
            re.IGNORECASE
        )
        cond_match = cond_pattern.search(working)
        if cond_match:
            grade_key = cond_match.group(1).lower().replace(' ', '')
            grade_from_title = condition_grades.get(grade_key)
            if grade_from_title:
                notes.append(f'Condition: {cond_match.group(1).upper()}')
                working = working[:cond_match.start()] + working[cond_match.end():]

    # ── Step 2: Detect signed ─────────────────────────────────────
    signed_pattern = re.compile(
        r'\b(\d+X\s+)?SIGNED\b',
        re.IGNORECASE
    )
    signed_match = signed_pattern.search(working)
    if signed_match:
        is_signed = True
        # Capture signer names after SIGNED (up to next keyword or end)
        after = working[signed_match.end():].strip()
        # Signer names: capitalized words joined by + or &
        signer_match = re.match(
            r'^[\s,]*([A-Za-z][A-Za-z\']+(?:\s*[\+&,]\s*[A-Za-z][A-Za-z\']+)*'
            r'(?:\s+[A-Za-z][A-Za-z\']+)*)',
            after
        )
        if signer_match:
            signer_text = signer_match.group(1).strip()
            # Don't capture common keywords as signer names
            stop_words = {'cgc', 'cbcs', 'pgx', 'marvel', 'dc', 'image', 'comic', 'comics',
                         'variant', 'cover', 'edition', 'print', 'printing', 'rare'}
            signer_words = signer_text.split()
            if signer_words and signer_words[0].lower() not in stop_words:
                notes.append(f'Signed: {signer_text}')
                working = working[:signed_match.start()] + working[signed_match.end() + len(signer_match.group(0)):]
            else:
                notes.append('Signed')
                working = working[:signed_match.start()] + working[signed_match.end():]
        else:
            notes.append('Signed')
            working = working[:signed_match.start()] + working[signed_match.end():]

    # Also catch "Signature" / "Autographed" / "Red Signature" etc.
    sig_pattern2 = re.compile(r'\b(Red\s+)?Signature\b|\bAutographed\b', re.IGNORECASE)
    sig_match2 = sig_pattern2.search(working)
    if sig_match2:
        is_signed = True
        notes.append(f'Signed: {sig_match2.group(0).strip()}')
        working = working[:sig_match2.start()] + working[sig_match2.end():]

    # ── Step 2a: Extract creator names ────────────────────────────
    creators = []
    if KNOWN_CREATORS:
        for creator in KNOWN_CREATORS:
            # Match creator name as whole words
            creator_pattern = re.compile(r'\b' + re.escape(creator) + r'\b', re.IGNORECASE)
            creator_match = creator_pattern.search(working)
            if creator_match:
                # Avoid duplicates (handle variations like "Brian Bendis" vs "Brian Michael Bendis")
                creator_found = creator_match.group(0)
                if creator_found not in creators:
                    creators.append(creator_found)
                # Remove from working string
                working = working[:creator_match.start()] + working[creator_match.end():]

    # Clean up extracted creators list
    creators_str = None
    if creators:
        creators_str = ', '.join(creators)
        notes.append(f'Creators: {creators_str}')

    # ── Step 3: Detect lot/bundle ─────────────────────────────────
    is_lot = False
    lot_pattern = re.compile(
        r'\b(lot\s+of\s+\d+|bundle\s+of\s+\d+|set\s+of\s+\d+|'
        r'\d+\s+comic\s+lot|comic\s+lot|book\s+lot|'
        r'multilist|sold\s+separately)\b',
        re.IGNORECASE
    )
    lot_match = lot_pattern.search(working)
    if lot_match:
        is_lot = True
        notes.append(f'Lot: {lot_match.group(0).strip()}')
        working = working[:lot_match.start()] + working[lot_match.end():]

    # ── Step 4: Detect facsimile ──────────────────────────────────
    is_facsimile = False
    facs_pattern = re.compile(r'\bfacsimile\s*(edition)?\b', re.IGNORECASE)
    facs_match = facs_pattern.search(working)
    if facs_match:
        is_facsimile = True
        notes.append('Facsimile')
        working = working[:facs_match.start()] + working[facs_match.end():]

    # ── Step 5: Detect reprint ────────────────────────────────────
    is_reprint = False
    # Match 2nd, 3rd, 4th+ printings - but NOT 1st printing (that's original)
    reprint_pattern = re.compile(
        r'\b(reprint|'
        r'(?:2nd|second|3rd|third|4th|fourth|5th|fifth|6th|7th|8th|9th|\d{2,}(?:st|nd|rd|th))\s+print(?:ing)?)\b',
        re.IGNORECASE
    )
    reprint_match = reprint_pattern.search(working)
    if reprint_match:
        is_reprint = True
        notes.append(f'Reprint: {reprint_match.group(0).strip()}')
        working = working[:reprint_match.start()] + working[reprint_match.end():]

    # ── Step 5a: Detect key issue claims ──────────────────────────
    is_key_issue = False
    key_issue_claim = None

    # Key issue patterns with context capture
    key_patterns = [
        r'\bkey\s+issue\b',
        r'\b(1st|first)\s+(full\s+)?appearance\s+(?:of\s+)?([A-Za-z\s]+?)(?:\s+\d{4}|\s+Marvel|\s+DC|\s+Image|$)',
        r'\b(1st|first)\s+cameo\s+(?:of\s+)?([A-Za-z\s]+?)(?:\s+\d{4}|\s+Marvel|\s+DC|\s+Image|$)',
        r'\borigin\s+(?:of\s+|story\s+)?([A-Za-z\s]+?)(?:\s+\d{4}|\s+Marvel|\s+DC|\s+Image|$)',
        r'\bdeath\s+of\s+([A-Za-z\s]+?)(?:\s+\d{4}|\s+Marvel|\s+DC|\s+Image|$)',
        r'\bdebut\s+(?:of\s+)?([A-Za-z\s]+?)(?:\s+\d{4}|\s+Marvel|\s+DC|\s+Image|$)',
        r'\bkey\s+collector\b',
    ]

    for pattern in key_patterns:
        key_match = re.search(pattern, working, re.IGNORECASE)
        if key_match:
            is_key_issue = True
            # Capture the full match as the claim
            claim_text = key_match.group(0).strip()
            if not key_issue_claim:
                key_issue_claim = claim_text
            else:
                key_issue_claim += f'; {claim_text}'
            notes.append(f'Key: {claim_text}')
            working = working[:key_match.start()] + working[key_match.end():]
            break  # Only capture first key issue mention

    # ── Step 6: Detect variant info (capture full match) ──────────
    is_variant = False
    variant_details = []

    variant_patterns = [
        (r'\b(35|30)\s*[¢c]\s*(price\s*)?variant\b', None),
        (r'\b(\d+:\d+)\s*(ratio\s*)?(variant|incentive)?\b', None),
        (r'\bvirgin\s*(cover)?\b', 'Virgin'),
        (r'\bNYCC\s*(variant|exclusive)?\b', 'NYCC'),
        (r'\bSDCC\s*(variant|exclusive)?\b', 'SDCC'),
        (r'\bECCC\s*(variant|exclusive)?\b', 'ECCC'),
        (r'\bC2E2\s*(variant|exclusive)?\b', 'C2E2'),
        (r'\bnewsstand\s*(edition)?\b', 'Newsstand'),
        (r'\bdirect\s*(edition)?\b', 'Direct Edition'),
        (r'\b(?:cover|cvr)\s+([A-Z])\b', None),  # Cover A, CVR B
        (r'\bvariant\s*(cover)?\b', 'Variant'),
        (r'\bexclusive\b', 'Exclusive'),
        (r'\bincentive\b', 'Incentive'),
        (r'\bfoil\s*(cover)?\b', 'Foil'),
        (r'\bholographic\b', 'Holographic'),
        (r'\bchromic?um\b', 'Chromium'),
        (r'\bglow[\s-]*in[\s-]*the[\s-]*dark\b', 'Glow in the Dark'),
        (r'\blenticular\b', 'Lenticular'),
        (r'\bsketch\s*(cover)?\b', 'Sketch'),
        (r'\bblank\s*(cover)?\b', 'Blank Cover'),
        (r'\bhomage\b', 'Homage'),
        (r'\bwrap[\s-]*around\s*(cover)?\b', 'Wraparound'),
        (r'\btrade\s*dress\b', 'Trade Dress'),
    ]

    for pattern, label in variant_patterns:
        match = re.search(pattern, working, re.IGNORECASE)
        if match:
            is_variant = True
            detail = label if label else match.group(0).strip()
            variant_details.append(detail)
            working = working[:match.start()] + working[match.end():]

    if variant_details:
        notes.append(f'Variant: {", ".join(variant_details)}')

    # ── Step 7: Strip common eBay prefixes ────────────────────────
    # Remove common listing prefixes that appear at the start
    prefix_patterns = [
        r'^(pre[-\s]*sale|presale)\b',
        r'^(sold\s*out|soldout)\b',
        r'^(new|brand\s*new)\b',
        r'^(hot|rare|htf|hard\s*to\s*find)\b',
        r'^(l@@k|look|wow)\b',
        r'^(nr|no\s*reserve)\b',
        r'^(vintage|retro)\b',
        r'^(free\s*ship(?:ping)?|fast\s*ship(?:ping)?|ships?\s*fast)\b',
        r'^(mint|nm|vf|fn)\b',  # Condition prefixes
    ]

    for prefix_pattern in prefix_patterns:
        prefix_match = re.search(prefix_pattern, working, re.IGNORECASE)
        if prefix_match:
            prefix_text = prefix_match.group(0).strip()
            notes.append(f'Prefix: {prefix_text}')
            working = working[prefix_match.end():].strip()
            break  # Only remove first prefix

    # ── Step 8: Remove publisher names ────────────────────────────
    # BUT: Don't strip if publisher name is part of the actual comic title
    # (e.g., "DC Comics Presents", "Marvel Comics Presents")
    publisher = None
    publishers = [
        ('Marvel Comics', 'Marvel'), ('Marvel', 'Marvel'),
        ('DC Comics', 'DC'), ('DC', 'DC'),
        ('EC Comics', 'EC'), ('EC', 'EC'),
        ('Gladstone', 'Gladstone'),
        ('Image Comics', 'Image'), ('Image', 'Image'),
        ('Dark Horse Comics', 'Dark Horse'), ('Dark Horse', 'Dark Horse'),
        ('IDW Publishing', 'IDW'), ('IDW', 'IDW'),
        ('Valiant', 'Valiant'), ('Boom! Studios', 'Boom'),
        ('Boom Studios', 'Boom'), ('BOOM!', 'Boom'),
        ('Dynamite', 'Dynamite'), ('Dynamite Entertainment', 'Dynamite'),
        ('Oni Press', 'Oni Press'), ('AfterShock', 'AfterShock'),
        ('AWA', 'AWA'), ('Scout Comics', 'Scout'),
        ('Titan Comics', 'Titan'), ('Zenescope', 'Zenescope'),
        ('Abstract Studio', 'Abstract Studio'),
    ]

    # Strip publisher names, but check each one individually to avoid breaking titles
    for pub_name, pub_short in publishers:
        pub_pattern = re.compile(r'\b' + re.escape(pub_name) + r'\b', re.IGNORECASE)
        pub_match = pub_pattern.search(working)
        if pub_match:
            # Check if this publisher is part of the actual comic title
            # Strategy: If publisher is part of a known title (e.g., "DC Comics Presents"), don't strip it
            skip_this_publisher = False
            if KNOWN_TITLES:
                for known_title in KNOWN_TITLES:
                    # If the known title contains this publisher name (e.g., "DC Comics Presents" contains "DC Comics")
                    # AND working starts with that known title, then this publisher is part of the title
                    if pub_name.lower() in known_title.lower():
                        # Check if working starts with this known title
                        if working.lower().strip().startswith(known_title.lower()):
                            skip_this_publisher = True
                            break

            if not skip_this_publisher:
                if not publisher:
                    publisher = pub_short
                working = working[:pub_match.start()] + working[pub_match.end():]
                # Don't break - continue checking for other publishers

    # ── Step 9: Remove filler words and noise ─────────────────────
    filler_patterns = [
        r'\bcomic\s*books?\b',
        r'\bissues?\b',  # "Issues" or "Issue" standalone
        r'\bTPB\b',
        r'\btrade\s+paperback\b',
        r'\bgraphic\s+novels?\b',
        r'\bhigh\s+grade\b',
        r'\blow\s+grade\b',
        r'\bmixed\s+grades?\b',
        r'\bvarious\s+grades?\b',
        r'\bread\s+desc(?:ription)?\b',
        r'\bsee\s+desc(?:ription)?\b',
        r'\bcheck\s+desc(?:ription)?\b',
        r'\bplease\s+read\b',
        r'\bsee\s+pics?\b',
        r'\bcheck\s+pics?\b',
        r'\breprints?\b',  # "Reprints" or "Gladstone reprints"
        r'\brare\b',
        r'\bhot\b',
        r'\bwhite\s+pages\b',
        r'\boff[\s-]?white\s+pages\b',
        r'\b(1st|first)\s+print(?:ing)?\b',  # "1st printing" - just noise (original is default)
        r'\bedition\b',
        r'\b\d{4}\b',  # Standalone year
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b',  # Month + year like "July 1990"
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b',  # Full month + year
        r'\b[A-Z]\d{2,3}[-]\d{2,3}\b',  # Inventory codes like X60-164
        r'\bcondition\b',
        r'\bcover\b',  # Standalone "cover" (variants already captured)
        r'\bof\b',  # Standalone "of" left over from "Lot of X"
    ]

    for fp in filler_patterns:
        working = re.sub(fp, ' ', working, flags=re.IGNORECASE)

    # ── Step 10: Extract issue number ──────────────────────────────
    issue_number = None

    # Skip issue extraction if this is a lot/bundle
    if not is_lot:
        # Pattern 1: #123 or #123A (most reliable)
        issue_match = re.search(r'#\s*(\d+[A-Za-z]?)', working)
        if issue_match:
            issue_number = issue_match.group(1)
            working = working[:issue_match.start()] + ' @@ISSUE@@ ' + working[issue_match.end():]
        else:
            # Pattern 2: Title followed by a standalone number at a word boundary
            # "Department of Truth 1", "AMAZING SPIDER-MAN 300"
            # Must be preceded by a letter (part of title) and be 1-4 digits
            issue_match2 = re.search(r'(?<=[A-Za-z])\s+(\d{1,4})\b', working)
            if issue_match2:
                # Make sure it's not a year or part of something else
                num = int(issue_match2.group(1))
                if num < 1000 and num > 0:  # Issue numbers are typically under 1000
                    issue_number = issue_match2.group(1)
                    working = working[:issue_match2.start()] + ' @@ISSUE@@ ' + working[issue_match2.end():]

    # ── Step 11: Split on issue marker — before = title, after = details ─
    if '@@ISSUE@@' in working:
        parts = working.split('@@ISSUE@@', 1)
        title_part = parts[0].strip()
        details_part = parts[1].strip() if len(parts) > 1 else ''
    else:
        # No issue found
        # For lots, try to extract clean title by removing issue lists/ranges
        if is_lot:
            # Remove patterns like: #1-5, #Annual 3, #1,2,3, (Lot of X), Issues 1-6
            cleaned = re.sub(r'#\s*\w+\s+[\d,\s]+', ' ', working)  # #Annual 3, 32, 37
            cleaned = re.sub(r'#\s*[\d,\s\-]+', ' ', cleaned)      # #1-5 or #1,2,3
            cleaned = re.sub(r'\bissues?\s+[\d,\s\-]+', ' ', cleaned, flags=re.IGNORECASE)  # Issues 1-6
            cleaned = re.sub(r'\([^)]*\)', ' ', cleaned)           # (Lot of 6)
            cleaned = re.sub(r'[-]+', ' ', cleaned)                # Remove trailing dashes
            cleaned = re.sub(r'\b\d+\s*$', '', cleaned)            # Remove trailing standalone digits
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            title_part = cleaned
            details_part = ''
        else:
            # Not a lot - take best guess at title
            title_part = working.strip()
            details_part = ''

    # Capture any meaningful details after the issue number
    if details_part:
        # Clean and capture as extra notes
        details_clean = re.sub(r'[()[\],.\-]+', ' ', details_part)
        details_clean = re.sub(r'\s+', ' ', details_clean).strip()
        # Remove trailing single digits (quantity markers)
        details_clean = re.sub(r'\s+\d\s*$', '', details_clean).strip()
        # Remove standalone single letters
        details_clean = re.sub(r'\b[A-Za-z]\b', '', details_clean).strip()
        details_clean = re.sub(r'\s+', ' ', details_clean).strip()
        if details_clean and len(details_clean) > 2:
            notes.append(f'Details: {details_clean}')

    # ── Step 12: Build canonical_title ────────────────────────────
    canonical_title = _build_canonical_title(title_part)

    return {
        'canonical_title': canonical_title,
        'issue_number': issue_number,
        'grade_from_title': grade_from_title,
        'grading_company': grading_company,
        'is_facsimile': is_facsimile,
        'is_reprint': is_reprint,
        'is_variant': is_variant,
        'is_signed': is_signed,
        'is_lot': is_lot,
        'is_key_issue': is_key_issue,
        'key_issue_claim': key_issue_claim,
        'creators': creators_str,
        'publisher': publisher,
        'title_notes': '; '.join(notes) if notes else None
    }


def _build_canonical_title(title_part):
    """
    Clean up the title portion and normalize to title case.
    Preserves hyphens in compound words (Spider-Man, X-Men).
    Uses fuzzy matching against known titles for accuracy.
    """
    if not title_part or len(title_part.strip()) < 2:
        return None

    text = title_part.strip()

    # Remove leading special characters and punctuation
    # BUT preserve apostrophes in words like "D'orc"
    text = re.sub(r'^[\s,.\-:;()\[\]*•~!@#$%^&_+=]+', '', text)  # Leading
    text = re.sub(r'[\s,.\-:;()\[\]]+$', '', text)  # Trailing (no apostrophe here)

    # Remove parenthetical content (usually publisher or notes)
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)  # Also remove [bracketed] content

    # Remove "by [creator]" pattern when creator wasn't already extracted
    text = re.sub(r'\s+by\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', '', text, flags=re.IGNORECASE)

    # Remove "comic" from title (e.g., "Batman Comic" → "Batman")
    text = re.sub(r'\bcomic\b', '', text, flags=re.IGNORECASE)

    # Remove standalone single digits at the end (quantity, not issue)
    text = re.sub(r'\s+\d\s*$', '', text)

    # Remove any remaining standalone single letters (except common ones in titles)
    # Keep: "X" (X-Men), "A" (A-Force), "D'" (D'orc), etc.
    # Don't remove if followed by apostrophe (D'orc) or hyphen (X-Men)
    text = re.sub(r'(?<!\w)\b([B-W])\b(?!\w)(?![-\'])', '', text)

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    if not text or len(text) < 2:
        return None

    # First, check mappings for limited series and variant titles (fuzzy match)
    if TITLE_MAPPINGS:
        for full_title, short_title in TITLE_MAPPINGS.items():
            # Check if the text contains the key parts of the full title
            # Remove "The", "Marvel", "DC" for comparison
            text_clean = text.lower().replace('the ', '').replace('marvel ', '').replace('dc ', '')
            full_clean = full_title.lower().replace('the ', '').replace('marvel ', '').replace('dc ', '')

            if text_clean == full_clean or text.lower() == full_title.lower():
                return short_title

    # Fuzzy match against known titles if available
    if KNOWN_TITLES:
        # Try to find best match using token_sort_ratio (handles word order variations)
        match_result = process.extractOne(
            text,
            KNOWN_TITLES,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=75  # 75% similarity threshold
        )

        if match_result:
            matched_title, score, _ = match_result
            # If we have a strong match (>75%), use the canonical version
            if score >= 75:
                return matched_title

    # No fuzzy match found - fall back to title case normalization
    small_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
                   'at', 'by', 'in', 'of', 'on', 'to', 'up', 'is', 'vs'}

    def capitalize_word(word, is_first):
        """Capitalize a word, handling hyphenated compounds."""
        if '-' in word and not word.startswith('-') and not word.endswith('-'):
            # Hyphenated compound: capitalize each part
            parts = word.split('-')
            return '-'.join(p.capitalize() for p in parts)

        lower = word.lower()

        # Keep common acronyms uppercase
        if lower in ('ii', 'iii', 'iv', 'dc', 'uk', 'usa', 'tmnt', 'gi'):
            return word.upper()

        # Capitalize first word and non-small words
        if is_first or lower not in small_words:
            return word.capitalize()
        return lower

    words = text.split()
    result = [capitalize_word(w, i == 0) for i, w in enumerate(words)]

    return ' '.join(result)


def _empty_result():
    return {
        'canonical_title': None,
        'issue_number': None,
        'grade_from_title': None,
        'grading_company': None,
        'is_facsimile': False,
        'is_reprint': False,
        'is_variant': False,
        'is_signed': False,
        'is_lot': False,
        'is_key_issue': False,
        'key_issue_claim': None,
        'creators': None,
        'publisher': None,
        'title_notes': None
    }


# ── Quick test / demo ─────────────────────────────────────────────
if __name__ == '__main__':
    test_titles = [
        # Real titles from Mike's DB
        "Department Of Truth #10 Cyn City Virgin CGC 9.8 Chinh Potter Red Signature",
        "CGC SS 9.8~Department of Truth #0~Elvis Akira NYCC variant~SIGNED James Tynion",
        "The Department of Truth #6 Cover Variant - B NM condition",
        "Department of Truth 1  Mirka Andolfo 1:50 Ratio Variant Image Comics 2020",
        "DEPARTMENT OF TRUTH #12 CASPER WIJNGAARD | ZOMBIE PIT X 1",
        "Department of Truth #1 | Proof of Concept Exclusive | James Tynion IV | Image",
        "The Department Of Truth #28A CGC 9.4",
        "CGC SS 9.8~The Department of Truth #0~1:10~SIGNED Tynion+Snyder+Simmonds+Hixson",
        "Department of Truth #2 2020 Image Comics High Grade Comic Book X60-164",
        "Image Comics Department of Truth #1 CGC 9.8 Rare Tiny Onion foil Comic",
        "DEPARTMENT OF TRUTH #0 COVER E SIMMONDS 1:50 2X SIGNED TYNION SNYDER CGC SS 9.8",
        "Spider-Gwen: Gwenverse #1 CGC 9.8 Chew Virgin Signed Derrick Chew",
        "BATGIRL #32 DERRICK CHEW 1",
        "Amazing Spider-Man #300 CGC 9.6 White Pages 1st Venom",
        "AMAZING SPIDER-MAN 300 NEWSSTAND EDITION MARVEL",
        "Lot of 5 Spider-Man Comics #1-5 Marvel",
        "Absolute Batman #1 2nd Print Foil Cover DC Comics 2024",
        "TMNT #1 Facsimile Edition CGC 9.8 Kevin Eastman",
    ]

    print("=" * 100)
    print("TITLE NORMALIZER TEST — v2")
    print("=" * 100)

    for raw in test_titles:
        result = normalize_title(raw)
        print(f"\nRAW: {raw}")
        print(f"  canonical_title:  {result['canonical_title']}")
        print(f"  issue_number:     {result['issue_number']}")
        print(f"  grade:            {result['grade_from_title']} ({result['grading_company'] or 'raw'})")

        flags = []
        if result['is_signed']:     flags.append('SIGNED')
        if result['is_variant']:    flags.append('VARIANT')
        if result['is_lot']:        flags.append('LOT')
        if result['is_facsimile']:  flags.append('FACSIMILE')
        if result['is_reprint']:    flags.append('REPRINT')
        print(f"  flags:            {', '.join(flags) if flags else 'none'}")
        print(f"  publisher:        {result['publisher'] or '-'}")
        print(f"  notes:            {result['title_notes'] or '-'}")
