"""
eBay Description Generator for CollectionCalc
Generates professional, eBay-compliant descriptions for comic book listings.
"""

import os
import anthropic

# eBay description constraints
MAX_DESCRIPTION_LENGTH = 4000
# Only match standalone bad words, not parts of names like "Cassidy" or "classic"
BANNED_WORDS_PATTERN = r'\b(fuck|shit|damn|bitch|crap)\b'

def generate_description(title: str, issue: str, grade: str, price: float, 
                         publisher: str = None, year: int = None) -> dict:
    """
    Generate a professional eBay-ready description for a comic book listing.
    
    Args:
        title: Comic book title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "300")
        grade: Comic grade (NM, VF, FN, etc.)
        price: Listing price in USD
        publisher: Publisher name (optional)
        year: Publication year (optional)
    
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
        
        # Build context
        comic_info = f"{title} #{issue}"
        if publisher:
            comic_info += f" ({publisher})"
        if year:
            comic_info += f" - {year}"
        
        grade_descriptions = {
            'MT': 'Mint condition - Perfect, as-new state',
            'NM': 'Near Mint - Excellent condition with minimal wear',
            'VF': 'Very Fine - Minor wear, presents beautifully',
            'FN': 'Fine - Light wear, very good overall condition',
            'VG': 'Very Good - Moderate wear but complete and intact',
            'G': 'Good - Noticeable wear, solid reading copy',
            'FR': 'Fair - Heavy wear but complete',
            'PR': 'Poor - Significant wear and possible damage'
        }
        
        grade_desc = grade_descriptions.get(grade.upper(), f'{grade} condition')
        
        prompt = f"""Generate a 300 character eBay listing description for this comic book.

Comic: {comic_info}

TARGET: Exactly 250-300 characters. This is critical for eBay mobile display.

Example (267 characters):
"DC Comics (1984), Bronze Age. KEY ISSUE: First appearance of Blue Devil (Dan Cassidy). Created by Dan Mishkin, Gary Cohn, and Paris Cullins. A must-have for Bronze Age DC collectors and fans of supernatural superhero comics."

Include ONLY:
- Publisher and year
- Era (Golden/Silver/Bronze/Copper/Modern Age)
- KEY ISSUE status if applicable (first appearance, origin, death, major event) - call this out explicitly
- Key characters introduced or featured
- Creators (writer/artist) if notable
- Why it's collectible (1 short phrase)

Do NOT include:
- Grade or condition (shown separately on eBay)
- "Please review photos" or similar (seller policies cover this)
- Shipping or packaging info
- CollectionCalc or AI mentions
- HTML tags - plain text only

Generate only the description, nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        
        description = response.content[0].text.strip()
        
        # Clean up the description
        description = _sanitize_description(description)
        
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
    
    # Build concise description - no grade, no "review photos" (those appear elsewhere)
    parts = [f"{title} #{issue}"]
    
    if publisher and year:
        parts.append(f"from {publisher} ({year})")
    elif publisher:
        parts.append(f"from {publisher}")
    elif year:
        parts.append(f"({year})")
    
    parts.append("- A collectible comic for any collection.")
    
    return " ".join(parts)


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
