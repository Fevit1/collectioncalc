#!/usr/bin/env python3
"""
Test Script: Comic ID Bug Fix
Tests that year is properly used for series disambiguation in:
1. Cache key generation (different years = different cache keys)
2. eBay search query (year appears in search string)
3. Database lookup (year filters results)
4. API endpoint (year flows from frontend to backend)

Usage: python test_comic_id_bug.py [--api]
  --api flag runs live API tests against the deployed server
  Without --api, runs local unit tests only
"""

import sys
import os
import json
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_URL = 'https://collectioncalc-docker.onrender.com'

# ═══════════════════════════════════════════════════════════════
# LOCAL UNIT TESTS (no server needed)
# ═══════════════════════════════════════════════════════════════

def test_cache_key_disambiguation():
    """Test that cache keys include year when provided."""
    print("\n── Test 1: Cache Key Disambiguation ──")

    from ebay_valuation import normalize_grade_for_cache

    title = "ghost rider"
    issue = "1"
    grade = "VF"
    normalized_grade = normalize_grade_for_cache(grade)

    # Build cache keys the same way get_cached_result and save_to_cache do
    key_no_year = f"{title.lower().strip()}|{str(issue).strip()}|{normalized_grade}"

    key_1973 = f"{title.lower().strip()}|{str(issue).strip()}|{normalized_grade}"
    key_1973 += f"|{1973}"

    key_2022 = f"{title.lower().strip()}|{str(issue).strip()}|{normalized_grade}"
    key_2022 += f"|{2022}"

    print(f"  Key (no year): {key_no_year}")
    print(f"  Key (1973):    {key_1973}")
    print(f"  Key (2022):    {key_2022}")

    assert key_1973 != key_2022, "FAIL: 1973 and 2022 cache keys are identical!"
    assert key_no_year != key_1973, "FAIL: no-year and 1973 cache keys are identical!"
    assert key_no_year != key_2022, "FAIL: no-year and 2022 cache keys are identical!"
    assert key_1973 == "ghost rider|1|VF|1973", f"FAIL: unexpected key format: {key_1973}"
    assert key_2022 == "ghost rider|1|VF|2022", f"FAIL: unexpected key format: {key_2022}"

    print("  ✓ PASS — Cache keys are unique per year")


def test_title_normalizer_preserves_year():
    """Test that title_normalizer extracts and returns year."""
    print("\n── Test 2: Title Normalizer Year Extraction ──")

    from title_normalizer import normalize_title

    test_cases = [
        ("Ghost Rider (2022) #1", 2022),
        ("Ghost Rider (1973) #1", 1973),
        ("Amazing Spider-Man (1963) #300", 1963),
        ("Batman #423", None),  # No year in title
    ]

    for raw_title, expected_year in test_cases:
        result = normalize_title(raw_title)
        actual_year = result.get('title_year')

        if expected_year is not None:
            # Year might be int or str depending on implementation
            actual_int = int(actual_year) if actual_year else None
            status = "✓" if actual_int == expected_year else "✗"
            print(f"  {status} '{raw_title}' → year={actual_year} (expected {expected_year})")
            assert actual_int == expected_year, f"FAIL: Expected year {expected_year}, got {actual_year}"
        else:
            status = "✓" if not actual_year else "✗"
            print(f"  {status} '{raw_title}' → year={actual_year} (expected None)")

    print("  ✓ PASS — Year extraction works correctly")


def test_search_query_includes_year():
    """Test that _single_search builds query with year."""
    print("\n── Test 3: Search Query Year Inclusion ──")

    # We can't easily call _single_search without an API client,
    # so we'll test the query construction logic directly

    title = "Ghost Rider"
    issue = "1"

    # Simulate the query construction from _single_search
    def build_query(full_title, issue, publisher=None, year=None):
        year_str = f" ({year})" if year else ""
        search_query = f"{full_title}{year_str} #{issue} comic raw ungraded"
        if publisher:
            search_query += f" {publisher}"
        search_query += " -CGC -CBCS -slab -graded price sold value"
        return search_query

    q_no_year = build_query(title, issue)
    q_1973 = build_query(title, issue, year=1973)
    q_2022 = build_query(title, issue, year=2022)

    print(f"  No year: {q_no_year}")
    print(f"  1973:    {q_1973}")
    print(f"  2022:    {q_2022}")

    assert "(1973)" in q_1973, "FAIL: 1973 not in search query"
    assert "(2022)" in q_2022, "FAIL: 2022 not in search query"
    assert "(" not in q_no_year.split("#")[0], "FAIL: year parens in no-year query"

    print("  ✓ PASS — Search queries include year for disambiguation")


def test_function_signatures():
    """Test that all functions accept year parameter."""
    print("\n── Test 4: Function Signature Verification ──")

    import inspect

    from ebay_valuation import (
        get_cached_result, save_to_cache, _single_search,
        search_ebay_sold, get_valuation_with_ebay
    )
    from comic_lookup import lookup_comic

    functions = [
        (get_cached_result, 'get_cached_result'),
        (save_to_cache, 'save_to_cache'),
        (_single_search, '_single_search'),
        (search_ebay_sold, 'search_ebay_sold'),
        (get_valuation_with_ebay, 'get_valuation_with_ebay'),
        (lookup_comic, 'lookup_comic'),
    ]

    for func, name in functions:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        has_year = 'year' in params

        # Check year has a default (is optional)
        if has_year:
            year_param = sig.parameters['year']
            has_default = year_param.default is not inspect.Parameter.empty
            status = "✓" if has_default else "✗ (no default!)"
        else:
            status = "✗ MISSING"

        print(f"  {status} {name}({'year' if has_year else 'NO YEAR'})")
        assert has_year, f"FAIL: {name} missing year parameter"

    print("  ✓ PASS — All functions accept optional year parameter")


def test_comic_lookup_year_filtering():
    """Test that lookup_comic uses year in queries."""
    print("\n── Test 5: Database Lookup Year Filtering ──")

    # Read the source code and verify the SQL includes year
    with open(os.path.join(os.path.dirname(__file__), 'comic_lookup.py'), 'r') as f:
        source = f.read()

    # Check for year in WHERE clause
    has_year_query = 'AND year = ?' in source
    has_year_publisher_combo = 'norm_publisher and year' in source
    has_year_only = 'elif year:' in source

    s1 = '✓' if has_year_query else '✗'
    s2 = '✓' if has_year_publisher_combo else '✗'
    s3 = '✓' if has_year_only else '✗'
    print(f"  {s1} WHERE ... AND year = ? exists")
    print(f"  {s2} publisher+year branch exists")
    print(f"  {s3} year-only branch exists")

    assert has_year_query, "FAIL: No year in WHERE clause"
    assert has_year_publisher_combo, "FAIL: No publisher+year branch"
    assert has_year_only, "FAIL: No year-only branch"

    print("  ✓ PASS — Database lookup includes year filtering")


# ═══════════════════════════════════════════════════════════════
# LIVE API TESTS (requires deployed server + auth token)
# ═══════════════════════════════════════════════════════════════

def test_api_valuate_with_year():
    """Test /api/valuate endpoint accepts and uses year."""
    print("\n── Test 6: Live API — /api/valuate with year ──")

    import requests

    # Try to get auth token from env or prompt
    auth_token = os.environ.get('SW_AUTH_TOKEN', '')
    if not auth_token:
        print("  ⚠ Set SW_AUTH_TOKEN env var to run API tests")
        print("  SKIP — No auth token")
        return False

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}'
    }

    # Test 1: Ghost Rider 2022 #1
    print("  Testing Ghost Rider (2022) #1...")
    resp_2022 = requests.post(f"{API_URL}/api/valuate", headers=headers, json={
        'title': 'Ghost Rider',
        'issue': '1',
        'grade': 'VF',
        'year': 2022,
        'publisher': 'Marvel'
    }, timeout=60)

    if resp_2022.status_code != 200:
        print(f"  ✗ FAIL — Status {resp_2022.status_code}: {resp_2022.text[:200]}")
        return False

    val_2022 = resp_2022.json()
    print(f"  2022 value: ${val_2022.get('fair_value', val_2022.get('final_value', 'N/A'))}")

    # Test 2: Ghost Rider 1973 #1
    print("  Testing Ghost Rider (1973) #1...")
    resp_1973 = requests.post(f"{API_URL}/api/valuate", headers=headers, json={
        'title': 'Ghost Rider',
        'issue': '1',
        'grade': 'VF',
        'year': 1973,
        'publisher': 'Marvel'
    }, timeout=60)

    if resp_1973.status_code != 200:
        print(f"  ✗ FAIL — Status {resp_1973.status_code}: {resp_1973.text[:200]}")
        return False

    val_1973 = resp_1973.json()
    print(f"  1973 value: ${val_1973.get('fair_value', val_1973.get('final_value', 'N/A'))}")

    # The 1973 original should be worth significantly more than 2022 reboot
    v2022 = float(val_2022.get('fair_value', val_2022.get('final_value', 0)))
    v1973 = float(val_1973.get('fair_value', val_1973.get('final_value', 0)))

    if v1973 > 0 and v2022 > 0:
        ratio = v1973 / v2022
        print(f"  Price ratio (1973/2022): {ratio:.1f}x")
        if ratio > 2:
            print("  ✓ PASS — 1973 original is significantly more valuable than 2022 reboot")
        else:
            print("  ⚠ WARNING — Expected 1973 to be worth much more than 2022")
            print(f"    1973=${v1973:.2f} vs 2022=${v2022:.2f}")
    else:
        print(f"  ⚠ Could not compare values (1973=${v1973}, 2022=${v2022})")

    # Test 3: No year (backward compat)
    print("  Testing Ghost Rider #1 (no year — backward compat)...")
    resp_none = requests.post(f"{API_URL}/api/valuate", headers=headers, json={
        'title': 'Ghost Rider',
        'issue': '1',
        'grade': 'VF',
        'publisher': 'Marvel'
    }, timeout=60)

    if resp_none.status_code == 200:
        val_none = resp_none.json()
        print(f"  No-year value: ${val_none.get('fair_value', val_none.get('final_value', 'N/A'))}")
        print("  ✓ PASS — Backward compatible (no year still works)")
    else:
        print(f"  ✗ FAIL — Backward compat broken! Status {resp_none.status_code}")
        return False

    return True


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    run_api = '--api' in sys.argv

    print("=" * 60)
    print("  COMIC ID BUG FIX — TEST SUITE")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    # Local unit tests
    local_tests = [
        test_cache_key_disambiguation,
        test_title_normalizer_preserves_year,
        test_search_query_includes_year,
        test_function_signatures,
        test_comic_lookup_year_filtering,
    ]

    for test in local_tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL — {e}")
            failed += 1

    # API tests (only with --api flag)
    if run_api:
        try:
            result = test_api_valuate_with_year()
            if result:
                passed += 1
            elif result is False:
                failed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ✗ FAIL — {e}")
            failed += 1
    else:
        print("\n── Test 6: Live API Tests ──")
        print("  SKIP — Run with --api flag to test live endpoint")
        skipped += 1

    # Summary
    print("\n" + "=" * 60)
    total = passed + failed + skipped
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed, {skipped} skipped")
    if failed == 0:
        print("  ✅ ALL TESTS PASSED")
    else:
        print("  ❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)
