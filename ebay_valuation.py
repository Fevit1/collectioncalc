"""
eBay-Powered Valuation Module
Searches eBay sold listings and applies recency/volume weighting.
Includes caching to reduce API costs and improve consistency.
Uses PostgreSQL for persistent cache storage.
"""

import os
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import anthropic

# Try to import psycopg2 for PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    print("psycopg2 not installed - cache will not persist")

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

def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL environment variable."""
    if not HAS_POSTGRES:
        print("psycopg2 not available")
        return None
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set")
        return None
    
    try:
        # Try with SSL first (required by Render)
        conn = psycopg2.connect(database_url, sslmode='require')
        return conn
    except Exception as e:
        print(f"PostgreSQL connection error (with SSL): {e}")
        # Try without SSL as fallback
        try:
            conn = psycopg2.connect(database_url)
            return conn
        except Exception as e2:
            print(f"PostgreSQL connection error (without SSL): {e2}")
            return None

def init_cache_db():
    """Initialize the cache table in PostgreSQL."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_cache (
                id SERIAL PRIMARY KEY,
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
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Cache init error: {e}")
        conn.close()
        return False

def get_cached_result(title: str, issue: str) -> Optional[EbayValuationResult]:
    """Check PostgreSQL cache for existing search result."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        init_cache_db()
        cursor = conn.cursor()
        
        search_key = f"{title.lower().strip()}|{issue.strip()}"
        
        cursor.execute('''
            SELECT estimated_value, confidence, confidence_score, num_sales, 
                   price_min, price_max, sales_data, reasoning, cached_at
            FROM search_cache 
            WHERE search_key = %s
        ''', (search_key,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            cached_at = row[8]
            if isinstance(cached_at, str):
                cached_at = datetime.strptime(cached_at, '%Y-%m-%d %H:%M:%S')
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
        try:
            conn.close()
        except:
            pass
        return None

def save_to_cache(title: str, issue: str, result: EbayValuationResult):
    """Save search result to PostgreSQL cache."""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        init_cache_db()
        cursor = conn.cursor()
        
        search_key = f"{title.lower().strip()}|{issue.strip()}"
        
        # Use INSERT ... ON CONFLICT for upsert
        cursor.execute('''
            INSERT INTO search_cache 
            (title, issue, search_key, estimated_value, confidence, confidence_score,
             num_sales, price_min, price_max, sales_data, reasoning, cached_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (search_key) 
            DO UPDATE SET
                estimated_value = EXCLUDED.estimated_value,
                confidence = EXCLUDED.confidence,
                confidence_score = EXCLUDED.confidence_score,
                num_sales = EXCLUDED.num_sales,
                price_min = EXCLUDED.price_min,
                price_max = EXCLUDED.price_max,
                sales_data = EXCLUDED.sales_data,
                reasoning = EXCLUDED.reasoning,
                cached_at = EXCLUDED.cached_at
        ''', (
            title, issue, search_key, result.estimated_value, result.confidence,
            result.confidence_score, result.num_sales, result.price_range[0],
            result.price_range[1], json.dumps(result.sales_data), result.reasoning,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Cached: {title} #{issue} = ${result.estimated_value}")
    except Exception as e:
        print(f"Cache write error: {e}")
        try:
            conn.close()
        except:
            pass

def update_cached_value(title: str, issue: str, new_value: float, samples: list = None) -> bool:
    """Update PostgreSQL cache with a new averaged value from admin refresh."""
    # Expand aliases
    title = expand_title_alias(title)
    
    conn = get_db_connection()
    if not conn:
        print("No database connection for cache update")
        return False
    
    try:
        init_cache_db()
        cursor = conn.cursor()
        
        search_key = f"{title.lower().strip()}|{issue.strip()}"
        
        # Build reasoning
        if samples:
            samples_str = ', '.join([f'${s:.2f}' for s in samples])
            reasoning = f"[REFRESHED] Average of {len(samples)} samples: {samples_str}"
        else:
            reasoning = "[REFRESHED] Admin override"
        
        # Build sales data from samples
        sales_data = []
        if samples:
            for i, price in enumerate(samples):
                sales_data.append({
                    'price': price,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'weight': 1.0,
                    'source': f'Refresh sample {i+1}'
                })
        
        price_min = min(samples) if samples else new_value
        price_max = max(samples) if samples else new_value
        
        # Use INSERT ... ON CONFLICT for upsert
        cursor.execute('''
            INSERT INTO search_cache 
            (title, issue, search_key, estimated_value, confidence, confidence_score,
             num_sales, price_min, price_max, sales_data, reasoning, cached_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (search_key) 
            DO UPDATE SET
                estimated_value = EXCLUDED.estimated_value,
                confidence = EXCLUDED.confidence,
                confidence_score = EXCLUDED.confidence_score,
                num_sales = EXCLUDED.num_sales,
                price_min = EXCLUDED.price_min,
                price_max = EXCLUDED.price_max,
                sales_data = EXCLUDED.sales_data,
                reasoning = EXCLUDED.reasoning,
                cached_at = EXCLUDED.cached_at
        ''', (
            title, issue, search_key, new_value, 'HIGH', 85,
            len(samples) if samples else 1, price_min, price_max,
            json.dumps(sales_data), reasoning,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Cache updated: {title} #{issue} = ${new_value:.2f}")
        return True
    except Exception as e:
        print(f"Cache update error: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def get_cache_db_path():
    """Legacy function for compatibility - returns None for PostgreSQL."""
    return None

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

def _single_search(client, title: str, issue: str, grade: str, publisher: str = None) -> tuple:
    """
    Run a single search query. Returns (sales_list, corrected_title) or ([], None) on error.
    """
    # Build search query - don't include grade (most listings don't specify)
    search_query = f"{title} #{issue} comic"
    if publisher:
        search_query += f" {publisher}"
    search_query += " price sold value"
    
    prompt = f"""Search for the current market value of this comic book: {title} #{issue}

IMPORTANT: First, correct any spelling errors in the title (e.g., "Captian America" → "Captain America", "Spiderman" → "Spider-Man", "Batmam" → "Batman"). Search using the corrected title.

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
    "corrected_title": "Captain America",
    "notes": "Brief notes about the search results"
}}

Rules:
- Include the source for each price (eBay, GoCollect, etc.)
- Include date if available (estimate month/year if exact date unknown)
- Note the grade if specified (use "raw" if ungraded)
- If no prices found, return empty sales array
- Maximum 10 prices
- Prices in USD
- Include "corrected_title" if you fixed any spelling"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            timeout=60.0,
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
            corrected_title = data.get('corrected_title', None)
            return (sales, corrected_title)
        
    except Exception as e:
        print(f"Search error: {e}")
    
    return ([], None)


def search_ebay_sold(title: str, issue: str, grade: str, publisher: str = None, num_samples: int = 3, force_refresh: bool = False) -> EbayValuationResult:
    """
    Search for market prices using Claude AI with web search.
    Runs multiple samples and takes median for accuracy.
    Checks cache first, saves successful results to cache.
    """
    # Expand aliases (ASM → Amazing Spider-Man)
    title = expand_title_alias(title)
    
    # Check cache first (unless force_refresh)
    if not force_refresh:
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
    
    # Run multiple searches for better accuracy
    all_sales = []
    corrected_title = None
    
    for i in range(num_samples):
        sales, title_fix = _single_search(client, title, issue, grade, publisher)
        all_sales.extend(sales)
        if title_fix and not corrected_title:
            corrected_title = title_fix
    
    # Deduplicate by price+date+source
    seen = set()
    sales = []
    for sale in all_sales:
        key = f"{sale.get('price')}-{sale.get('date')}-{sale.get('source')}"
        if key not in seen:
            seen.add(key)
            sales.append(sale)
    
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
        f"Found {len(prices)} price(s) from 3-sample search",
        f"Price range: ${price_min:.2f} - ${price_max:.2f}",
        f"Recency-weighted average: ${recency_weighted_avg:.2f}"
    ]
    
    # Add spelling correction note if title was corrected
    if corrected_title and corrected_title.lower() != title.lower():
        reasoning_parts.insert(0, f"Corrected spelling: '{title}' → '{corrected_title}'")
    
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
                            db_result: dict = None, force_refresh: bool = False) -> dict:
    """
    Main valuation function that combines database and eBay data.
    Set force_refresh=True to bypass cache and get fresh eBay data.
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
        ebay_result = search_ebay_sold(title, issue, grade, publisher, force_refresh=force_refresh)
        
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
        ebay_result = search_ebay_sold(title, issue, grade, publisher, force_refresh=force_refresh)
        
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
