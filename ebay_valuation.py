"""
eBay-Powered Valuation Module
Searches eBay sold listings and applies recency/volume weighting.
Includes caching to reduce API costs and improve consistency.
"""

import os
import json
import re
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import anthropic

@dataclass
class EbaySale:
    price: float
    date: datetime
    grade: Optional[str] = None
    is_cgc: bool = False

@dataclass 
class EbayValuationResult:
    estimated_value: float
    confidence: str  # HIGH, MEDIUM-HIGH, MEDIUM, LOW, VERY LOW
    confidence_score: int  # 0-100
    num_sales: int
    price_range: tuple  # (min, max)
    recency_weighted_avg: float
    sales_data: List[dict]
    reasoning: str

# Recency weights
RECENCY_WEIGHTS = {
    'this_week': 1.0,
    'this_month': 0.9,
    'last_3_months': 0.7,
    'last_year': 0.5,
    'older': 0.25
}

# Cache duration in hours
CACHE_DURATION_HOURS = 48

# Common comic abbreviations
TITLE_ALIASES = {
    'asm': 'Amazing Spider-Man',
    'tasm': 'The Amazing Spider-Man',
    'uxm': 'Uncanny X-Men',
    'xmen': 'X-Men',
    'ff': 'Fantastic Four',
    'tmnt': 'Teenage Mutant Ninja Turtles',
    'swb': 'Star Wars Bounty Hunters',
    'dkr': 'Batman The Dark Knight Returns',
    'twd': 'The Walking Dead',
    'tos': 'Tales of Suspense',
    'tot': 'Tales to Astonish',
    'jla': 'Justice League of America',
    'jli': 'Justice League International',
    'avx': 'Avengers vs X-Men',
    'gg': 'Green Goblin',
    'gl': 'Green Lantern',
    'ga': 'Green Arrow',
    'bp': 'Black Panther',
    'bm': 'Batman',
    'sm': 'Superman',
    'ww': 'Wonder Woman',
    'ss': 'Silver Surfer',
    'dp': 'Deadpool',
    'dd': 'Daredevil',
    'pp': 'Peter Parker',
    'mtu': 'Marvel Team-Up',
    'mtio': 'Marvel Two-In-One',
    'gsxm': 'Giant-Size X-Men',
    'nyx': 'NYX',
    'nm': 'New Mutants',
    'hulk': 'Incredible Hulk',
    'ih': 'Incredible Hulk',
    'im': 'Iron Man',
    'thor': 'Thor',
    'cap': 'Captain America',
    'ca': 'Captain America',
    'af': 'Amazing Fantasy',
    'sw': 'Secret Wars',
    'coie': 'Crisis on Infinite Earths',
    'hq': 'Harley Quinn',
    'sg': 'Supergirl',
    'aquaman': 'Aquaman',
    'flash': 'The Flash',
    'spawn': 'Spawn',
    'saga': 'Saga',
    'wm': 'War Machine',
    'ms': 'Ms Marvel',
    'cm': 'Captain Marvel',
}

def expand_title_alias(title: str) -> str:
    """Expand common comic abbreviations to full titles."""
    title_lower = title.lower().strip()
    return TITLE_ALIASES.get(title_lower, title)

def get_cache_db_path():
    """Get path to cache database."""
    return os.path.join(os.path.dirname(__file__), 'price_cache.db')

def init_cache_db():
    """Initialize the cache database."""
    conn = sqlite3.connect(get_cache_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            issue TEXT NOT NULL,
            search_key TEXT UNIQUE NOT NULL,
            estimated_value REAL,
            confidence TEXT,
            confidence_score INTEGER,
            num_sales INTEGER,
            price_min REAL,
            price_max REAL,
            sales_data TEXT,
            reasoning TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_cached_result(title: str, issue: str) -> Optional[EbayValuationResult]:
    """Check cache for existing search result."""
    try:
        init_cache_db()
        conn = sqlite3.connect(get_cache_db_path())
        cursor = conn.cursor()
        
        search_key = f"{title.lower().strip()}|{issue.strip()}"
        
        cursor.execute('''
            SELECT estimated_value, confidence, confidence_score, num_sales, 
                   price_min, price_max, sales_data, reasoning, cached_at
            FROM search_cache 
            WHERE search_key = ?
        ''', (search_key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            cached_at = datetime.strptime(row[8], '%Y-%m-%d %H:%M:%S')
            age_hours = (datetime.now() - cached_at).total_seconds() / 3600
            
            # Check if cache is still valid
            if age_hours < CACHE_DURATION_HOURS:
                return EbayValuationResult(
                    estimated_value=row[0],
                    confidence=row[1],
                    confidence_score=row[2],
                    num_sales=row[3],
                    price_range=(row[4], row[5]),
                    recency_weighted_avg=row[0],
                    sales_data=json.loads(row[6]) if row[6] else [],
                    reasoning=f"[CACHED] {row[7]}"
                )
        return None
    except Exception as e:
        print(f"Cache read error: {e}")
        return None

def save_to_cache(title: str, issue: str, result: EbayValuationResult):
    """Save search result to cache."""
    try:
        init_cache_db()
        conn = sqlite3.connect(get_cache_db_path())
        cursor = conn.cursor()
        
        search_key = f"{title.lower().strip()}|{issue.strip()}"
        
        cursor.execute('''
            INSERT OR REPLACE INTO search_cache 
            (title, issue, search_key, estimated_value, confidence, confidence_score,
             num_sales, price_min, price_max, sales_data, reasoning, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title, issue, search_key, result.estimated_value, result.confidence,
            result.confidence_score, result.num_sales, result.price_range[0],
            result.price_range[1], json.dumps(result.sales_data), result.reasoning,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cache write error: {e}")

def get_recency_weight(sale_date: datetime) -> float:
    """Calculate recency weight based on sale date."""
    now = datetime.now()
    days_ago = (now - sale_date).days
    
    if days_ago <= 7:
        return RECENCY_WEIGHTS['this_week']
    elif days_ago <= 30:
        return RECENCY_WEIGHTS['this_month']
    elif days_ago <= 90:
        return RECENCY_WEIGHTS['last_3_months']
    elif days_ago <= 365:
        return RECENCY_WEIGHTS['last_year']
    else:
        return RECENCY_WEIGHTS['older']

def calculate_confidence(num_sales: int, days_span: int, price_variance: float) -> tuple:
    """
    Calculate confidence based on volume, recency, and price consistency.
    Returns (confidence_label, confidence_score)
    """
    score = 50  # Base score
    
    # Volume factor (+/- 25 points)
    if num_sales >= 10:
        score += 25
    elif num_sales >= 5:
        score += 15
    elif num_sales >= 2:
        score += 5
    elif num_sales == 1:
        score -= 15
    else:
        score -= 25
    
    # Recency factor (+/- 15 points)
    if days_span <= 30:
        score += 15
    elif days_span <= 90:
        score += 10
    elif days_span <= 365:
        score += 0
    else:
        score -= 10
    
    # Price variance factor (+/- 10 points)
    # variance is coefficient of variation (std/mean)
    if price_variance < 0.1:  # Very consistent
        score += 10
    elif price_variance < 0.25:  # Fairly consistent
        score += 5
    elif price_variance < 0.5:  # Some variance
        score -= 5
    else:  # High variance
        score -= 10
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Map to label
    if score >= 90:
        label = "HIGH"
    elif score >= 70:
        label = "MEDIUM-HIGH"
    elif score >= 50:
        label = "MEDIUM"
    elif score >= 30:
        label = "LOW"
    else:
        label = "VERY LOW"
    
    return label, score

def search_ebay_sold(title: str, issue: str, grade: str, publisher: str = None) -> EbayValuationResult:
    """
    Search for market prices using Claude AI with web search.
    Checks cache first, saves successful results to cache.
    """
    # Expand aliases (ASM → Amazing Spider-Man)
    title = expand_title_alias(title)
    
    # Check cache first
    cached = get_cached_result(title, issue)
    if cached:
        return cached
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        return EbayValuationResult(
            estimated_value=0,
            confidence="VERY LOW",
            confidence_score=0,
            num_sales=0,
            price_range=(0, 0),
            recency_weighted_avg=0,
            sales_data=[],
            reasoning="No API key configured for web search"
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Build search query - don't include grade (most listings don't specify)
    search_query = f"{title} #{issue} comic"
    if publisher:
        search_query += f" {publisher}"
    search_query += " price sold value"
    
    prompt = f"""Search for the current market value of this comic book: {title} #{issue}

Look for recent sale prices, price guide values, and market data from sources like:
- eBay sold listings
- GoCollect
- CovrPrice  
- ComicsPriceGuide
- Heritage Auctions
- Any other comic pricing sources

Return a JSON object with this exact structure:
{{
    "sales": [
        {{"price": 450.00, "date": "2026-01-10", "grade": "raw", "source": "eBay"}},
        {{"price": 520.00, "date": "2025-12-15", "grade": "9.4", "source": "GoCollect"}}
    ],
    "notes": "Brief notes about the search results"
}}

Rules:
- Include the source for each price (eBay, GoCollect, etc.)
- Include date if available (estimate month/year if exact date unknown)
- Note the grade if specified (use "raw" if ungraded)
- If no prices found, return empty sales array
- Maximum 10 prices
- Prices in USD"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            timeout=60.0,  # 60 second timeout
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract text response
        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            data = json.loads(json_match.group())
            sales = data.get('sales', [])
        else:
            sales = []
            # Return diagnostic info
            return EbayValuationResult(
                estimated_value=0,
                confidence="VERY LOW",
                confidence_score=0,
                num_sales=0,
                price_range=(0, 0),
                recency_weighted_avg=0,
                sales_data=[],
                reasoning=f"Could not parse JSON from response. Raw: {result_text[:500]}"
            )
            
    except Exception as e:
        return EbayValuationResult(
            estimated_value=0,
            confidence="VERY LOW",
            confidence_score=0,
            num_sales=0,
            price_range=(0, 0),
            recency_weighted_avg=0,
            sales_data=[],
            reasoning=f"Search error: {str(e)}"
        )
    
    if not sales:
        return EbayValuationResult(
            estimated_value=0,
            confidence="VERY LOW",
            confidence_score=0,
            num_sales=0,
            price_range=(0, 0),
            recency_weighted_avg=0,
            sales_data=[],
            reasoning="No market prices found from web search"
        )
    
    # Process sales data
    processed_sales = []
    prices = []
    weighted_sum = 0
    weight_total = 0
    
    for sale in sales:
        try:
            price = float(sale.get('price', 0))
            date_str = sale.get('date', '')
            
            # Parse date
            try:
                sale_date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                sale_date = datetime.now() - timedelta(days=30)  # Default to 1 month ago
            
            weight = get_recency_weight(sale_date)
            weighted_sum += price * weight
            weight_total += weight
            prices.append(price)
            
            processed_sales.append({
                'price': price,
                'date': sale_date.strftime('%Y-%m-%d'),
                'weight': weight,
                'grade': sale.get('grade'),
                'source': sale.get('source', 'unknown')
            })
        except:
            continue
    
    if not prices:
        return EbayValuationResult(
            estimated_value=0,
            confidence="VERY LOW", 
            confidence_score=0,
            num_sales=0,
            price_range=(0, 0),
            recency_weighted_avg=0,
            sales_data=[],
            reasoning="Could not parse sales data"
        )
    
    # Calculate statistics
    recency_weighted_avg = weighted_sum / weight_total if weight_total > 0 else 0
    price_min = min(prices)
    price_max = max(prices)
    price_mean = sum(prices) / len(prices)
    
    # Calculate variance (coefficient of variation)
    if len(prices) > 1 and price_mean > 0:
        variance = (sum((p - price_mean) ** 2 for p in prices) / len(prices)) ** 0.5
        cv = variance / price_mean
    else:
        cv = 0.5  # Default moderate variance for single sale
    
    # Days span
    if processed_sales:
        dates = [datetime.strptime(s['date'], '%Y-%m-%d') for s in processed_sales]
        days_span = (datetime.now() - min(dates)).days
    else:
        days_span = 365
    
    # Calculate confidence
    confidence_label, confidence_score = calculate_confidence(len(prices), days_span, cv)
    
    # Build reasoning
    reasoning_parts = [
        f"Found {len(prices)} sold listing(s) on eBay",
        f"Price range: ${price_min:.2f} - ${price_max:.2f}",
        f"Recency-weighted average: ${recency_weighted_avg:.2f}"
    ]
    
    if cv < 0.1:
        reasoning_parts.append("Prices very consistent")
    elif cv > 0.5:
        reasoning_parts.append("Prices vary significantly")
    
    result = EbayValuationResult(
        estimated_value=round(recency_weighted_avg, 2),
        confidence=confidence_label,
        confidence_score=confidence_score,
        num_sales=len(prices),
        price_range=(price_min, price_max),
        recency_weighted_avg=round(recency_weighted_avg, 2),
        sales_data=processed_sales,
        reasoning=". ".join(reasoning_parts)
    )
    
    # Save to cache for future requests
    save_to_cache(title, issue, result)
    
    return result


def get_valuation_with_ebay(title: str, issue: str, grade: str, 
                            publisher: str = None, year: int = None,
                            db_result: dict = None) -> dict:
    """
    Main valuation function that combines database and eBay data.
    """
    from valuation_model import ValuationModel
    
    # Expand aliases (ASM → Amazing Spider-Man)
    original_title = title
    title = expand_title_alias(title)
    
    model = ValuationModel()
    
    # If found in database, use that as base
    if db_result and db_result.get('found'):
        base_value = db_result.get('base_value', 50.0)
        source = 'database'
        
        # Still search eBay to validate/adjust
        ebay_result = search_ebay_sold(title, issue, grade, publisher)
        
        if ebay_result.num_sales > 0:
            # Blend database and eBay (favor eBay if high confidence)
            if ebay_result.confidence_score >= 70:
                # High confidence eBay - use eBay price
                final_value = ebay_result.estimated_value
                source = 'ebay_verified'
            else:
                # Lower confidence - blend 50/50
                final_value = (base_value * 0.5) + (ebay_result.estimated_value * 0.5)
                source = 'database+ebay_blend'
        else:
            # No eBay data - use database with grade adjustment
            result = model.calculate_value(
                base_nm_value=base_value,
                grade=grade,
                edition='direct',
                year=year,
                publisher=publisher or 'Unknown'
            )
            final_value = result.final_value
            
        return {
            'final_value': round(final_value, 2),
            'confidence': ebay_result.confidence if ebay_result.num_sales > 0 else 'MEDIUM',
            'confidence_score': ebay_result.confidence_score if ebay_result.num_sales > 0 else 60,
            'source': source,
            'db_found': True,
            'ebay_sales': ebay_result.num_sales,
            'ebay_price_range': ebay_result.price_range,
            'reasoning': ebay_result.reasoning if ebay_result.reasoning else 'Based on database value',
            'sales_data': ebay_result.sales_data,
            'debug': {
                'ebay_attempted': True,
                'ebay_reasoning': ebay_result.reasoning,
                'db_base_value': base_value,
                'title_expanded': title if title != original_title else None
            }
        }
    
    else:
        # Not in database - rely on eBay
        ebay_result = search_ebay_sold(title, issue, grade, publisher)
        
        if ebay_result.num_sales > 0:
            return {
                'final_value': ebay_result.estimated_value,
                'confidence': ebay_result.confidence,
                'confidence_score': ebay_result.confidence_score,
                'source': 'ebay',
                'db_found': False,
                'ebay_sales': ebay_result.num_sales,
                'ebay_price_range': ebay_result.price_range,
                'reasoning': ebay_result.reasoning,
                'sales_data': ebay_result.sales_data,
                'debug': {
                    'ebay_attempted': True,
                    'ebay_reasoning': ebay_result.reasoning,
                    'db_base_value': None,
                    'title_expanded': title if title != original_title else None
                }
            }
        else:
            # No data anywhere - return estimate with very low confidence
            result = model.calculate_value(
                base_nm_value=50.0,  # Default base
                grade=grade,
                edition='direct',
                year=year,
                publisher=publisher or 'Unknown'
            )
            return {
                'final_value': result.final_value,
                'confidence': 'VERY LOW',
                'confidence_score': 20,
                'source': 'estimate',
                'db_found': False,
                'ebay_sales': 0,
                'ebay_price_range': (0, 0),
                'reasoning': 'No market data found. Using default estimate.',
                'sales_data': [],
                'debug': {
                    'ebay_attempted': True,
                    'ebay_reasoning': 'No results found',
                    'db_base_value': None,
                    'title_expanded': title if title != original_title else None
                }
            }
