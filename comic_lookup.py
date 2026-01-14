"""
CollectionCalc - Comic Lookup Module
Fast database lookups with fuzzy matching for comic valuations
"""

import sqlite3
import re
from difflib import SequenceMatcher
from typing import Optional, Dict, List, Tuple

DB_PATH = "comics_pricing.db"


def normalize_title(title: str) -> str:
    """Normalize title for consistent matching"""
    if not title:
        return ""
    
    normalized = title.lower().strip()
    
    # Remove common prefixes
    prefixes = ['the ', 'a ']
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Standardize punctuation
    normalized = re.sub(r'[:\-–—]', ' ', normalized)
    normalized = re.sub(r'[\'\"''""]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def normalize_issue(issue: str) -> str:
    """Normalize issue number"""
    if not issue:
        return ""
    
    # Extract just the number (handle "#1", "Issue 1", etc.)
    match = re.search(r'(\d+[a-zA-Z]?)', str(issue))
    if match:
        return match.group(1).lower()
    return str(issue).strip().lower()


def normalize_publisher(publisher: str) -> str:
    """Normalize publisher name using aliases"""
    if not publisher:
        return ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Try to find a canonical name
    cursor.execute('''
        SELECT canonical_name FROM publisher_aliases 
        WHERE alias = ?
    ''', (publisher.lower(),))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return publisher


def similarity_score(s1: str, s2: str) -> float:
    """Calculate string similarity (0-1)"""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def lookup_comic(
    title: str,
    issue: str,
    publisher: Optional[str] = None,
    year: Optional[int] = None,
    grade: str = "NM",
    edition: str = "direct",
    cgc: bool = False
) -> Dict:
    """
    Look up a comic in the database and return estimated value
    
    Args:
        title: Comic title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "300" or "#300")
        publisher: Publisher name (optional, helps with disambiguation)
        year: Publication year (optional, helps with disambiguation)
        grade: Grade string (e.g., "NM", "VF", "FN")
        edition: Edition type (e.g., "direct", "newsstand")
        cgc: Whether it's CGC graded
        
    Returns:
        Dict with:
            - found: bool
            - title: matched title
            - issue: matched issue
            - base_value: NM value from database
            - estimated_value: adjusted for grade/edition
            - confidence: match confidence (0-1)
            - source: where the price came from
            - needs_web_search: bool - should fall back to web search
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Normalize inputs
    norm_title = normalize_title(title)
    norm_issue = normalize_issue(issue)
    norm_publisher = normalize_publisher(publisher) if publisher else None
    
    result = {
        'found': False,
        'title': title,
        'issue': issue,
        'base_value': None,
        'estimated_value': None,
        'confidence': 0,
        'source': None,
        'needs_web_search': True,
        'match_details': {}
    }
    
    # Strategy 1: Exact match on normalized title + issue
    if norm_publisher:
        cursor.execute('''
            SELECT title, issue_number, publisher, nm_value, source, last_updated
            FROM comics
            WHERE title_normalized = ? AND issue_number = ? AND publisher = ?
        ''', (norm_title, norm_issue, norm_publisher))
    else:
        cursor.execute('''
            SELECT title, issue_number, publisher, nm_value, source, last_updated
            FROM comics
            WHERE title_normalized = ? AND issue_number = ?
        ''', (norm_title, norm_issue))
    
    matches = cursor.fetchall()
    
    # Strategy 2: If no exact match, try fuzzy matching
    if not matches:
        cursor.execute('''
            SELECT title, title_normalized, issue_number, publisher, nm_value, source
            FROM comics
            WHERE issue_number = ?
        ''', (norm_issue,))
        
        potential_matches = cursor.fetchall()
        
        # Find best fuzzy match
        best_match = None
        best_score = 0
        
        for pm in potential_matches:
            score = similarity_score(norm_title, pm[1])
            
            # Boost score if publisher matches
            if norm_publisher and pm[3] == norm_publisher:
                score += 0.1
            
            if score > best_score and score > 0.7:  # Minimum 70% similarity
                best_score = score
                best_match = pm
        
        if best_match:
            matches = [(best_match[0], best_match[2], best_match[3], best_match[4], best_match[5], None)]
            result['confidence'] = best_score
            result['match_details']['fuzzy_match'] = True
        else:
            # No good match found
            conn.close()
            result['needs_web_search'] = True
            return result
    else:
        result['confidence'] = 1.0
        result['match_details']['exact_match'] = True
    
    # We found a match!
    if matches:
        match = matches[0]
        result['found'] = True
        result['title'] = match[0]
        result['issue'] = match[1]
        result['publisher'] = match[2]
        result['base_value'] = match[3]
        result['source'] = match[4]
        result['last_updated'] = match[5]
        result['needs_web_search'] = False
        
        # Apply grade multiplier
        cursor.execute('''
            SELECT multiplier FROM grade_multipliers WHERE grade = ?
        ''', (grade.upper(),))
        grade_mult = cursor.fetchone()
        grade_multiplier = grade_mult[0] if grade_mult else 1.0
        
        # Apply edition multiplier
        cursor.execute('''
            SELECT multiplier FROM edition_multipliers WHERE edition_type = ?
        ''', (edition.lower(),))
        edition_mult = cursor.fetchone()
        edition_multiplier = edition_mult[0] if edition_mult else 1.0
        
        # CGC premium
        cgc_multiplier = 1.3 if cgc else 1.0
        
        # Calculate estimated value
        base = result['base_value'] or 0
        estimated = base * grade_multiplier * edition_multiplier * cgc_multiplier
        result['estimated_value'] = round(estimated, 2)
        
        result['match_details']['grade_multiplier'] = grade_multiplier
        result['match_details']['edition_multiplier'] = edition_multiplier
        result['match_details']['cgc_multiplier'] = cgc_multiplier
        
        # Check if this is a key issue
        cursor.execute('''
            SELECT reason, premium_multiplier FROM key_issues 
            WHERE title_normalized = ? AND issue_number = ?
        ''', (normalize_title(result['title']), result['issue']))
        
        key_issue = cursor.fetchone()
        if key_issue:
            result['match_details']['key_issue'] = True
            result['match_details']['key_reason'] = key_issue[0]
            # Note: Key issue premiums are usually already in the base price
    
    conn.close()
    return result


def batch_lookup(comics: List[Dict]) -> List[Dict]:
    """
    Look up multiple comics at once
    
    Args:
        comics: List of dicts with keys: title, issue, publisher (optional), 
                grade (optional), edition (optional), cgc (optional)
    
    Returns:
        List of lookup results with needs_web_search flag
    """
    results = []
    need_web_search = []
    
    for i, comic in enumerate(comics):
        result = lookup_comic(
            title=comic.get('title', ''),
            issue=comic.get('issue', ''),
            publisher=comic.get('publisher'),
            year=comic.get('year'),
            grade=comic.get('grade', 'NM'),
            edition=comic.get('edition', 'direct'),
            cgc=comic.get('cgc', False)
        )
        
        result['index'] = i
        results.append(result)
        
        if result['needs_web_search']:
            need_web_search.append(i)
    
    return {
        'results': results,
        'found_count': len([r for r in results if r['found']]),
        'need_web_search_count': len(need_web_search),
        'need_web_search_indices': need_web_search
    }


def get_grade_multiplier(grade: str) -> float:
    """Get the multiplier for a specific grade"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT multiplier FROM grade_multipliers WHERE grade = ?', (grade.upper(),))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 1.0


def get_all_grades() -> List[Dict]:
    """Get all grades and their multipliers"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT grade, grade_numeric, multiplier, description FROM grade_multipliers ORDER BY grade_numeric DESC')
    results = cursor.fetchall()
    conn.close()
    
    return [
        {'grade': r[0], 'numeric': r[1], 'multiplier': r[2], 'description': r[3]}
        for r in results
    ]


def search_titles(query: str, limit: int = 10) -> List[Dict]:
    """Search for comic titles in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    norm_query = normalize_title(query)
    
    cursor.execute('''
        SELECT DISTINCT title, publisher, COUNT(*) as issue_count
        FROM comics
        WHERE title_normalized LIKE ?
        GROUP BY title, publisher
        ORDER BY issue_count DESC
        LIMIT ?
    ''', (f'%{norm_query}%', limit))
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {'title': r[0], 'publisher': r[1], 'issue_count': r[2]}
        for r in results
    ]


# Quick test function
def test_lookup():
    """Test the lookup functionality"""
    test_cases = [
        {'title': 'Amazing Spider-Man', 'issue': '300', 'grade': 'VF'},
        {'title': 'Batman', 'issue': '1', 'publisher': 'DC Comics', 'grade': 'NM'},
        {'title': 'X-Men', 'issue': '1', 'grade': 'NM', 'edition': 'newsstand'},
        {'title': 'Spawn', 'issue': '1', 'grade': 'NM', 'cgc': True},
    ]
    
    print("\n" + "=" * 60)
    print("COMIC LOOKUP TEST")
    print("=" * 60)
    
    for comic in test_cases:
        result = lookup_comic(**comic)
        print(f"\n📚 {comic['title']} #{comic['issue']}")
        print(f"   Found: {result['found']}")
        print(f"   Confidence: {result['confidence']:.0%}")
        if result['found']:
            print(f"   Base Value (NM): ${result['base_value']:.2f}")
            print(f"   Estimated Value: ${result['estimated_value']:.2f}")
            print(f"   Source: {result['source']}")
        else:
            print(f"   Needs web search: {result['needs_web_search']}")


if __name__ == "__main__":
    test_lookup()
