"""
eBay Description Generator for Slab Worthy
Generates professional, eBay-compliant descriptions for comic book listings.
"""

import os
import anthropic
from models import SONNET

# eBay description constraints
MAX_DESCRIPTION_LENGTH = 4000
# Only match standalone bad words, not parts of names like "Cassidy" or "classic"
BANNED_WORDS_PATTERN = r'\b(fuck|shit|damn|bitch|crap)\b'

# The valuation's "more than one edition shares this name, and no year was given"
# basis (routes/sales_valuation.py verdict_basis). A description written for
# that report must not pick an edition the report itself declined to pick.
EDITION_UNRESOLVED = 'multi_edition'


def _build_prompt(title, issue, publisher=None, year=None, verdict_basis=None) -> str:
    """The AI prompt. Separated from the API call so it can be read without one.

    2026-09-17: the prompt used to omit the year entirely and ask for era, first
    appearance and KEY ISSUE status -- so "X-Men #1" got the 1963 book's copy
    whether the seller's copy was 1963, 1991 or unknown, and a report whose
    valuation was WITHHELD for lack of a year still shipped "Silver Age. KEY
    ISSUE: first appearance of..." onto a public listing. Now: a known year names
    the edition to describe; an unresolved edition forbids edition claims.
    """
    comic_info = f"{title} #{issue}"
    if publisher:
        comic_info += f" ({publisher})"
    if year:
        comic_info += f" - {year}"
    unresolved = (verdict_basis == EDITION_UNRESOLVED)
    if unresolved:
        edition_rules = """EDITION NOT ESTABLISHED. More than one edition shares this title and issue number, and the seller has NOT said which this copy is (no publication year was given). So:
- Do NOT name an era (Golden/Silver/Bronze/Copper/Modern Age)
- Do NOT claim a first appearance, origin, death, major event, or KEY ISSUE status
- Do NOT name a publication year, or the writer or artist of any one edition
Describe only what is true of the title itself: the characters it features and why collectors follow the series."""
        include = """Include ONLY:
- The characters and series the book belongs to
- Why the title is collected (1-2 short phrases), without tying it to one edition"""
        example = """Example (232 characters):
"Gotham's Dark Knight in one of the most-collected numbers in the title, with Robin and the rogues gallery that made the series. A cornerstone issue number for Batman collectors, sought after in every printing that carries it.\""""
    else:
        edition_rules = (f"The publication year is {year}: describe THAT edition, not another printing that shares the number."
                         if year else "No publication year was given: if this title has more than one edition, keep era and first-appearance claims general.")
        include = """Include ONLY:
- Era (Golden/Silver/Bronze/Copper/Modern Age)
- KEY ISSUE status if applicable (first appearance, origin, death, major event) - call this out explicitly
- Key characters introduced or featured
- Creators (writer/artist) if notable
- Why it's collectible (1-2 short phrases)"""
        example = """Example (238 characters):
"Copper Age. KEY ISSUE: First full appearance of Blue Devil (Dan Cassidy). The definitive origin story. Created by Dan Mishkin, Gary Cohn, and Paris Cullins. Essential for Bronze Age DC collectors and fans of supernatural superhero comics.\""""
    return f"""Generate an eBay listing description for this comic book.

Comic: {comic_info}
{edition_rules}

TARGET: Exactly 235-245 characters. A verification URL (~55 chars) will be appended, bringing total to ~300 characters for optimal eBay mobile display.

{example}

{include}

Do NOT include:
- Title, publisher, or year (already shown in eBay listing fields)
- Grade or condition (shown separately on eBay)
- "Please review photos" or similar (seller policies cover this)
- Shipping or packaging info
- CollectionCalc or AI mentions
- HTML tags - plain text only

Generate only the description, nothing else."""


def generate_description(title, issue, grade, price,
                         publisher=None, year=None, verdict_basis=None) -> dict:
    """
    Generate a professional eBay-ready description for a comic book listing.

    Args:
        title: Comic book title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "300")
        grade: Comic grade (NM, VF, FN, etc.)
        price: Listing price in USD
        publisher: Publisher name (optional)
        year: Publication year (optional)
        verdict_basis: the saved report's valuation basis; 'multi_edition' means
            the edition is not established and the prompt forbids edition claims
    
    Returns:
        Dict with 'success', 'description', and optional 'error'
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        # Fallback to template-based description
        return {
            'success': True,
            'description': _generate_template_description(title, issue, grade, price, publisher, year),
            'source': 'template'
        }
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = _build_prompt(title, issue, publisher, year, verdict_basis)

        response = client.messages.create(
            model=SONNET,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        description = response.content[0].text.strip()
        
        # Clean up the description
        description = _sanitize_description(description)

        # An unresolved edition that still came back with a KEY ISSUE claim is the
        # AI ignoring the rule; the template says nothing edition-specific.
        if verdict_basis == EDITION_UNRESOLVED and 'KEY ISSUE' in description.upper():
            print(f"Description for {title} #{issue} claimed KEY ISSUE on an unresolved edition; using template")
            return {'success': True,
                    'description': _generate_template_description(title, issue, grade, price, publisher, year),
                    'source': 'template'}
        
        # Validate length
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH-3] + "..."
        
        print(f"AI description generated successfully for {title} #{issue}")
        
        return {
            'success': True,
            'description': description,
            'source': 'ai'
        }
        
    except Exception as e:
        print(f"AI description generation failed: {e}")
        # Fallback to template
        return {
            'success': True,
            'description': _generate_template_description(title, issue, grade, price, publisher, year),
            'source': 'template',
            'ai_error': str(e)
        }


def _generate_template_description(title: str, issue: str, grade: str, price: float,
                                   publisher: str = None, year: int = None) -> str:
    """Generate a basic template-based description as fallback. Target: under 300 chars."""
    
    # Title, publisher, year shown in other eBay fields - just provide basic collectibility note
    return "A collectible comic for any collection. Great addition for fans and collectors alike."


def _sanitize_description(description: str) -> str:
    """Clean up and sanitize the description for eBay compliance."""
    
    # Remove any markdown code blocks if present
    if description.startswith('```'):
        lines = description.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        description = '\n'.join(lines)
    
    # Remove banned words using word boundaries (won't catch "Cassidy" or "classic")
    import re
    description = re.sub(BANNED_WORDS_PATTERN, lambda m: '*' * len(m.group()), description, flags=re.IGNORECASE)
    
    # Remove potentially problematic HTML tags
    import re
    # Only allow safe tags
    allowed_tags = ['p', 'br', 'b', 'strong', 'i', 'em', 'ul', 'ol', 'li', 'h2', 'h3']
    
    # Remove script, style, iframe, etc.
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<style[^>]*>.*?</style>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'javascript:',
        r'onclick=',
        r'onerror=',
        r'onload='
    ]
    
    for pattern in dangerous_patterns:
        description = re.sub(pattern, '', description, flags=re.IGNORECASE | re.DOTALL)
    
    return description.strip()


def validate_description(description: str) -> dict:
    """
    Validate a description before submission.
    
    Returns dict with 'valid' boolean and list of 'issues' if any.
    """
    issues = []
    
    if len(description) > MAX_DESCRIPTION_LENGTH:
        issues.append(f"Description too long ({len(description)} chars, max {MAX_DESCRIPTION_LENGTH})")
    
    if len(description) < 50:
        issues.append("Description too short (minimum 50 characters recommended)")
    
    # Check for banned words using word boundaries
    import re
    if re.search(BANNED_WORDS_PATTERN, description, re.IGNORECASE):
        issues.append("Contains inappropriate language")
    
    # Check for external links
    if 'http://' in description or 'https://' in description or 'www.' in description:
        issues.append("External links are not allowed in eBay descriptions")
    
    # Check for contact info patterns
    import re
    if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', description):
        issues.append("Phone numbers are not allowed")
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', description):
        issues.append("Email addresses are not allowed")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }
