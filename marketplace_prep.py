"""
Marketplace Prep Content Generator for Slab Worthy
Generates platform-optimized listing content for multiple selling platforms.
Supports: Whatnot, Mercari, Facebook Marketplace, Heritage Auctions,
ComicConnect, MyComicShop, COMC, Hip Comics
"""

import os
import anthropic
from models import SONNET


# Platform configurations
PLATFORMS = {
    'whatnot': {
        'name': 'Whatnot',
        'color': '#ff6b35',
        'type': 'live_auction',
        'desc_target': '100-150 characters',
        'desc_tone': 'Short, punchy, hype-driven. Energy appropriate for live auctions.',
        'has_show_notes': True,
        'suggested_start': 0.99,
        'start_label': 'Starting Bid',
        'buy_now_label': 'Buy Now',
        'url': 'https://www.whatnot.com',
        'paste_instructions': 'Open Whatnot Seller Dashboard → Create Listing → Paste fields'
    },
    'mercari': {
        'name': 'Mercari',
        'color': '#4dc0e8',
        'type': 'fixed_price',
        'desc_target': '200-300 characters',
        'desc_tone': 'Friendly, conversational. Mercari buyers are casual collectors. Mention condition clearly.',
        'has_show_notes': False,
        'suggested_start': None,
        'start_label': None,
        'buy_now_label': 'Listing Price',
        'url': 'https://www.mercari.com',
        'paste_instructions': 'Open Mercari → Sell → Fill in fields → Upload photos'
    },
    'facebook': {
        'name': 'Facebook Marketplace',
        'color': '#1877f2',
        'type': 'fixed_price',
        'desc_target': '150-250 characters',
        'desc_tone': 'Casual, local-friendly. Mention condition, no shipping needed if local pickup. Include key details since FB buyers may not be comic experts.',
        'has_show_notes': False,
        'suggested_start': None,
        'start_label': None,
        'buy_now_label': 'Listing Price',
        'url': 'https://www.facebook.com/marketplace',
        'paste_instructions': 'Facebook → Marketplace → Create New Listing → Item for Sale'
    },
    'heritage': {
        'name': 'Heritage Auctions',
        'color': '#1a3c6e',
        'type': 'consignment_auction',
        'desc_target': '250-400 characters',
        'desc_tone': 'Professional, detailed, scholarly. Heritage buyers are serious investors. Emphasize provenance, pedigree, historical significance, and census data if known.',
        'has_show_notes': True,
        'suggested_start': None,
        'start_label': 'Estimated Value',
        'buy_now_label': 'Reserve Suggestion',
        'url': 'https://www.ha.com',
        'paste_instructions': 'Submit at HA.com/Consign → Comics & Comic Art → Paste details in consignment form'
    },
    'comicconnect': {
        'name': 'ComicConnect',
        'color': '#cc0000',
        'type': 'consignment_auction',
        'desc_target': '200-350 characters',
        'desc_tone': 'Professional, market-aware. ComicConnect buyers track trends. Reference recent comparable sales and market position.',
        'has_show_notes': True,
        'suggested_start': None,
        'start_label': 'Estimated Value',
        'buy_now_label': 'Reserve Suggestion',
        'url': 'https://www.comicconnect.com',
        'paste_instructions': 'ComicConnect.com → Sell → Submit consignment request with details'
    },
    'mycomicshop': {
        'name': 'MyComicShop',
        'color': '#336699',
        'type': 'fixed_price',
        'desc_target': '150-250 characters',
        'desc_tone': 'Straightforward, collector-focused. MyComicShop buyers know comics. Focus on grade accuracy, notable features (white pages, off-white pages), and variant info.',
        'has_show_notes': False,
        'suggested_start': None,
        'start_label': None,
        'buy_now_label': 'Listing Price',
        'url': 'https://www.mycomicshop.com',
        'paste_instructions': 'MyComicShop.com → Sell → Search for title → Enter details'
    },
    'comc': {
        'name': 'COMC',
        'color': '#e67e22',
        'type': 'consignment',
        'desc_target': '100-200 characters',
        'desc_tone': 'Brief and factual. COMC handles most listing details. Focus on condition notes and any special attributes (signed, variant, first print).',
        'has_show_notes': False,
        'suggested_start': None,
        'start_label': None,
        'buy_now_label': 'Suggested Price',
        'url': 'https://www.comc.com',
        'paste_instructions': 'Ship item to COMC → They scan and list → Set your price online'
    },
    'hipcomic': {
        'name': 'Hip Comics',
        'color': '#8b5cf6',
        'type': 'fixed_price',
        'desc_target': '150-250 characters',
        'desc_tone': 'Collector-to-collector tone. Hip Comics is a niche marketplace. Emphasize key issue status, grade details, and why this book matters.',
        'has_show_notes': False,
        'suggested_start': None,
        'start_label': None,
        'buy_now_label': 'Listing Price',
        'url': 'https://www.hipcomic.com',
        'paste_instructions': 'HipComic.com → Sell Comics → Create listing → Paste details'
    }
}


def get_platform_config(platform_key):
    """Get configuration for a platform. Returns None if not found."""
    return PLATFORMS.get(platform_key)


def get_all_platforms():
    """Return list of all platform configs for frontend dropdown."""
    return {k: {'name': v['name'], 'color': v['color'], 'type': v['type'],
                'has_show_notes': v['has_show_notes'], 'url': v['url'],
                'paste_instructions': v['paste_instructions'],
                'start_label': v['start_label'], 'buy_now_label': v['buy_now_label']}
            for k, v in PLATFORMS.items()}


def generate_platform_content(platform_key, title, issue, grade, price,
                              publisher=None, year=None) -> dict:
    """
    Generate platform-optimized listing content.

    Args:
        platform_key: Platform identifier (e.g., 'whatnot', 'mercari')
        title: Comic book title
        issue: Issue number
        grade: Comic grade
        price: Fair market value in USD
        publisher: Publisher name (optional)
        year: Publication year (optional)

    Returns:
        Dict with success, listing_title, description, show_notes (if applicable),
        pricing suggestions, and platform metadata
    """
    platform = PLATFORMS.get(platform_key)
    if not platform:
        return {'success': False, 'error': f'Unknown platform: {platform_key}'}

    fmv = float(price) if price else 9.99
    grade_str = str(grade).strip() if grade else ''

    # Build listing title
    listing_title = f"{title} #{issue}"
    if grade_str:
        listing_title += f" {grade_str}"
    listing_title = listing_title[:80]

    # Pricing based on platform type
    if platform['suggested_start'] is not None:
        suggested_start = platform['suggested_start']
    elif platform['type'] in ('consignment_auction', 'consignment'):
        suggested_start = round(fmv * 0.8, 2)  # 80% of FMV as estimate
    else:
        suggested_start = None

    suggested_buy_now = round(fmv, 2)

    # Try AI generation
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return _build_response(platform, platform_key, listing_title, grade_str,
                               title, issue, fmv, publisher, year,
                               suggested_start, suggested_buy_now, source='template')

    try:
        client = anthropic.Anthropic(api_key=api_key)

        comic_info = f"{title} #{issue}"
        if publisher:
            comic_info += f" ({publisher})"
        if year:
            comic_info += f" - {year}"

        # Build platform-specific prompt
        show_notes_section = ""
        response_format = "DESCRIPTION: [your description]"

        if platform['has_show_notes']:
            show_notes_section = f"""
PIECE 2 — PREP NOTES (target 200-300 characters):
Talking points for the seller. Written as bullet-style notes starting with "•".
Include:
- What makes this comic special (first appearance, key creator, major event)
- Recent sales context
- One-liner hook
"""
            response_format = """DESCRIPTION: [your description]
SHOW_NOTES:
[your notes]"""

        prompt = f"""Generate listing content for {platform['name']} for this comic book.

Comic: {comic_info}
Grade: {grade_str or 'Unknown'}
FMV: ${fmv:.2f}
Platform type: {platform['type']}

PIECE 1 — LISTING DESCRIPTION (target {platform['desc_target']}):
{platform['desc_tone']}
Include: KEY ISSUE status if applicable, era, why it's collectible.
Exclude: grade, price, title (shown separately), shipping info.
Plain text only, no HTML.
{show_notes_section}
Respond in this exact format:
{response_format}"""

        response = client.messages.create(
            model=SONNET,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()

        # Parse response
        description = ''
        show_notes = ''

        if platform['has_show_notes'] and 'SHOW_NOTES:' in text:
            parts = text.split('SHOW_NOTES:')
            description = parts[0].replace('DESCRIPTION:', '').strip()
            show_notes = parts[1].strip() if len(parts) > 1 else ''
        elif 'DESCRIPTION:' in text:
            description = text.replace('DESCRIPTION:', '').strip()
        else:
            description = text[:300]

        # Enforce max length
        if len(description) > 500:
            description = description[:497] + "..."

        result = {
            'success': True,
            'platform': platform_key,
            'platform_name': platform['name'],
            'listing_title': listing_title,
            'description': description,
            'suggested_start': suggested_start,
            'suggested_buy_now': suggested_buy_now,
            'source': 'ai'
        }
        if platform['has_show_notes']:
            result['show_notes'] = show_notes
        return result

    except Exception as e:
        print(f"{platform['name']} AI content generation failed: {e}")
        return _build_response(platform, platform_key, listing_title, grade_str,
                               title, issue, fmv, publisher, year,
                               suggested_start, suggested_buy_now,
                               source='template', ai_error=str(e))


def _build_response(platform, platform_key, listing_title, grade_str,
                    title, issue, fmv, publisher, year,
                    suggested_start, suggested_buy_now,
                    source='template', ai_error=None):
    """Build a fallback/template response."""
    result = {
        'success': True,
        'platform': platform_key,
        'platform_name': platform['name'],
        'listing_title': listing_title,
        'description': _fallback_description(title, issue, grade_str, platform['name']),
        'suggested_start': suggested_start,
        'suggested_buy_now': suggested_buy_now,
        'source': source
    }
    if platform['has_show_notes']:
        result['show_notes'] = _fallback_show_notes(title, issue, grade_str, fmv, publisher, year)
    if ai_error:
        result['ai_error'] = ai_error
    return result


def _fallback_description(title, issue, grade, platform_name):
    """Basic template description when AI is unavailable."""
    parts = [f"{title} #{issue}"]
    if grade:
        parts.append(f"in {grade} condition")
    parts.append("— a great pickup for any collection!")
    return " ".join(parts)


def _fallback_show_notes(title, issue, grade, fmv, publisher=None, year=None):
    """Basic show/prep notes template when AI is unavailable."""
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
    notes.append("• Great addition to any collection!")
    return "\n".join(notes)
