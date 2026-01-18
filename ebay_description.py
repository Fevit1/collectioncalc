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
        
        prompt = f"""Generate a professional eBay listing description for this comic book:

Comic: {comic_info}
Grade: {grade} - {grade_desc}
Price: ${price:.2f}

Write a description similar to this eBay style example:
"The product is Firestorm #1, a comic book published by DC Comics in March 1978 during the Bronze Age era of US Comics. The storyline introduces characters such as Ronnie Raymond, Mr. Taubman, Firestorm, Prof. Martin Stein, and Doreen Day in a superhero genre setting. With artwork by Joe Rubinstein, Gerry Conway, Adrienne Roy, and Klaus Janson, this collectible comic is a key addition to any comics and graphic novels collection."

Requirements:
1. Professional, collector-focused tone
2. Include publisher and publication era (Golden Age, Silver Age, Bronze Age, Modern Age) if you know it
3. Mention key characters that appear in this issue
4. Mention creators (writer, artist) if you know them
5. Explain why this issue is collectible or significant
6. Include the grade and briefly what it means
7. Do NOT mention shipping, packaging, or handling
8. Do NOT mention CollectionCalc or that this was AI-generated
9. Use clean HTML formatting (only <p>, <br>, <b> tags - no lists)
10. Do NOT include the title or price (eBay shows those separately)
11. Do NOT include any contact information, external links, or policies
12. End with exactly: "Please review all photos carefully before purchasing. Feel free to message with any questions."

Generate only the description HTML, nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        description = response.content[0].text.strip()
        
        # Clean up the description
        description = _sanitize_description(description)
        
        # Validate length
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH-3] + "..."
        
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
    """Generate a basic template-based description as fallback."""
    
    grade_descriptions = {
        'MT': 'Mint - perfect, as-new condition with no visible wear',
        'NM': 'Near Mint - excellent condition with only minimal wear visible upon close inspection',
        'VF': 'Very Fine - a sharp, attractive copy with minor wear',
        'FN': 'Fine - an above-average copy showing moderate wear',
        'VG': 'Very Good - shows moderate wear but is fully intact and complete',
        'G': 'Good - a well-read copy with noticeable wear, ideal for reading',
        'FR': 'Fair - heavy wear present but the comic is complete',
        'PR': 'Poor - significant wear and possible damage, for collectors who need any copy'
    }
    
    grade_text = grade_descriptions.get(grade.upper(), f'{grade} condition')
    
    # Build basic description
    desc_parts = []
    
    comic_desc = f"This is {title} #{issue}"
    if publisher:
        comic_desc += f", published by {publisher}"
    if year:
        comic_desc += f" in {year}"
    comic_desc += "."
    desc_parts.append(f"<p>{comic_desc}</p>")
    
    desc_parts.append(f"<p><b>Condition:</b> {grade} - {grade_text}.</p>")
    desc_parts.append("<p>This comic has been carefully evaluated and graded. A great addition to any collection.</p>")
    desc_parts.append("<p>Please review all photos carefully before purchasing. Feel free to message with any questions.</p>")
    
    return "\n\n".join(desc_parts)


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
