"""
Test script to verify title_normalizer integration.
Run this BEFORE deploying to ensure everything works.

Usage:
    python test_integration.py
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        from title_normalizer import normalize_title
        print("  ✅ title_normalizer imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import title_normalizer: {e}")
        return False

    try:
        from rapidfuzz import fuzz, process
        print("  ✅ rapidfuzz imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import rapidfuzz: {e}")
        print("     Run: pip install rapidfuzz")
        return False

    return True


def test_json_files():
    """Test that JSON files exist and are valid"""
    print("\nTesting JSON files...")

    files = ['known_titles.json', 'known_creators.json', 'title_mappings.json']

    for filename in files:
        if os.path.exists(filename):
            print(f"  ✅ {filename} found")
            try:
                import json
                with open(filename, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"     Contains {len(data)} items")
                    elif isinstance(data, dict):
                        print(f"     Contains {len(data)} mappings")
            except Exception as e:
                print(f"  ❌ {filename} is invalid: {e}")
                return False
        else:
            print(f"  ❌ {filename} not found")
            return False

    return True


def test_normalization():
    """Test the normalizer with sample titles"""
    print("\nTesting normalization...")

    from title_normalizer import normalize_title

    test_cases = [
        ("Batman #1 CGC 9.8", "Batman", "1"),
        ("Marvel Super-Heroes Secret Wars #1", "Secret Wars", "1"),
        ("Amazing Spider-Man #300 Todd McFarlane", "Amazing Spider-Man", "300"),
        ("DC Comics Presents #1", "DC Comics Presents", "1"),
    ]

    all_passed = True

    for raw, expected_title, expected_issue in test_cases:
        result = normalize_title(raw)

        if result['canonical_title'] == expected_title and result['issue_number'] == expected_issue:
            print(f"  ✅ '{raw}'")
            print(f"     → {result['canonical_title']} #{result['issue_number']}")
        else:
            print(f"  ❌ '{raw}'")
            print(f"     Expected: {expected_title} #{expected_issue}")
            print(f"     Got: {result['canonical_title']} #{result['issue_number']}")
            all_passed = False

    return all_passed


def test_creator_extraction():
    """Test creator name extraction"""
    print("\nTesting creator extraction...")

    from title_normalizer import normalize_title

    test_cases = [
        ("Batman #1 Frank Miller", "Frank Miller"),
        ("Spawn #1 Todd McFarlane Image Comics", "Todd McFarlane"),
        ("Amazing Spider-Man #300 NM", None),  # No creator
    ]

    all_passed = True

    for raw, expected_creator in test_cases:
        result = normalize_title(raw)

        if expected_creator:
            if result['creators'] and expected_creator in result['creators']:
                print(f"  ✅ Found '{expected_creator}' in '{raw}'")
            else:
                print(f"  ❌ Failed to find '{expected_creator}' in '{raw}'")
                print(f"     Got: {result['creators']}")
                all_passed = False
        else:
            if not result['creators']:
                print(f"  ✅ Correctly found no creators in '{raw}'")
            else:
                print(f"  ⚠️  Found unexpected creator: {result['creators']}")

    return all_passed


def test_performance():
    """Test normalization performance"""
    print("\nTesting performance...")

    from title_normalizer import normalize_title
    import time

    test_title = "CGC SS 9.8~Amazing Spider-Man #300~SIGNED Todd McFarlane~1st Venom"

    iterations = 100
    start = time.time()

    for _ in range(iterations):
        normalize_title(test_title)

    end = time.time()
    avg_ms = ((end - start) / iterations) * 1000

    print(f"  ✅ {iterations} normalizations in {(end-start)*1000:.1f}ms")
    print(f"     Average: {avg_ms:.2f}ms per title")

    if avg_ms < 5:
        print(f"     Performance: Excellent (< 5ms)")
    elif avg_ms < 10:
        print(f"     Performance: Good (< 10ms)")
    else:
        print(f"     Performance: Acceptable but monitor in production")

    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("TITLE NORMALIZER INTEGRATION TEST")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("JSON Files", test_json_files),
        ("Normalization", test_normalization),
        ("Creator Extraction", test_creator_extraction),
        ("Performance", test_performance),
    ]

    results = {}

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")

    all_passed = all(results.values())

    print("=" * 60)

    if all_passed:
        print("✅ ALL TESTS PASSED - Ready to deploy!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Fix issues before deploying")
        return 1


if __name__ == '__main__':
    sys.exit(main())
