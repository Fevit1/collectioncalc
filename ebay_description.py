"""
eBay Description Generator for CollectionCalc
Generates professional, eBay-compliant descriptions for comic book listings.
"""

import os
import anthropic

# eBay description constraints
MAX_DESCRIPTION_LENGTH = 4000
BANNED_WORDS = ['fuck', 'shit', 'damn', 'ass', 'bitch', 'crap']  # Simplified list

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
        
        prompt = f"""Generate a VERY SHORT eBay listing description for this comic book.

Comic: {comic_info}
Grade: {grade} - {grade_desc}

MAXIMUM 300 CHARACTERS TOTAL. This is critical for mobile display.

Example (283 characters):
"This is Firestorm #1 from DC Comics (1978), a Bronze Age key introducing Ronnie Raymond and Prof. Martin Stein. Art by Al Milgrom, story by Gerry Conway. Grade: VF - sharp copy with minor wear. Please review all photos carefully. Feel free to message with any questions."

Write in this exact style:
- Sentence 1: What it is (title, publisher, year/era, key characters or significance)
- Sentence 2: Creators if notable
- Sentence 3: Grade and what it means
- Sentence 4: "Please review all photos carefully. Feel free to message with any questions."

Do NOT mention shipping, CollectionCalc, or AI. Use plain text, no HTML tags.

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
    
    grade_descriptions = {
        'MT': 'Mint - perfect condition',
        'NM': 'Near Mint - excellent with minimal wear',
        'VF': 'Very Fine - sharp with minor wear',
        'FN': 'Fine - above-average with moderate wear',
        'VG': 'Very Good - moderate wear, fully intact',
        'G': 'Good - noticeable wear, great for reading',
        'FR': 'Fair - heavy wear but complete',
        'PR': 'Poor - significant wear'
    }
    
    grade_text = grade_descriptions.get(grade.upper(), f'{grade} condition')
    
    # Build concise description - target under 300 chars
    comic_desc = f"This is {title} #{issue}"
    if publisher and year:
        comic_desc += f" from {publisher} ({year})"
    elif publisher:
        comic_desc += f" from {publisher}"
    elif year:
        comic_desc += f" ({year})"
    comic_desc += f". Grade: {grade} - {grade_text}. Please review all photos carefully. Feel free to message with any questions."
    
    return comic_desc


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
    
    # Remove banned words (case insensitive)
    desc_lower = description.lower()
    for word in BANNED_WORDS:
        if word in desc_lower:
            # Replace with asterisks
            import re
            description = re.sub(re.escape(word), '*' * len(word), description, flags=re.IGNORECASE)
    
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
    
    desc_lower = description.lower()
    for word in BANNED_WORDS:
        if word in desc_lower:
            issues.append(f"Contains inappropriate language")
            break
    
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
