"""
eBay-Powered Valuation Module
Searches eBay sold listings and applies recency/volume weighting.
"""

import os
import json
import re
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
    Search eBay sold listings using Claude AI with web search.
    """
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
            reasoning="No API key configured for eBay search"
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Build search query
    search_query = f"{title} #{issue}"
    if publisher:
        search_query += f" {publisher}"
    search_query += f" {grade} sold eBay"
    
    prompt = f"""Search eBay sold listings for: {search_query}

Find recent SOLD prices (not current listings) for this comic book.

Return a JSON object with this exact structure:
{{
    "sales": [
        {{"price": 45.00, "date": "2026-01-10", "grade": "VF", "is_cgc": false}},
        {{"price": 52.00, "date": "2025-12-15", "grade": "VF", "is_cgc": true}}
    ],
    "notes": "Brief notes about the search results"
}}

Rules:
- Only include SOLD listings, not active listings
- Include date sold if available (estimate if only "sold in last month" etc)
- Note if the listing was CGC graded
- If no sold listings found, return empty sales array
- Maximum 10 most recent sales
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
            reasoning="No sold listings found on eBay"
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
                'is_cgc': sale.get('is_cgc', False)
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
    
    return EbayValuationResult(
        estimated_value=round(recency_weighted_avg, 2),
        confidence=confidence_label,
        confidence_score=confidence_score,
        num_sales=len(prices),
        price_range=(price_min, price_max),
        recency_weighted_avg=round(recency_weighted_avg, 2),
        sales_data=processed_sales,
        reasoning=". ".join(reasoning_parts)
    )


def get_valuation_with_ebay(title: str, issue: str, grade: str, 
                            publisher: str = None, year: int = None,
                            db_result: dict = None) -> dict:
    """
    Main valuation function that combines database and eBay data.
    """
    from valuation_model import ValuationModel
    
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
                'db_base_value': base_value
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
                'sales_data': ebay_result.sales_data
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
                'sales_data': []
            }
