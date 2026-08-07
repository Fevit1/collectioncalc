"""Series-type qualifier handling for valuation title matching (Batch 8).

"Giant-Size X-Men #1" is a DIFFERENT book from "X-Men #1". The extractor reads
the qualifier into `issue_type`; the sold corpus stores it inside
`canonical_title` (e.g. 'Giant-Size X-Men', 112 eBay rows). This module:

  - composes the qualified identity the corpus stores a book under, respecting
    qualifier POSITION (Giant-Size/King-Size = prefix; Annual/Special = suffix);
  - builds a qualifier-PRECISE SQL match clause so a qualified query matches
    only its own rows and a plain query does not blend in qualified rows
    — TO THE EXTENT canonical_title is correct. That caveat is load-bearing:
    a row whose canonical_title was TRUNCATED at ingest (stored 'Fantastic
    Four' for a Fantastic Four Annual listing) normalizes equal to the plain
    target and is admitted by exact match. The old qualifier gate never caught
    this either — it was ANDed inside the fallback, and OR short-circuits, so a
    row matched by exact match never reached the gate. Measured 2026-08-07 at
    1,159 rows, 0.56% of the window, Annuals dominating. Logged, not fixed here.

2026-08-07: the gated LIKE fallback was REMOVED. It contributed 39.9% of all
matched rows and 74% of those were a different book; its honest yield was 1.1%
of matched rows. See the block in qualifier_title_clause() for the measurement
and for why no softened variant replaces it.

Single source of truth shared by /api/sales/valuation and /api/sales/fmv.
No Flask import on purpose — pure functions, unit-testable.
"""
import re

# Qualifiers that sit BEFORE the series name in the canonical title.
_PREFIX_QUALIFIERS = ('giant-size', 'giant size', 'king-size', 'king size')
# Everything else we treat as a qualifier (Annual, Special, Special Edition) is
# a SUFFIX. 'Regular' and '' mean NO qualifier.

# Normalized tokens that mark a corpus title as carrying SOME qualifier — used
# to exclude qualified rows from a plain query. (Coarse on purpose; a base-title
# LIKE only ever sees rows already sharing the base name.)
_QUALIFIER_REGEX = r'(giant size|king size|annual|special)'


def _norm(s):
    """Lowercase, hyphens->spaces, collapse whitespace, strip a leading 'the '.
    Mirrors _norm_sql() so a Python-built term and a SQL-normalized column compare
    identically. Fix A (2026-06-27): the leading article 'the ' is stripped on BOTH
    sides (query + canonical_title) so 'The Amazing Spider-Man' unifies with the
    corpus 'Amazing Spider-Man' (was a normalized-exact-match miss → 0 comps →
    key-blind estimate). Corpus-proven ZERO false merges across 14,033 titles;
    'a'/'an' deliberately NOT stripped (no rescue value, nonzero collision risk)."""
    n = re.sub(r'\s+', ' ', (s or '').replace('-', ' ')).strip().lower()
    return re.sub(r'^the ', '', n)


def has_qualifier(issue_type):
    it = (issue_type or '').strip().lower()
    return bool(it) and it != 'regular'


def compose_qualified_title(title, issue_type):
    """The identity a qualified book is stored under. Giant-Size/King-Size are
    PREFIXES ('Giant-Size X-Men'); Annual/Special are SUFFIXES ('Star Wars
    Annual'). No qualifier -> bare title."""
    title = (title or '').strip()
    it = (issue_type or '').strip()
    if not has_qualifier(it):
        return title
    if it.lower() in _PREFIX_QUALIFIERS:
        return f"{it} {title}".strip()
    return f"{title} {it}".strip()


def _norm_sql(col):
    """SQL expression normalizing a column the same way _norm() does — INCLUDING the
    leading-'the ' strip (Fix A; must stay in lockstep with _norm). COALESCE to ''
    so a NULL/empty column yields '' (false in ~/LIKE/= tests) instead of NULL —
    otherwise NULL three-valued logic silently drops rows with no canonical title
    from the plain-query gate."""
    base = r"regexp_replace(btrim(replace(lower(coalesce(%s,'')), '-', ' ')), '\s+', ' ', 'g')" % col
    return r"regexp_replace(%s, '^the ', '')" % base


def qualifier_title_clause(exact_col, like_cols, title, issue_type):
    """Return (sql_fragment, params) for a qualifier-precise title match.

    exact_col: clean canonical column (e.g. 'canonical_title'), tested for exact
               normalized equality vs the COMPOSED identity.
    like_cols: RETAINED FOR DOCUMENTATION ONLY, and deliberately UNUSED since
               2026-08-07. It records which columns the removed LIKE fallback
               used to search, so the pending canonical_title repair unit has
               the list. Passing it changes nothing.

    Placeholder contract: the returned SQL contains EXACTLY ONE %s and params is
    a ONE-element list, on every path, qualified or plain. (Before 2026-08-07 it
    was one per like_col plus one gate term per column, and varied by whether
    issue_type carried a qualifier. Callers that built params positionally
    against that old shape must be re-checked, though none did.)
    """
    composed = compose_qualified_title(title, issue_type)
    qnorm = _norm(composed)
    base_norm = _norm(title)
    all_cols = [exact_col] + list(like_cols)
    params = []

    # 1) precise exact match on the normalized canonical title
    exact = f"{_norm_sql(exact_col)} = %s"
    params.append(qnorm)

    # 2) THE BASE-TITLE LIKE FALLBACK (branch B) WAS REMOVED 2026-08-07.
    #
    # It was `(norm(like_col) LIKE %base%) AND <qualifier gate>`, justified as a
    # rescue for rows with an unclean canonical_title. Measured on the live
    # corpus (800 cells, 35,060 matched rows) it was not doing that job:
    #
    #     branch B rows        14,001   39.9% of all matched rows
    #       FOREIGN book       10,365   74.0% of branch B
    #       AMBIG sub-series    3,238   23.1%
    #       LEGIT rescue          398    2.8%  = 1.1% of all matched rows
    #
    # The LIKE has no word boundary, so target 'Ms' matched canonical
    # 'doomsday clock' through doo-MS-day, and 'R-Man' matched 'Amazing
    # Spider-Man' through spide-R-MAN. Worst live case: Wolverine #181 drew
    # 213 graded comps, ALL of them Incredible Hulk #181 (the first Wolverine
    # APPEARANCE, whose listings say "Wolverine"), and returned $6,735.00 with
    # fmv_method='exact' and verdict_reliable=TRUE. Contamination at that
    # volume defeats every downstream gate, because the gates count comps and
    # the comps are real sales of the wrong book.
    #
    # Cost, measured against 594 real lookups in lookup_demand: 40 move from a
    # number to no-data, and 36 of those 40 were assembling a valuation
    # entirely from foreign books. Exactly ONE cell loses a confident verdict,
    # and that cell is Wolverine #181. Not one of the 27 books in the capture
    # schedule's §2A/§2B/§2C key lists is branch-B dependent.
    #
    # ⚠️ DO NOT REINTRODUCE A SOFTENED VARIANT. Word-boundary matching removes
    # only 12.7% of the contamination while losing 18.1% of the legitimate
    # yield; prefix-anchoring removes 95.2% but loses 83.9%. No matcher-side
    # predicate separates the two populations. The 398 legitimate rows are ALL
    # canonical_title data-quality gaps (cosmetic 197, possessive/plural 77,
    # NULL canonical 58, truncated 66) and are recoverable upstream by
    # repairing canonical_title, not here. That is logged, not done.
    #
    # `like_cols` is retained in the signature so the four call sites keep
    # documenting which columns USED to be searched, and so a future
    # normalizer-repair unit has the list. It is deliberately unused.
    #
    # The qualifier gate went with it: the gate only ever guarded the fallback.
    # Exact match was never gated and does not need to be — a plain target
    # cannot equal 'Giant-Size X-Men' by normalized equality.
    _ = (base_norm, all_cols, like_cols, has_qualifier, _QUALIFIER_REGEX)

    return f"({exact})", params
