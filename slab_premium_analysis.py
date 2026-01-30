"""
Slab Premium Analysis Script
Analyzes eBay sold data to calculate CGC slab premium across value tiers.

Run locally or on Render with: python slab_premium_analysis.py

Output: CSV with raw vs slabbed prices and calculated premiums
"""

import os
import json
import time
import statistics
from datetime import datetime
import requests

# eBay API credentials - uses same env vars as main app
EBAY_APP_ID = os.environ.get('EBAY_APP_ID')

# Comics to analyze across value ranges
# Format: (title, issue, grades_to_check)
COMICS_TO_ANALYZE = [
    # $5-25 raw value range (common moderns, 90s books)
    ("Spawn", "1", ["9.0", "9.2"]),
    ("X-Men", "1", ["9.0", "9.2"]),  # 1991 Jim Lee
    ("Spider-Man", "1", ["9.4", "9.6"]),  # 1990 McFarlane
    ("Venom Lethal Protector", "1", ["9.4", "9.6"]),
    ("Deadpool", "1", ["9.0", "9.2"]),  # 1997 series
    ("Batman", "497", ["9.4", "9.6"]),  # Bane breaks back
    ("Superman", "75", ["9.4", "9.6"]),  # Death of Superman
    ("X-Force", "1", ["9.6", "9.8"]),
    
    # $25-75 raw value range
    ("New Mutants", "98", ["7.0", "8.0"]),  # First Deadpool
    ("Amazing Spider-Man", "361", ["9.4", "9.6"]),  # First Carnage
    ("Batman Adventures", "12", ["6.0", "7.0"]),  # First Harley
    ("Incredible Hulk", "340", ["9.4", "9.6"]),  # Hulk vs Wolverine
    ("Wolverine", "1", ["9.4", "9.6"]),  # 1988 ongoing
    ("Uncanny X-Men", "266", ["9.0", "9.2"]),  # First Gambit
    ("New Mutants", "87", ["9.0", "9.2"]),  # First Cable
    
    # $75-150 raw value range
    ("Amazing Spider-Man", "300", ["6.0", "7.0"]),  # First Venom
    ("New Mutants", "98", ["9.0", "9.2"]),  # First Deadpool
    ("Batman Adventures", "12", ["8.0", "8.5"]),  # First Harley
    ("Teenage Mutant Ninja Turtles", "1", ["6.0", "7.0"]),  # 2nd/3rd print
    ("Walking Dead", "1", ["8.0", "8.5"]),
    ("Invincible", "1", ["9.0", "9.2"]),
    
    # $150-300 raw value range
    ("Amazing Spider-Man", "300", ["8.0", "8.5"]),
    ("Incredible Hulk", "181", ["4.0", "5.0"]),  # First Wolverine
    ("New Mutants", "98", ["9.6", "9.8"]),
    ("Batman Adventures", "12", ["9.2", "9.4"]),
    ("Giant-Size X-Men", "1", ["3.0", "4.0"]),
    ("Amazing Spider-Man", "129", ["5.0", "6.0"]),  # First Punisher
    
    # $300-750 raw value range
    ("Amazing Spider-Man", "300", ["9.4", "9.6"]),
    ("Incredible Hulk", "181", ["5.5", "6.5"]),
    ("Giant-Size X-Men", "1", ["5.0", "6.0"]),
    ("Amazing Spider-Man", "129", ["7.0", "8.0"]),
    ("X-Men", "94", ["6.0", "7.0"]),
    ("Werewolf By Night", "32", ["6.0", "7.0"]),  # First Moon Knight
    
    # $750-1500 raw value range
    ("Amazing Spider-Man", "300", ["9.8"]),
    ("Incredible Hulk", "181", ["7.0", "7.5"]),
    ("Giant-Size X-Men", "1", ["7.0", "8.0"]),
    ("Amazing Spider-Man", "129", ["9.0", "9.2"]),
    ("X-Men", "94", ["8.0", "8.5"]),
    ("Iron Man", "55", ["8.0", "8.5"]),  # First Thanos
    
    # $1500-5000 raw value range
    ("Incredible Hulk", "181", ["8.0", "8.5"]),
    ("Giant-Size X-Men", "1", ["9.0", "9.2"]),
    ("Amazing Spider-Man", "129", ["9.4", "9.6"]),
    ("X-Men", "1", ["4.0", "5.0"]),  # 1963 Silver Age
    ("Fantastic Four", "48", ["7.0", "8.0"]),  # First Silver Surfer
    ("Avengers", "1", ["3.0", "4.0"]),
    
    # $5000+ raw value range
    ("Incredible Hulk", "181", ["9.4", "9.6"]),
    ("Amazing Fantasy", "15", ["2.0", "3.0"]),  # First Spider-Man
    ("X-Men", "1", ["6.0", "7.0"]),  # 1963
    ("Fantastic Four", "1", ["2.0", "3.0"]),
    ("Amazing Spider-Man", "1", ["4.0", "5.0"]),
    ("Tales of Suspense", "39", ["4.0", "5.0"]),  # First Iron Man
]


def search_ebay_sold(query, limit=20):
    """Search eBay sold listings using Finding API"""
    if not EBAY_APP_ID:
        print("ERROR: EBAY_APP_ID not set")
        return []
    
    url = "https://svcs.ebay.com/services/search/FindingService/v1"
    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.0.0",
        "SECURITY-APPNAME": EBAY_APP_ID,
        "RESPONSE-DATA-FORMAT": "JSON",
        "REST-PAYLOAD": "true",
        "keywords": query,
        "categoryId": "259104",  # Collectible Comics
        "itemFilter(0).name": "SoldItemsOnly",
        "itemFilter(0).value": "true",
        "sortOrder": "EndTimeSoonest",
        "paginationInput.entriesPerPage": str(limit)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        items = data.get("findCompletedItemsResponse", [{}])[0] \
                    .get("searchResult", [{}])[0] \
                    .get("item", [])
        
        prices = []
        for item in items:
            try:
                price = float(item["sellingStatus"][0]["currentPrice"][0]["__value__"])
                title = item["title"][0].lower()
                prices.append({"price": price, "title": title})
            except (KeyError, IndexError, ValueError):
                continue
        
        return prices
    
    except Exception as e:
        print(f"  Error searching eBay: {e}")
        return []


def analyze_comic(title, issue, grade):
    """Compare raw vs CGC prices for a specific comic/grade"""
    print(f"\n  Analyzing: {title} #{issue} grade {grade}")
    
    # Search for raw copies
    raw_query = f"{title} {issue} {grade} raw -cgc -cbcs -pgx -signed"
    raw_results = search_ebay_sold(raw_query, limit=15)
    
    # Filter out obvious non-matches and slabs that slipped through
    raw_prices = []
    for r in raw_results:
        t = r["title"]
        if "cgc" not in t and "cbcs" not in t and "pgx" not in t and "slab" not in t:
            raw_prices.append(r["price"])
    
    time.sleep(0.5)  # Rate limiting
    
    # Search for CGC slabbed copies
    cgc_query = f"{title} {issue} CGC {grade}"
    cgc_results = search_ebay_sold(cgc_query, limit=15)
    
    # Filter for actual CGC slabs
    cgc_prices = []
    for r in cgc_results:
        t = r["title"]
        if "cgc" in t and "signed" not in t and "ss" not in t and "signature" not in t:
            cgc_prices.append(r["price"])
    
    time.sleep(0.5)  # Rate limiting
    
    # Calculate stats
    result = {
        "title": title,
        "issue": issue,
        "grade": grade,
        "raw_count": len(raw_prices),
        "cgc_count": len(cgc_prices),
        "raw_median": None,
        "cgc_median": None,
        "premium": None
    }
    
    if len(raw_prices) >= 3:
        result["raw_median"] = statistics.median(raw_prices)
        result["raw_avg"] = statistics.mean(raw_prices)
        result["raw_min"] = min(raw_prices)
        result["raw_max"] = max(raw_prices)
    
    if len(cgc_prices) >= 3:
        result["cgc_median"] = statistics.median(cgc_prices)
        result["cgc_avg"] = statistics.mean(cgc_prices)
        result["cgc_min"] = min(cgc_prices)
        result["cgc_max"] = max(cgc_prices)
    
    if result["raw_median"] and result["cgc_median"] and result["raw_median"] > 0:
        result["premium"] = result["cgc_median"] / result["raw_median"]
    
    print(f"    Raw: {len(raw_prices)} sales, median ${result['raw_median']:.2f}" if result["raw_median"] else f"    Raw: {len(raw_prices)} sales (insufficient data)")
    print(f"    CGC: {len(cgc_prices)} sales, median ${result['cgc_median']:.2f}" if result["cgc_median"] else f"    CGC: {len(cgc_prices)} sales (insufficient data)")
    if result["premium"]:
        print(f"    Premium: {result['premium']:.2f}x ({(result['premium']-1)*100:.0f}%)")
    
    return result


def calculate_tier_premiums(results):
    """Group results by raw value tier and calculate average premiums"""
    
    # Define tiers
    tiers = [
        (0, 15, "$0-15"),
        (15, 30, "$15-30"),
        (30, 50, "$30-50"),
        (50, 75, "$50-75"),
        (75, 100, "$75-100"),
        (100, 150, "$100-150"),
        (150, 200, "$150-200"),
        (200, 300, "$200-300"),
        (300, 400, "$300-400"),
        (400, 500, "$400-500"),
        (500, 750, "$500-750"),
        (750, 1000, "$750-1000"),
        (1000, 1500, "$1000-1500"),
        (1500, 2000, "$1500-2000"),
        (2000, 3000, "$2000-3000"),
        (3000, 5000, "$3000-5000"),
        (5000, 7500, "$5000-7500"),
        (7500, 10000, "$7500-10000"),
        (10000, 25000, "$10000-25000"),
        (25000, float('inf'), "$25000+"),
    ]
    
    tier_data = {label: [] for _, _, label in tiers}
    
    # Group results into tiers
    for r in results:
        if r["raw_median"] and r["premium"]:
            raw_val = r["raw_median"]
            for low, high, label in tiers:
                if low <= raw_val < high:
                    tier_data[label].append(r["premium"])
                    break
    
    # Calculate averages
    tier_premiums = []
    for low, high, label in tiers:
        premiums = tier_data[label]
        if premiums:
            avg = statistics.mean(premiums)
            tier_premiums.append({
                "range": label,
                "low": low,
                "high": high,
                "sample_size": len(premiums),
                "avg_premium": avg,
                "min_premium": min(premiums),
                "max_premium": max(premiums)
            })
        else:
            tier_premiums.append({
                "range": label,
                "low": low,
                "high": high,
                "sample_size": 0,
                "avg_premium": None,
                "min_premium": None,
                "max_premium": None
            })
    
    return tier_premiums


def generate_js_function(tier_premiums):
    """Generate JavaScript function for grading.js"""
    
    # Build tier array for JS
    js_tiers = []
    last_premium = 3.0  # Default for lowest tier if no data
    
    for t in tier_premiums:
        if t["avg_premium"]:
            premium = round(t["avg_premium"], 2)
            last_premium = premium
        else:
            premium = last_premium  # Carry forward if no data
        
        if t["high"] == float('inf'):
            js_tiers.append(f"        {{ max: Infinity, premium: {premium} }}")
        else:
            js_tiers.append(f"        {{ max: {t['high']}, premium: {premium} }}")
    
    js_code = f"""
// Slab Premium Calculator - Generated {datetime.now().strftime('%Y-%m-%d')}
// Based on eBay sold data analysis
function getSlabPremium(rawValue) {{
    const tiers = [
{chr(10).join(js_tiers)}
    ];
    
    // Find tier and interpolate
    let prevTier = {{ max: 0, premium: {tier_premiums[0]['avg_premium'] or 3.0} }};
    for (const tier of tiers) {{
        if (rawValue <= tier.max) {{
            const range = tier.max - prevTier.max;
            const position = (rawValue - prevTier.max) / range;
            return prevTier.premium - (prevTier.premium - tier.premium) * position;
        }}
        prevTier = tier;
    }}
    return tiers[tiers.length - 1].premium;
}}
"""
    return js_code


def main():
    print("=" * 60)
    print("SLAB PREMIUM ANALYSIS")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Comics to analyze: {len(COMICS_TO_ANALYZE)}")
    print()
    
    if not EBAY_APP_ID:
        print("ERROR: EBAY_APP_ID environment variable not set!")
        print("Set it and run again.")
        return
    
    all_results = []
    
    for title, issue, grades in COMICS_TO_ANALYZE:
        print(f"\n{'='*40}")
        print(f"{title} #{issue}")
        print("=" * 40)
        
        for grade in grades:
            result = analyze_comic(title, issue, grade)
            all_results.append(result)
            time.sleep(1)  # Rate limiting between comics
    
    # Filter to only valid results
    valid_results = [r for r in all_results if r["premium"] is not None]
    
    print("\n" + "=" * 60)
    print("TIER ANALYSIS")
    print("=" * 60)
    
    tier_premiums = calculate_tier_premiums(valid_results)
    
    for t in tier_premiums:
        if t["sample_size"] > 0:
            print(f"{t['range']:15} | n={t['sample_size']:2} | avg={t['avg_premium']:.2f}x | range={t['min_premium']:.2f}-{t['max_premium']:.2f}x")
        else:
            print(f"{t['range']:15} | n=0  | (no data)")
    
    # Generate output files
    print("\n" + "=" * 60)
    print("GENERATING OUTPUT FILES")
    print("=" * 60)
    
    # Save raw data as JSON
    with open("slab_premium_data.json", "w") as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "results": all_results,
            "tiers": tier_premiums
        }, f, indent=2, default=str)
    print("Saved: slab_premium_data.json")
    
    # Save tier summary as CSV
    with open("slab_premium_tiers.csv", "w") as f:
        f.write("range,low,high,sample_size,avg_premium,min_premium,max_premium\n")
        for t in tier_premiums:
            f.write(f"{t['range']},{t['low']},{t['high']},{t['sample_size']},{t['avg_premium'] or ''},{t['min_premium'] or ''},{t['max_premium'] or ''}\n")
    print("Saved: slab_premium_tiers.csv")
    
    # Generate JS function
    js_code = generate_js_function(tier_premiums)
    with open("slab_premium_function.js", "w") as f:
        f.write(js_code)
    print("Saved: slab_premium_function.js")
    
    print("\n" + "=" * 60)
    print("GENERATED JAVASCRIPT FUNCTION")
    print("=" * 60)
    print(js_code)
    
    print("\n" + "=" * 60)
    print(f"COMPLETE - {len(valid_results)} valid data points collected")
    print("=" * 60)


if __name__ == "__main__":
    main()
