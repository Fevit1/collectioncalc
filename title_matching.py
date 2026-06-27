"""Series-type qualifier handling for valuation title matching (Batch 8).

"Giant-Size X-Men #1" is a DIFFERENT book from "X-Men #1". The extractor reads
the qualifier into `issue_type`; the sold corpus stores it inside
`canonical_title` (e.g. 'Giant-Size X-Men', 112 eBay rows). This module:

  - composes the qualified identity the corpus stores a book under, respecting
    qualifier POSITION (Giant-Size/King-Size = prefix; Annual/Special = suffix);
  - builds a qualifier-PRECISE SQL match clause so a qualified query matches
    only its own rows and a plain query never blends in qualified rows — while
    keeping a (gated) LIKE fallback for rows with an unclean canonical_title.

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
    like_cols: columns tested with a qualifier-GATED LIKE on the BASE title
               (fallback for rows whose canonical title is unclean/empty).

    Placeholder order in the returned SQL: exact term, then one per like_col,
    then one gate term per (exact_col + like_cols). params is built in that order.
    """
    composed = compose_qualified_title(title, issue_type)
    qnorm = _norm(composed)
    base_norm = _norm(title)
    all_cols = [exact_col] + list(like_cols)
    params = []

    # 1) precise exact match on the normalized canonical title
    exact = f"{_norm_sql(exact_col)} = %s"
    params.append(qnorm)

    # 2) base-title LIKE across like_cols (the fallback)
    like_param = f"%{base_norm}%"
    like_terms = []
    for col in like_cols:
        like_terms.append(f"{_norm_sql(col)} LIKE %s")
        params.append(like_param)
    like_any = " OR ".join(like_terms)

    # 3) qualifier gate on the fallback so it can't cross qualifier boundaries
    if has_qualifier(issue_type):
        qual_like = f"%{_norm(issue_type)}%"   # qualified: row MUST carry this qualifier
        gate_terms = []
        for col in all_cols:
            gate_terms.append(f"{_norm_sql(col)} LIKE %s")
            params.append(qual_like)
        gate = "(" + " OR ".join(gate_terms) + ")"
    else:
        gate_terms = []                         # plain: row must carry NO qualifier
        for col in all_cols:
            gate_terms.append(f"{_norm_sql(col)} ~ %s")
            params.append(_QUALIFIER_REGEX)
        gate = "NOT (" + " OR ".join(gate_terms) + ")"

    sql = f"({exact} OR (({like_any}) AND {gate}))"
    return sql, params
