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
    POSTGRES_IMPORT_ERROR = None
except ImportError as e:
    HAS_POSTGRES = False
    POSTGRES_IMPORT_ERROR = str(e)
    print(f"psycopg2 import error: {e}")

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
    # Tiered pricing
    quick_sale: float = 0.0      # Lowest BIN or lowest sold - for fast sale
    fair_value: float = 0.0      # Median sold price - fair market value
    high_end: float = 0.0        # Highest recent sold - premium price
    lowest_bin: Optional[float] = None  # Current lowest Buy It Now price
    # Per-tier confidence (0-100)
    quick_sale_confidence: int = 50
    fair_value_confidence: int = 50
    high_end_confidence: int = 50

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

# Comic grade scale (numeric values for comparison)
GRADE_SCALE = {
    'MT': 10.0,   # Mint
    'GM': 10.0,   # Gem Mint (alias)
    'NM+': 9.6,
    'NM': 9.4,    # Near Mint
    'NM-': 9.2,
    'VF+': 8.5,
    'VF': 8.0,    # Very Fine
    'VF-': 7.5,
    'FN+': 6.5,
    'FN': 6.0,    # Fine
    'FN-': 5.5,
    'VG+': 4.5,
    'VG': 4.0,    # Very Good
    'VG-': 3.5,
    'G+': 2.5,
    'G': 2.0,     # Good
    'GD': 2.0,    # Good (alias)
    'G-': 1.8,
    'FR': 1.5,    # Fair
    'PR': 1.0,    # Poor
    'raw': 6.0,   # Default for unspecified raw = assume FN
}

def get_grade_value(grade: str) -> float:
    """Convert grade string to numeric value."""
    if not grade:
        return 6.0  # Default to FN
    grade_upper = grade.upper().strip()
    return GRADE_SCALE.get(grade_upper, 6.0)

def is_grade_compatible(sale_grade: str, requested_grade: str, tolerance: float = 1.0) -> bool:
    """
    Check if a sale's grade is within tolerance of the requested grade.
    Default tolerance of 1.0 means ±0.5 grade level (e.g., VF accepts VF-, VF, VF+ only)
    """
    sale_value = get_grade_value(sale_grade)
    requested_value = get_grade_value(requested_grade)
    return abs(sale_value - requested_value) <= tolerance

def expand_title_alias(title: str) -> str:
    """Expand common comic abbreviations to full titles."""
    title_lower = title.lower().strip()
    return TITLE_ALIASES.get(title_lower, title)

def normalize_grade_for_cache(grade: str) -> str:
    """
    Normalize grade variants to base grade for consistent cache keys.
    VF+, VF, VF- all become "VF" for cache purposes.
    This prevents cache misses when different grade variants are requested.
    """
    if not grade:
        return "FN"  # Default
    grade_upper = grade.upper().strip()
    
    # Map all variants to their base grade
    grade_map = {
        # Near Mint variants
        'MT': 'NM', 'GM': 'NM', '10.0': 'NM', '9.8': 'NM', '9.6': 'NM', '9.4': 'NM',
        'NM+': 'NM', 'NM': 'NM', 'NM-': 'NM', '9.2': 'NM',
        # Very Fine variants
        'VF+': 'VF', 'VF': 'VF', 'VF-': 'VF', '8.5': 'VF', '8.0': 'VF', '7.5': 'VF',
        # Fine variants
        'FN+': 'FN', 'FN': 'FN', 'FN-': 'FN', '6.5': 'FN', '6.0': 'FN', '5.5': 'FN',
        # Very Good variants
        'VG+': 'VG', 'VG': 'VG', 'VG-': 'VG', '4.5': 'VG', '4.0': 'VG', '3.5': 'VG',
        # Good variants
        'G+': 'G', 'G': 'G', 'GD': 'G', 'G-': 'G', '2.5': 'G', '2.0': 'G', '1.8': 'G',
        # Fair/Poor
        'FR': 'FR', '1.5': 'FR',
        'PR': 'PR', '1.0': 'PR', '0.5': 'PR'
    }
    return grade_map.get(grade_upper, 'VF')  # Default to VF if unknown

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
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                quick_sale REAL,
                fair_value REAL,
                high_end REAL,
                lowest_bin REAL,
                quick_sale_confidence INTEGER,
                fair_value_confidence INTEGER,
                high_end_confidence INTEGER
            )
        ''')
        
        # Add new columns to existing tables (PostgreSQL supports IF NOT EXISTS)
        new_columns = [
            'quick_sale', 'fair_value', 'high_end', 'lowest_bin',
            'quick_sale_confidence', 'fair_value_confidence', 'high_end_confidence'
        ]
        for col in new_columns:
            try:
                col_type = 'INTEGER' if 'confidence' in col else 'REAL'
                cursor.execute(f'ALTER TABLE search_cache ADD COLUMN IF NOT EXISTS {col} {col_type}')
            except Exception as col_err:
                print(f"Column {col} add note: {col_err}")
                pass  # Column might already exist or other issue
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Cache init error: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def get_cached_result(title: str, issue: str, grade: str = None) -> Optional[EbayValuationResult]:
    """Check PostgreSQL cache for existing search result."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        init_cache_db()
        cursor = conn.cursor()
        
        # Include NORMALIZED grade in cache key if provided (VF+, VF, VF- all map to "VF")
        if grade:
            normalized_grade = normalize_grade_for_cache(grade)
            search_key = f"{title.lower().strip()}|{str(issue).strip()}|{normalized_grade}"
        else:
            search_key = f"{title.lower().strip()}|{str(issue).strip()}"
        
        cursor.execute('''
            SELECT estimated_value, confidence, confidence_score, num_sales, 
                   price_min, price_max, sales_data, reasoning, cached_at,
                   quick_sale, fair_value, high_end, lowest_bin,
                   quick_sale_confidence, fair_value_confidence, high_end_confidence
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
                # Get tiered pricing (may be None for old cache entries)
                quick_sale = row[9] if len(row) > 9 and row[9] else row[4]  # fallback to price_min
                fair_value = row[10] if len(row) > 10 and row[10] else row[0]  # fallback to estimated_value
                high_end = row[11] if len(row) > 11 and row[11] else row[5]  # fallback to price_max
                lowest_bin = row[12] if len(row) > 12 else None
                
                # Get tier confidences (fallback to overall confidence for old entries)
                base_conf = row[2] or 50
                quick_sale_conf = row[13] if len(row) > 13 and row[13] else base_conf
                fair_value_conf = row[14] if len(row) > 14 and row[14] else base_conf
                high_end_conf = row[15] if len(row) > 15 and row[15] else base_conf
                
                return EbayValuationResult(
                    estimated_value=row[0],
                    confidence=row[1],
                    confidence_score=row[2],
                    num_sales=row[3],
                    price_range=(row[4], row[5]),
                    recency_weighted_avg=row[0],
                    sales_data=json.loads(row[6]) if row[6] else [],
                    reasoning=f"[CACHED] {row[7]}",
                    quick_sale=quick_sale,
                    fair_value=fair_value,
                    high_end=high_end,
                    lowest_bin=lowest_bin,
                    quick_sale_confidence=quick_sale_conf,
                    fair_value_confidence=fair_value_conf,
                    high_end_confidence=high_end_conf
                )
        return None
    except Exception as e:
        print(f"Cache read error: {e}")
        try:
            conn.close()
        except:
            pass
        return None

def save_to_cache(title: str, issue: str, result: EbayValuationResult, grade: str = None):
    """Save search result to PostgreSQL cache."""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        init_cache_db()
        cursor = conn.cursor()
        
        # Include NORMALIZED grade in cache key if provided (VF+, VF, VF- all map to "VF")
        if grade:
            normalized_grade = normalize_grade_for_cache(grade)
            search_key = f"{title.lower().strip()}|{str(issue).strip()}|{normalized_grade}"
        else:
            search_key = f"{title.lower().strip()}|{str(issue).strip()}"
        
        # Use INSERT ... ON CONFLICT for upsert
        cursor.execute('''
            INSERT INTO search_cache 
            (title, issue, search_key, estimated_value, confidence, confidence_score,
             num_sales, price_min, price_max, sales_data, reasoning, cached_at,
             quick_sale, fair_value, high_end, lowest_bin,
             quick_sale_confidence, fair_value_confidence, high_end_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                cached_at = EXCLUDED.cached_at,
                quick_sale = EXCLUDED.quick_sale,
                fair_value = EXCLUDED.fair_value,
                high_end = EXCLUDED.high_end,
                lowest_bin = EXCLUDED.lowest_bin,
                quick_sale_confidence = EXCLUDED.quick_sale_confidence,
                fair_value_confidence = EXCLUDED.fair_value_confidence,
                high_end_confidence = EXCLUDED.high_end_confidence
        ''', (
            title, issue, search_key, result.estimated_value, result.confidence,
            result.confidence_score, result.num_sales, result.price_range[0],
            result.price_range[1], json.dumps(result.sales_data), result.reasoning,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            result.quick_sale, result.fair_value, result.high_end, result.lowest_bin,
            result.quick_sale_confidence, result.fair_value_confidence, result.high_end_confidence
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Cached: {title} #{issue} = ${result.estimated_value} (Quick: ${result.quick_sale}, Fair: ${result.fair_value}, High: ${result.high_end})")
    except Exception as e:
        print(f"Cache write error: {e}")
        try:
            conn.close()
        except:
            pass

def update_cached_value(title: str, issue: str, new_value: float, samples: list = None, grade: str = None) -> bool:
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
        
        # Include grade in cache key if provided
        if grade:
            search_key = f"{title.lower().strip()}|{str(issue).strip()}|{grade.upper().strip()}"
        else:
            search_key = f"{title.lower().strip()}|{str(issue).strip()}"
        
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

def calculate_tier_confidence(
    base_confidence: int,
    prices: List[float],
    median_price: float,
    has_bin: bool,
    lowest_bin: Optional[float],
    quick_sale: float,
    high_end: float
) -> tuple:
    """
    Calculate separate confidence scores for each pricing tier.
    Returns (quick_sale_confidence, fair_value_confidence, high_end_confidence)
    """
    if not prices or median_price == 0:
        return (25, 25, 25)  # Very low confidence for all if no data
    
    # Fair Value confidence = base confidence (median is most stable)
    fair_value_conf = base_confidence
    
    # Quick Sale confidence
    quick_sale_conf = base_confidence
    if has_bin and lowest_bin:
        # We have current BIN data - high confidence in quick sale price
        quick_sale_conf += 15
    else:
        # Relying on min sold price only
        quick_sale_conf -= 5
        # Check if multiple sales near the min
        min_price = min(prices)
        near_min_count = sum(1 for p in prices if p <= min_price * 1.2)
        if near_min_count >= 2:
            quick_sale_conf += 10  # Multiple sales near floor = more confidence
        elif len(prices) == 1:
            quick_sale_conf -= 10  # Only 1 sale total = less confidence
    
    # High End confidence
    high_end_conf = base_confidence
    max_price = max(prices)
    
    # Check if max is an outlier compared to median
    if median_price > 0:
        ratio = max_price / median_price
        if ratio > 2.0:
            high_end_conf -= 25  # Max is >2x median - likely outlier
        elif ratio > 1.5:
            high_end_conf -= 15  # Max is >1.5x median - possible outlier
        elif ratio <= 1.2:
            high_end_conf += 5   # Max is close to median - consistent data
    
    # Check if multiple sales near the max
    near_max_count = sum(1 for p in prices if p >= max_price * 0.8)
    if near_max_count >= 2:
        high_end_conf += 10  # Multiple high sales = more confidence
    elif near_max_count == 1 and len(prices) > 1:
        high_end_conf -= 10  # Single high sale among others = less confidence
    
    # Clamp all scores
    quick_sale_conf = max(0, min(100, quick_sale_conf))
    fair_value_conf = max(0, min(100, fair_value_conf))
    high_end_conf = max(0, min(100, high_end_conf))
    
    return (quick_sale_conf, fair_value_conf, high_end_conf)

def _single_search(client, title: str, issue: str, grade: str, publisher: str = None, issue_type: str = None, is_signed: bool = False, signer: str = None) -> tuple:
    """
    Run a single search query. Returns (sales_list, corrected_title) or ([], None) on error.
    """
    # Ensure title and issue are strings (not None)
    title = str(title) if title else "Unknown"
    issue = str(issue) if issue else "1"
    
    # Build the full title including issue_type for Annuals, Giant-Size, etc.
    full_title = title
    if issue_type and issue_type.lower() not in ['regular', '']:
        # Add issue_type to the title for searching (e.g., "Amazing Spider-Man Annual")
        full_title = f"{title} {issue_type}"
    
    # Build search query based on whether it's signed or not
    if is_signed:
        # For signed comics, search for signed/autographed copies
        search_query = f"{full_title} #{issue} comic signed autograph"
        if signer:
            search_query += f" {signer}"
        if publisher:
            search_query += f" {publisher}"
        search_query += " price sold value"
        signed_note = f"\n\nIMPORTANT: This is a SIGNED/AUTOGRAPHED copy{f' signed by {signer}' if signer else ''}. Search for signed copies, not raw unsigned copies. Signed comics are worth significantly more than unsigned."
    else:
        # For unsigned comics, exclude CGC/slabs
        search_query = f"{full_title} #{issue} comic raw ungraded"
        if publisher:
            search_query += f" {publisher}"
        search_query += " -CGC -CBCS -slab -graded price sold value"
        signed_note = ""
    
    # Note in prompt if this is an Annual/Special
    issue_type_note = ""
    if issue_type and issue_type.lower() not in ['regular', '']:
        issue_type_note = f"\n\nIMPORTANT: This is a {issue_type} issue, NOT a regular series issue. Search specifically for \"{full_title} #{issue}\" - do NOT confuse with the regular series."
    
    # Build conditional rules based on whether comic is signed
    if is_signed:
        slab_rule = "- CGC/CBCS slabbed copies are OK if they are signed - we want to see signed copy prices"
        signed_rule = "- ONLY include signed/autographed copies - REJECT unsigned copies"
        value_note = f"""- We want SIGNED copies{f' (signed by {signer})' if signer else ''}
- Signed comics typically sell for 2-10x more than unsigned
- If you can't find signed copies, note this and return empty array"""
    else:
        slab_rule = "- **CGC/CBCS SLABS: ALWAYS REJECT** - We are valuing RAW (ungraded) comics ONLY. Slabbed/graded copies sell for 2-10x more and MUST NOT be included. Look for keywords: CGC, CBCS, \"graded\", \"slab\", \"9.8\", \"9.6\" with a grade label. If a price seems unusually high ($200+ for a common comic), verify it's not a slab."
        signed_rule = "- REJECT signed copies, variant covers, or special editions unless specifically requested"
        value_note = """- We want RAW/UNGRADED comics ONLY - never include CGC/CBCS slab prices
- For RAW comics, typical values are $2-100 for most issues, $100-500 for key issues
- If you accidentally find only CGC prices, return an empty sales array - do NOT estimate from slab prices"""
    
    prompt = f"""Find the market value for: {full_title} #{issue} in {grade} condition{signed_note}{issue_type_note}

STEP 1 - CORRECT SPELLING: Fix any errors (e.g., "Captian America" → "Captain America", "Spiderman" → "Spider-Man")

STEP 2 - SEARCH PRICECHARTING FIRST: Search "site:pricecharting.com {full_title} #{issue}" to find the exact issue page. PriceCharting has the most reliable ungraded/raw comic prices.

STEP 3 - CHECK EBAY SOLD LISTINGS: Search eBay sold/completed listings for recent actual sales.

STEP 4 - CHECK CURRENT BUY IT NOW: Also search eBay for current Buy It Now listings to see what's available now. This helps establish a price ceiling.

CRITICAL MATCHING RULES - REJECT prices that don't match EXACTLY:
- Title must match EXACTLY (e.g., "Captain America Annual #8" is NOT "Captain America #8")
- "Annual", "Giant-Size", "Special", "King-Size Special" are DIFFERENT series - don't mix them with regular issues
- Issue number must match EXACTLY
- REJECT lot sales (multiple comics sold together)
{slab_rule}
{signed_rule}

GRADE ESTIMATION - For each sale/listing, estimate the condition:
- If listing says "NM", "Near Mint", "9.4" → grade: "NM"
- If listing says "VF", "Very Fine", "8.0" → grade: "VF"  
- If listing says "FN", "Fine", "6.0" → grade: "FN"
- If listing says "VG", "Very Good", "4.0" → grade: "VG"
- If listing says "G", "Good", "2.0" → grade: "G"
- If no condition specified, estimate from photos/description or use "raw" (assumes FN)

Return JSON:
{{
    "sales": [
        {{"price": 25.00, "date": "2026-01-10", "grade": "VF", "source": "eBay sold"}},
        {{"price": 30.00, "date": "2025-12-15", "grade": "FN", "source": "PriceCharting"}}
    ],
    "buy_it_now": [
        {{"price": 22.00, "grade": "VF", "source": "eBay BIN"}},
        {{"price": 35.00, "grade": "NM", "source": "eBay BIN"}}
    ],
    "corrected_title": "Captain America Annual",
    "notes": "Brief notes"
}}

IMPORTANT:
- "sales" = SOLD/COMPLETED listings only (actual transactions)
- "buy_it_now" = CURRENT active listings (asking prices)
{value_note}
- Maximum 10 items per array, USD only
- Use standard grade abbreviations: MT, NM, VF, FN, VG, G, FR, PR (or "raw" if unknown)"""

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
            if hasattr(block, 'text') and block.text:
                result_text += block.text
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            data = json.loads(json_match.group())
            sales = data.get('sales', [])
            buy_it_now = data.get('buy_it_now', [])
            corrected_title = data.get('corrected_title', None)
            return (sales, buy_it_now, corrected_title)
        
    except Exception as e:
        print(f"Search error: {e}")
    
    return ([], [], None)


def search_ebay_sold(title: str, issue: str, grade: str, publisher: str = None, issue_type: str = None, num_samples: int = 3, force_refresh: bool = False, is_signed: bool = False, signer: str = None) -> EbayValuationResult:
    """
    Search for market prices using Claude AI with web search.
    Runs multiple samples and takes median for accuracy.
    Checks cache first, saves successful results to cache.
    
    Args:
        title: Comic title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "6")
        grade: Grade (e.g., "VF")
        publisher: Optional publisher
        issue_type: "Regular", "Annual", "Giant-Size", "Special", etc.
        num_samples: Number of search samples to run
        force_refresh: Bypass cache
        is_signed: Whether comic is signed/autographed
        signer: Name of signer (e.g., "Stan Lee")
    """
    # Expand aliases (ASM → Amazing Spider-Man)
    title = expand_title_alias(title)
    
    # Build cache key that includes issue_type for Annuals, etc. and signed status
    cache_title = title
    if issue_type and issue_type.lower() not in ['regular', '']:
        cache_title = f"{title} {issue_type}"
    if is_signed:
        cache_title = f"{cache_title} SIGNED"
        if signer:
            cache_title = f"{cache_title} {signer}"
    
    # Check cache first (unless force_refresh)
    if not force_refresh:
        cached = get_cached_result(cache_title, issue, grade)
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
            reasoning="No API key configured for web search",
            quick_sale_confidence=0,
            fair_value_confidence=0,
            high_end_confidence=0
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Run multiple searches for better accuracy
    all_sales = []
    all_bin_listings = []
    corrected_title = None
    
    for i in range(num_samples):
        sales, bin_listings, title_fix = _single_search(client, title, issue, grade, publisher, issue_type, is_signed, signer)
        all_sales.extend(sales)
        all_bin_listings.extend(bin_listings)
        if title_fix and not corrected_title:
            corrected_title = title_fix
    
    # Deduplicate sales by price+date+source
    seen = set()
    sales = []
    for sale in all_sales:
        key = f"{sale.get('price')}-{sale.get('date')}-{sale.get('source')}"
        if key not in seen:
            seen.add(key)
            sales.append(sale)
    
    # Deduplicate BIN by price+grade+source
    seen_bin = set()
    bin_listings = []
    for item in all_bin_listings:
        key = f"{item.get('price')}-{item.get('grade')}-{item.get('source')}"
        if key not in seen_bin:
            seen_bin.add(key)
            bin_listings.append(item)
    
    # Filter by grade compatibility (±1 grade level from requested grade)
    total_before_grade_filter = len(sales)
    grade_filtered_sales = []
    grade_rejected = []
    
    for sale in sales:
        sale_grade = sale.get('grade', 'raw')
        if is_grade_compatible(sale_grade, grade, tolerance=1.0):
            grade_filtered_sales.append(sale)
        else:
            grade_rejected.append(f"${sale.get('price')} ({sale_grade})")
    
    # Use grade-filtered sales if we have enough, otherwise fall back to all sales
    if len(grade_filtered_sales) >= 2:
        sales = grade_filtered_sales
        grade_filter_note = f"Filtered to {len(sales)}/{total_before_grade_filter} sales matching {grade} (±0.5 grade)."
        if grade_rejected:
            grade_filter_note += f" Excluded: {', '.join(grade_rejected[:3])}"
            if len(grade_rejected) > 3:
                grade_filter_note += f" and {len(grade_rejected)-3} more."
    else:
        grade_filter_note = f"Using all {len(sales)} sales (not enough {grade}-specific matches)."
    
    # Filter BIN listings by grade too
    grade_filtered_bin = []
    for item in bin_listings:
        item_grade = item.get('grade', 'raw')
        if is_grade_compatible(item_grade, grade, tolerance=1.0):
            grade_filtered_bin.append(item)
    
    # Calculate lowest BIN price (grade-filtered if available, else all)
    lowest_bin = None
    bin_prices = []
    for item in (grade_filtered_bin if grade_filtered_bin else bin_listings):
        try:
            price = float(item.get('price', 0))
            if price > 0:
                bin_prices.append(price)
        except:
            continue
    if bin_prices:
        lowest_bin = min(bin_prices)
    
    if not sales:
        return EbayValuationResult(
            estimated_value=0,
            confidence="VERY LOW",
            confidence_score=0,
            num_sales=0,
            price_range=(0, 0),
            recency_weighted_avg=0,
            sales_data=[],
            reasoning="No market prices found from web search",
            quick_sale_confidence=0,
            fair_value_confidence=0,
            high_end_confidence=0
        )
    
    # Process sales data
    processed_sales = []
    prices = []
    weighted_sum = 0
    weight_total = 0
    
    # First pass: extract all prices for outlier detection
    raw_prices = []
    for sale in sales:
        try:
            price = float(sale.get('price', 0))
            if price > 0:
                raw_prices.append(price)
        except:
            continue
    
    # Outlier filtering using IQR method (if we have enough data)
    outlier_threshold_low = 0
    outlier_threshold_high = float('inf')
    
    if len(raw_prices) >= 4:
        sorted_prices = sorted(raw_prices)
        q1_idx = len(sorted_prices) // 4
        q3_idx = (3 * len(sorted_prices)) // 4
        q1 = sorted_prices[q1_idx]
        q3 = sorted_prices[q3_idx]
        iqr = q3 - q1
        outlier_threshold_low = max(0, q1 - 1.5 * iqr)
        outlier_threshold_high = q3 + 1.5 * iqr
    elif len(raw_prices) >= 2:
        # For small samples, reject if price is >5x the minimum (likely CGC or wrong issue)
        min_price = min(raw_prices)
        outlier_threshold_high = min_price * 5
    
    for sale in sales:
        try:
            price = float(sale.get('price', 0))
            
            # Skip outliers
            if price < outlier_threshold_low or price > outlier_threshold_high:
                print(f"Outlier filtered: ${price} (thresholds: ${outlier_threshold_low:.2f}-${outlier_threshold_high:.2f})")
                continue
            
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
            reasoning="Could not parse sales data",
            quick_sale_confidence=0,
            fair_value_confidence=0,
            high_end_confidence=0
        )
    
    # Calculate statistics
    recency_weighted_avg = weighted_sum / weight_total if weight_total > 0 else 0
    price_min = min(prices)
    price_max = max(prices)
    price_mean = sum(prices) / len(prices)
    
    # Calculate median for fair value
    sorted_prices = sorted(prices)
    if len(sorted_prices) % 2 == 0:
        median_price = (sorted_prices[len(sorted_prices)//2 - 1] + sorted_prices[len(sorted_prices)//2]) / 2
    else:
        median_price = sorted_prices[len(sorted_prices)//2]
    
    # Calculate tiered pricing
    # Quick Sale: lowest BIN if available, otherwise lowest sold price
    quick_sale = lowest_bin if lowest_bin else price_min
    # Fair Value: median of sold prices (more stable than mean)
    fair_value = median_price
    # High End: highest recent sold price
    high_end = price_max
    
    # Sanity check: quick_sale shouldn't be higher than fair_value
    if quick_sale > fair_value:
        quick_sale = price_min  # Fall back to lowest sold
    
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
    
    # Calculate per-tier confidence
    quick_sale_conf, fair_value_conf, high_end_conf = calculate_tier_confidence(
        base_confidence=confidence_score,
        prices=prices,
        median_price=median_price,
        has_bin=lowest_bin is not None,
        lowest_bin=lowest_bin,
        quick_sale=quick_sale,
        high_end=high_end
    )
    
    # Build reasoning
    reasoning_parts = [
        f"Found {len(prices)} price(s) from 3-sample search",
        f"Price range: ${price_min:.2f} - ${price_max:.2f}",
        f"Recency-weighted average: ${recency_weighted_avg:.2f}"
    ]
    
    # Add spelling correction note if title was corrected
    if corrected_title and corrected_title.lower() != title.lower():
        reasoning_parts.insert(0, f"Corrected spelling: '{title}' → '{corrected_title}'")
    
    # Add grade filtering note
    reasoning_parts.append(grade_filter_note)
    
    if cv < 0.1:
        reasoning_parts.append("Prices very consistent")
    elif cv > 0.5:
        reasoning_parts.append("⚠️ Prices vary significantly - value may be unreliable")
    elif cv > 0.3:
        reasoning_parts.append("Prices show moderate variation")
    
    # Warn if we filtered outliers
    if outlier_threshold_high < float('inf') and len(raw_prices) > len(prices):
        filtered_count = len(raw_prices) - len(prices)
        reasoning_parts.append(f"Filtered {filtered_count} outlier(s)")
    
    result = EbayValuationResult(
        estimated_value=round(recency_weighted_avg, 2),
        confidence=confidence_label,
        confidence_score=confidence_score,
        num_sales=len(prices),
        price_range=(price_min, price_max),
        recency_weighted_avg=round(recency_weighted_avg, 2),
        sales_data=processed_sales,
        reasoning=". ".join(reasoning_parts),
        quick_sale=round(quick_sale, 2),
        fair_value=round(fair_value, 2),
        high_end=round(high_end, 2),
        lowest_bin=round(lowest_bin, 2) if lowest_bin else None,
        quick_sale_confidence=quick_sale_conf,
        fair_value_confidence=fair_value_conf,
        high_end_confidence=high_end_conf
    )
    
    # Save to cache for future requests (use cache_title which includes issue_type, and grade)
    save_to_cache(cache_title, issue, result, grade)
    
    return result


def get_valuation_with_ebay(title: str, issue: str, grade: str, 
                            publisher: str = None, year: int = None,
                            db_result: dict = None, force_refresh: bool = False,
                            issue_type: str = None, is_signed: bool = False,
                            signer: str = None) -> dict:
    """
    Main valuation function that combines database and eBay data.
    Set force_refresh=True to bypass cache and get fresh eBay data.
    
    Args:
        title: Comic title
        issue: Issue number
        grade: Grade (e.g., "VF")
        publisher: Optional publisher
        year: Optional year
        db_result: Optional database lookup result
        force_refresh: Bypass cache
        issue_type: "Regular", "Annual", "Giant-Size", "Special", etc.
        is_signed: Whether comic is signed/autographed
        signer: Name of signer (e.g., "Stan Lee")
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
        ebay_result = search_ebay_sold(title, issue, grade, publisher, issue_type=issue_type, force_refresh=force_refresh, is_signed=is_signed, signer=signer)
        
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
            'quick_sale': ebay_result.quick_sale if ebay_result.num_sales > 0 else round(final_value * 0.7, 2),
            'fair_value': ebay_result.fair_value if ebay_result.num_sales > 0 else round(final_value, 2),
            'high_end': ebay_result.high_end if ebay_result.num_sales > 0 else round(final_value * 1.3, 2),
            'lowest_bin': ebay_result.lowest_bin,
            'quick_sale_confidence': ebay_result.quick_sale_confidence if ebay_result.num_sales > 0 else 30,
            'fair_value_confidence': ebay_result.fair_value_confidence if ebay_result.num_sales > 0 else 50,
            'high_end_confidence': ebay_result.high_end_confidence if ebay_result.num_sales > 0 else 30,
            'debug': {
                'ebay_attempted': True,
                'ebay_reasoning': ebay_result.reasoning,
                'db_base_value': base_value,
                'title_expanded': title if title != original_title else None
            }
        }
    
    else:
        # Not in database - rely on eBay
        ebay_result = search_ebay_sold(title, issue, grade, publisher, issue_type=issue_type, force_refresh=force_refresh, is_signed=is_signed, signer=signer)
        
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
                'quick_sale': ebay_result.quick_sale,
                'fair_value': ebay_result.fair_value,
                'high_end': ebay_result.high_end,
                'lowest_bin': ebay_result.lowest_bin,
                'quick_sale_confidence': ebay_result.quick_sale_confidence,
                'fair_value_confidence': ebay_result.fair_value_confidence,
                'high_end_confidence': ebay_result.high_end_confidence,
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
                'quick_sale': round(result.final_value * 0.7, 2),
                'fair_value': round(result.final_value, 2),
                'high_end': round(result.final_value * 1.3, 2),
                'lowest_bin': None,
                'quick_sale_confidence': 15,
                'fair_value_confidence': 20,
                'high_end_confidence': 15,
                'debug': {
                    'ebay_attempted': True,
                    'ebay_reasoning': 'No results found',
                    'db_base_value': None,
                    'title_expanded': title if title != original_title else None
                }
            }
