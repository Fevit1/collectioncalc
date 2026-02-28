"""
Test script for the Signature Matcher system.

Run after deploying routes/signatures.py to production.

Usage:
    # 1. First, check how many signed sales we have in the DB
    python test_signature_matcher.py --check-signed-sales

    # 2. Test the db-stats endpoint (no auth needed)
    python test_signature_matcher.py --db-stats

    # 3. Test matching with a known artist signature from our reference DB
    #    (requires auth token — get from browser dev tools)
    python test_signature_matcher.py --test-known "Jim Lee" --token YOUR_TOKEN

    # 4. Cross-validate: test each artist's sig against all others
    python test_signature_matcher.py --cross-validate --token YOUR_TOKEN

    # 5. Test against real eBay signed comic images
    python test_signature_matcher.py --test-ebay --token YOUR_TOKEN
"""

import os
import sys
import json
import base64
import argparse
import random
import time
from pathlib import Path

# Try requests, fall back to urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

API_BASE = "https://collectioncalc-docker.onrender.com"
SIGNATURES_DIR = Path(__file__).parent / "signatures"
DB_PATH = SIGNATURES_DIR / "signatures_db.json"


def api_get(path, token=None):
    """GET request to API."""
    url = f"{API_BASE}{path}"
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    if HAS_REQUESTS:
        r = requests.get(url, headers=headers, timeout=30)
        try:
            return r.json(), r.status_code
        except Exception:
            return {"error": f"Non-JSON response (HTTP {r.status_code}): {r.text[:200]}"}, r.status_code
    else:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read()), resp.status
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read()), e.code
            except Exception:
                return {"error": f"Non-JSON error response (HTTP {e.code})"}, e.code


def api_post(path, data, token=None):
    """POST request to API."""
    url = f"{API_BASE}{path}"
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    body = json.dumps(data).encode('utf-8')

    if HAS_REQUESTS:
        r = requests.post(url, json=data, headers=headers, timeout=60)
        try:
            return r.json(), r.status_code
        except Exception:
            return {"error": f"Non-JSON response (HTTP {r.status_code}): {r.text[:200]}"}, r.status_code
    else:
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read()), resp.status
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read()), e.code
            except Exception:
                return {"error": f"Non-JSON error response (HTTP {e.code})"}, e.code


def load_db():
    with open(DB_PATH, 'r') as f:
        return json.load(f)


def image_to_base64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_media_type(filename):
    ext = filename.lower().split('.')[-1]
    return {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}.get(ext, 'image/jpeg')


# -------------------------------------------------------------------
# Test 1: Check signed sales in DB
# -------------------------------------------------------------------
def check_signed_sales():
    print("Checking signed sales on production...")
    print("─" * 60)

    data, status = api_get("/api/signatures/signed-sales?limit=5")

    if status != 200:
        print(f"❌ Error ({status}): {data}")
        return

    print(f"Total signed sales: {data.get('total_signed', '?')}")
    print(f"Returned: {data.get('returned', 0)}")

    if data.get('creator_breakdown'):
        print(f"\nCreator breakdown (top 15):")
        for cb in data['creator_breakdown'][:15]:
            print(f"  {cb['creators']}: {cb['count']} sales")

    if data.get('sales'):
        print(f"\nSample signed sales:")
        for s in data['sales'][:5]:
            print(f"  ${s.get('sale_price', '?')} — {s.get('raw_title', '?')[:80]}")
            if s.get('creators'):
                print(f"    Creator: {s['creators']}")
            if s.get('image_url'):
                print(f"    Image: ✅ available")


# -------------------------------------------------------------------
# Test 2: DB stats endpoint
# -------------------------------------------------------------------
def check_db_stats():
    print("Checking signature database stats...")
    print("─" * 60)

    data, status = api_get("/api/signatures/db-stats")

    if status != 200:
        print(f"❌ Error ({status}): {data}")
        return

    print(f"Version: {data.get('version')}")
    print(f"Artists: {data.get('total_artists')}")
    print(f"Images:  {data.get('total_images')}")
    print(f"Quality: {json.dumps(data.get('quality_breakdown', {}))}")

    if data.get('missing_priority'):
        print(f"\nMissing priority artists:")
        for m in data['missing_priority']:
            print(f"  ⚠️  {m['name']} — {m['reason']}")


# -------------------------------------------------------------------
# Test 3: Match a known artist (from our reference DB)
# -------------------------------------------------------------------
def test_known_artist(artist_name, token):
    db = load_db()

    artist = None
    for a in db["artists"]:
        if a["name"].lower() == artist_name.lower():
            artist = a
            break

    if not artist:
        print(f"❌ Artist '{artist_name}' not found in database")
        print(f"Available: {', '.join(a['name'] for a in db['artists'])}")
        return

    # Pick a random image
    test_image = random.choice(artist["images"])
    test_path = SIGNATURES_DIR / test_image

    if not test_path.exists():
        print(f"❌ Image not found: {test_path}")
        return

    print(f"Testing: {artist['name']}")
    print(f"Image:   {test_image}")
    print("─" * 60)

    img_b64 = image_to_base64(test_path)
    media_type = get_media_type(test_image)

    print("Calling /api/signatures/match...")
    start = time.time()

    data, status = api_post("/api/signatures/match", {
        "image": img_b64,
        "media_type": media_type
    }, token=token)

    elapsed = time.time() - start
    print(f"Response in {elapsed:.1f}s (status {status})")

    if status != 200:
        print(f"❌ Error: {data}")
        return

    # Evaluate result
    best = data.get("best_match", "UNKNOWN")
    conf = data.get("best_confidence", 0)
    correct = best.lower().strip() == artist["name"].lower().strip()

    status_icon = "✅" if correct else "❌"
    print(f"\n{status_icon} Result:")
    print(f"  Best match:  {best}")
    print(f"  Confidence:  {conf}")
    print(f"  Correct:     {'YES' if correct else 'NO (expected ' + artist['name'] + ')'}")

    if data.get("matches"):
        print(f"\n  Top matches:")
        for m in data["matches"]:
            print(f"    {m['artist']}: {m['confidence']} — {m.get('reasoning', '')[:100]}")

    if data.get("notes"):
        print(f"\n  Notes: {data['notes']}")

    return correct, conf


# -------------------------------------------------------------------
# Test 4: Cross-validate all artists
# -------------------------------------------------------------------
def cross_validate(token):
    db = load_db()
    results = []

    print(f"Cross-validating {len(db['artists'])} artists...")
    print("Each artist's own signature tested as 'unknown' against all references")
    print("=" * 60)

    for i, artist in enumerate(db["artists"]):
        if len(artist["images"]) < 2:
            print(f"⚠️  Skipping {artist['name']} — need at least 2 images")
            continue

        # Pick a random image
        test_image = random.choice(artist["images"])
        test_path = SIGNATURES_DIR / test_image

        if not test_path.exists():
            print(f"⚠️  Skipping {artist['name']} — image not found")
            continue

        print(f"\n[{i+1}/{len(db['artists'])}] Testing {artist['name']}...", end=" ", flush=True)

        img_b64 = image_to_base64(test_path)
        media_type = get_media_type(test_image)

        start = time.time()
        data, status = api_post("/api/signatures/match", {
            "image": img_b64,
            "media_type": media_type
        }, token=token)
        elapsed = time.time() - start

        if status != 200:
            print(f"❌ Error ({status})")
            results.append({"artist": artist["name"], "correct": False, "error": True})
            continue

        best = data.get("best_match", "UNKNOWN")
        conf = data.get("best_confidence", 0)
        correct = best.lower().strip() == artist["name"].lower().strip()

        icon = "✅" if correct else "❌"
        print(f"{icon} → {best} ({conf}) [{elapsed:.1f}s]")

        results.append({
            "artist": artist["name"],
            "predicted": best,
            "confidence": conf,
            "correct": correct,
            "time": elapsed
        })

        # Small delay to avoid rate limiting
        time.sleep(1)

    # Summary
    print(f"\n{'=' * 60}")
    print("CROSS-VALIDATION RESULTS")
    print(f"{'=' * 60}")

    total = len(results)
    correct_count = sum(1 for r in results if r.get("correct"))
    accuracy = (correct_count / total * 100) if total > 0 else 0

    print(f"Total tested: {total}")
    print(f"Correct:      {correct_count}")
    print(f"Accuracy:     {accuracy:.1f}%")

    high = [r for r in results if r.get("confidence", 0) >= 0.8]
    med = [r for r in results if 0.6 <= r.get("confidence", 0) < 0.8]
    low = [r for r in results if r.get("confidence", 0) < 0.6]

    print(f"\nConfidence breakdown:")
    print(f"  High (>=0.8):     {len(high)} ({sum(1 for r in high if r.get('correct'))}/{len(high)} correct)")
    print(f"  Medium (0.6-0.8): {len(med)} ({sum(1 for r in med if r.get('correct'))}/{len(med)} correct)")
    print(f"  Low (<0.6):       {len(low)} ({sum(1 for r in low if r.get('correct'))}/{len(low)} correct)")

    wrong = [r for r in results if not r.get("correct") and not r.get("error")]
    if wrong:
        print(f"\nMisidentified (need better samples?):")
        for r in wrong:
            print(f"  {r['artist']} → predicted {r.get('predicted', '?')} ({r.get('confidence', 0)})")

    # Save results
    results_path = Path(__file__).parent / "signatures" / "cross_validation_results.json"
    with open(results_path, 'w') as f:
        json.dump({
            "date": time.strftime("%Y-%m-%d"),
            "total": total,
            "correct": correct_count,
            "accuracy": accuracy,
            "results": results
        }, f, indent=2)
    print(f"\nResults saved to: {results_path}")


# -------------------------------------------------------------------
# Test 5: Test against real eBay signed comic images
# -------------------------------------------------------------------
def test_ebay_signed(token):
    print("Fetching signed eBay sales with images...")
    print("─" * 60)

    # Get signed sales that have images and creator info
    data, status = api_get("/api/signatures/signed-sales?limit=20&has_image=true")

    if status != 200:
        print(f"❌ Error ({status}): {data}")
        return

    sales = data.get("sales", [])
    if not sales:
        print("No signed sales with images found.")
        return

    # Filter to sales where we have a matching creator in our DB
    db = load_db()
    db_artists = {a["name"].lower(): a["name"] for a in db["artists"]}
    # Also check aliases
    for a in db["artists"]:
        for alias in a.get("aliases", []):
            db_artists[alias.lower()] = a["name"]

    testable = []
    for s in sales:
        creators = s.get("creators", "")
        if not creators:
            continue
        # Check if any creator in the sale matches our DB
        for db_key, db_name in db_artists.items():
            if db_key in creators.lower():
                testable.append({"sale": s, "expected_artist": db_name})
                break

    print(f"Found {len(sales)} signed sales, {len(testable)} with creators in our reference DB")

    if not testable:
        print("\nNo testable sales — signed sales don't match any artists in reference DB.")
        print("Creator breakdown from signed sales:")
        for cb in data.get("creator_breakdown", [])[:10]:
            in_db = "✅" if any(cb['creators'].lower() in k for k in db_artists) else "❌"
            print(f"  {in_db} {cb['creators']}: {cb['count']} sales")
        return

    # Test each one (limited to 5 to save API costs)
    print(f"\nTesting up to 5 signed sales against reference DB...")
    for item in testable[:5]:
        sale = item["sale"]
        expected = item["expected_artist"]

        print(f"\n{'─' * 50}")
        print(f"Sale: {sale.get('raw_title', '?')[:70]}")
        print(f"Expected signer: {expected}")
        print(f"Image URL: {sale.get('image_url', 'none')[:80]}")

        # Note: We'd need to download the eBay image and convert to base64
        # For now, just show what we'd test
        print(f"⚠️  Full eBay image testing requires downloading sale images — skipping for now")
        print(f"    Sale ID {sale.get('id')} is a candidate for testing")


# -------------------------------------------------------------------
# Test 6: Premium analysis
# -------------------------------------------------------------------
def premium_analysis():
    print("Running signed premium analysis...")
    print("─" * 60)

    data, status = api_get("/api/signatures/premium-analysis?min_comps=3&min_price=10")

    if status != 200:
        print(f"❌ Error ({status}): {data}")
        return

    summary = data.get("summary", {})
    pairs = data.get("pairs", [])

    print(f"Total signed sales in DB:  {summary.get('total_signed_sales', '?')}")
    print(f"Matched pairs (w/ comps):  {summary.get('matched_pairs', '?')}")
    print(f"Skipped (no comps):        {summary.get('skipped_no_comps', '?')}")
    print(f"Skipped (title collision):  {summary.get('skipped_collision', '?')}")

    overall = summary.get("overall")
    if overall:
        print(f"\n{'═' * 50}")
        print(f"OVERALL SIGNED PREMIUM")
        print(f"{'═' * 50}")
        print(f"  Mean premium:    {overall['mean_premium']:+.1f}%")
        print(f"  Median premium:  {overall['median_premium']:+.1f}%")
        print(f"  Range:           {overall['min_premium']:+.0f}% to {overall['max_premium']:+.0f}%")
        print(f"  Positive:        {overall['positive_count']}/{summary['matched_pairs']} ({overall['positive_pct']:.0f}%)")

    tiers = summary.get("by_grade_tier", {})
    if any(tiers.values()):
        print(f"\nBY GRADE TIER:")
        for tier_name, tier_data in tiers.items():
            if tier_data:
                label = tier_name.replace('_', ' ').title()
                print(f"  {label}: {tier_data['count']} pairs, "
                      f"median {tier_data['median']:+.0f}%, "
                      f"mean {tier_data['mean']:+.0f}%, "
                      f"range {tier_data['min']:+.0f}% to {tier_data['max']:+.0f}%")

    if pairs:
        print(f"\n{'─' * 50}")
        print(f"TOP MATCHED PAIRS (by premium)")
        print(f"{'Comic':40s} {'Grade':>5s} {'Signed':>8s} {'Unsign':>8s} {'Prem':>7s} {'Comps':>5s}  {'Creator'}")
        print(f"{'─' * 110}")
        for p in pairs[:25]:
            grade_str = f"{p['grade']:.1f}" if p['grade'] else "raw"
            collision = " ⚠️" if p.get('collision_adjusted') else ""
            print(f"{p['comic'][:40]:40s} {grade_str:>5s} ${p['signed_price']:>7.0f} ${p['unsigned_median']:>7.0f} "
                  f"{p['premium_vs_median']:>+6.0f}% {p['num_comps']:>5d}  {(p.get('creator') or '')[:20]}{collision}")

    methodology = data.get("methodology", {})
    if methodology:
        print(f"\nMethodology: {methodology.get('description', '')[:120]}")
        print(f"Collision handling: {methodology.get('collision_handling', '')[:120]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Signature Matcher")
    parser.add_argument("--check-signed-sales", action="store_true", help="Check signed sales in DB")
    parser.add_argument("--db-stats", action="store_true", help="Check signature DB stats")
    parser.add_argument("--test-known", help="Test with a known artist name")
    parser.add_argument("--cross-validate", action="store_true", help="Cross-validate all artists")
    parser.add_argument("--test-ebay", action="store_true", help="Test against eBay signed sales")
    parser.add_argument("--premium-analysis", action="store_true", help="Analyze signed vs unsigned premium")
    parser.add_argument("--token", help="Auth token for protected endpoints")

    args = parser.parse_args()

    if args.check_signed_sales:
        check_signed_sales()
    elif args.db_stats:
        check_db_stats()
    elif args.premium_analysis:
        premium_analysis()
    elif args.test_known:
        if not args.token:
            print("❌ --token required for matching endpoints")
            sys.exit(1)
        test_known_artist(args.test_known, args.token)
    elif args.cross_validate:
        if not args.token:
            print("❌ --token required for matching endpoints")
            sys.exit(1)
        cross_validate(args.token)
    elif args.test_ebay:
        if not args.token:
            print("❌ --token required")
            sys.exit(1)
        test_ebay_signed(args.token)
    else:
        print("Signature Matcher Test Suite")
        print("─" * 40)
        print("Run with one of:")
        print("  --check-signed-sales   See what signed data we have")
        print("  --db-stats            Check reference DB stats (no auth)")
        print("  --premium-analysis    Signed vs unsigned price premium (no auth)")
        print("  --test-known 'Jim Lee' --token TOKEN   Test known artist")
        print("  --cross-validate --token TOKEN          Full validation")
        print("  --test-ebay --token TOKEN               Test against eBay data")
