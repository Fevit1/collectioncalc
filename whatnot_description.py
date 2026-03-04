"""
Whatnot Content Generator for Slab Worthy
Generates listing content and show prep notes optimized for Whatnot live auctions.
"""

import os
import anthropic


def generate_whatnot_content(title, issue, grade, price,
                             publisher=None, year=None) -> dict:
    """
    Generate Whatnot-optimized listing content and live show talking points.

    Args:
        title: Comic book title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "300")
        grade: Comic grade (NM, VF, FN, etc.)
        price: Fair market value in USD
        publisher: Publisher name (optional)
        year: Publication year (optional)

    Returns:
        Dict with 'success', 'listing_title', 'description', 'show_notes',
        'suggested_start', 'suggested_buy_now'
    """
    # Pricing suggestions
    fmv = float(price) if price else 9.99
    suggested_start = 0.99  # Whatnot convention: low starts drive engagement
    suggested_buy_now = round(fmv, 2)

    # Build listing title (Whatnot titles are shorter, punchier)
    grade_str = str(grade).strip() if grade else ''
    listing_title = f"{title} #{issue}"
    if grade_str:
        listing_title += f" {grade_str}"
    listing_title = listing_title[:80]

    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        return {
            'success': True,
            'listing_title': listing_title,
            'description': _fallback_description(title, issue, grade_str),
            'show_notes': _fallback_show_notes(title, issue, grade_str, fmv, publisher, year),
            'suggested_start': suggested_start,
            'suggested_buy_now': suggested_buy_now,
            'source': 'template'
        }

    try:
        client = anthropic.Anthropic(api_key=api_key)

        comic_info = f"{title} #{issue}"
        if publisher:
            comic_info += f" ({publisher})"
        if year:
            comic_info += f" - {year}"

        prompt = f"""Generate TWO pieces of content for a Whatnot live auction listing for this comic book.

Comic: {comic_info}
Grade: {grade_str or 'Unknown'}
FMV: ${fmv:.2f}

PIECE 1 — LISTING DESCRIPTION (target 100-150 characters):
Short, punchy description for the Whatnot listing card. Energy and hype appropriate for live auctions.
Include: KEY ISSUE status if applicable, era, why it's collectible.
Exclude: grade, price, title (shown separately), shipping info.
Plain text only, no HTML.

PIECE 2 — SHOW PREP NOTES (target 200-300 characters):
Talking points the seller can reference during their live stream. Written as bullet-style notes.
Include:
- What makes this comic special (first appearance, key creator, major event)
- Recent sales context ("Recent sales in this grade range: $X-$Y")
- One-liner hook to hype bidders
Format as short lines separated by newlines, starting with "•"

Respond in this exact format:
DESCRIPTION: [your description]
SHOW_NOTES:
[your show notes]"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()

        # Parse the two pieces
        description = ''
        show_notes = ''

        if 'DESCRIPTION:' in text and 'SHOW_NOTES:' in text:
            parts = text.split('SHOW_NOTES:')
            description = parts[0].replace('DESCRIPTION:', '').strip()
            show_notes = parts[1].strip() if len(parts) > 1 else ''
        else:
            # Fallback: use whole response as description
            description = text[:150]
            show_notes = _fallback_show_notes(title, issue, grade_str, fmv, publisher, year)

        # Clean up description
        if len(description) > 200:
            description = description[:197] + "..."

        return {
            'success': True,
            'listing_title': listing_title,
            'description': description,
            'show_notes': show_notes,
            'suggested_start': suggested_start,
            'suggested_buy_now': suggested_buy_now,
            'source': 'ai'
        }

    except Exception as e:
        print(f"Whatnot AI content generation failed: {e}")
        return {
            'success': True,
            'listing_title': listing_title,
            'description': _fallback_description(title, issue, grade_str),
            'show_notes': _fallback_show_notes(title, issue, grade_str, fmv, publisher, year),
            'suggested_start': suggested_start,
            'suggested_buy_now': suggested_buy_now,
            'source': 'template',
            'ai_error': str(e)
        }


def _fallback_description(title, issue, grade):
    """Basic template description when AI is unavailable."""
    parts = [f"{title} #{issue}"]
    if grade:
        parts.append(f"in {grade} condition")
    parts.append("— a great pickup for any collection!")
    return " ".join(parts)


def _fallback_show_notes(title, issue, grade, fmv, publisher=None, year=None):
    """Basic show notes template when AI is unavailable."""
    notes = []
    notes.append(f"• {title} #{issue}")
    if publisher and year:
        notes.append(f"• {publisher}, {year}")
    elif publisher:
        notes.append(f"• {publisher}")
    if grade:
        notes.append(f"• Graded {grade} by Slab Worthy AI")
    if fmv and fmv > 0:
        notes.append(f"• FMV: ${fmv:.2f} based on recent sales data")
    notes.append("• Low start — let the bidders decide the price!")
    return "\n".join(notes)
