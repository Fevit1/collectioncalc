"""
Whatnot Content Generator for Slab Worthy
Generates listing content and show prep notes optimized for Whatnot live auctions.
"""

import os
import anthropic


def generate_whatnot_content(title, issue, grade, price,
                             publisher=None, year=None,
                             assessment_id=None, registry_serial=None) -> dict:
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
            'show_notes': _append_sw_ids(
                _fallback_show_notes(title, issue, grade_str, fmv, publisher, year),
                assessment_id, registry_serial),
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

        prompt = f"""Generate content for a Whatnot live auction listing for this comic book. Whatnot is a live-streaming marketplace where sellers present items on camera. Content should be energetic and drive bidding.

Comic: {comic_info}
Grade: {grade_str or 'Unknown'}
FMV: ${fmv:.2f}

PIECE 1 — LISTING DESCRIPTION (100-150 characters):
This appears on the listing card in the Whatnot app before the live show starts. Keep it short and punchy.
- Lead with what makes this book special (KEY ISSUE, first appearance, iconic cover, etc.)
- Use language that creates urgency/excitement for collectors
- Do NOT include: grade, price, title (shown separately), shipping info
- Plain text only, no HTML or hashtags

PIECE 2 — SHOW PREP NOTES (200-400 characters):
Talking points the seller reads during their live stream while showing the book on camera. Written as bullet-style notes starting with "•".
Include:
- What makes this comic special (first appearance, key creator run, major storyline event, iconic cover artist)
- Why collectors want this book specifically
- Suggested opening line to hype bidders (e.g., "Alright who needs this for their run...")
- Any notable recent market movement or demand context
Do NOT fabricate specific sales prices — keep market references general (e.g., "hot book right now", "always in demand").

Respond in this exact format:
DESCRIPTION: [your description]
SHOW_NOTES:
[your show notes]"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
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

        # Clean up description (Whatnot listing cards support ~150 chars)
        if len(description) > 250:
            description = description[:247] + "..."

        # Append Slab Worthy IDs to show notes
        show_notes = _append_sw_ids(show_notes, assessment_id, registry_serial)

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
            'show_notes': _append_sw_ids(
                _fallback_show_notes(title, issue, grade_str, fmv, publisher, year),
                assessment_id, registry_serial),
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


def _append_sw_ids(show_notes, assessment_id=None, registry_serial=None):
    """Append Slab Worthy assessment and registry IDs to show notes."""
    if assessment_id:
        show_notes += f"\n• Slab Worthy Assessment #{assessment_id}"
    if registry_serial:
        show_notes += f"\n• Slab Guard Registered: {registry_serial}"
    return show_notes
