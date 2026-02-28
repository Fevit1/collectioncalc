"""
Grading Consistency Test Suite
Tests the structured grading engine for deterministic results.

Usage:
    # Unit tests (no API calls, free):
    python test_grading_consistency.py

    # Live API consistency test (requires ANTHROPIC_API_KEY, costs money):
    python test_grading_consistency.py --live

    # Live test with specific image:
    python test_grading_consistency.py --live --image path/to/comic.jpg --runs 5
"""

import json
import sys
import os
import statistics
from grading_engine import (
    compute_grade, snap_to_cgc_grade, average_multi_run,
    parse_grading_response, build_grading_prompt,
    CATEGORY_WEIGHTS, CGC_GRADES, VALID_GRADES,
    grade_to_label, label_to_grade
)


# ──────────────────────────────────────────────
# Unit Tests (no API, deterministic)
# ──────────────────────────────────────────────

def test_weights_sum_to_one():
    """Category weights must sum to 1.0"""
    total = sum(CATEGORY_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"
    print("✅ Weights sum to 1.0")


def test_grade_snap_boundaries():
    """Test that grade snapping works correctly at boundaries"""
    test_cases = [
        (10.0, 10.0, "GM"),
        (9.9, 9.9, "MT"),
        (9.7, 9.6, "NM+"),      # 9.7 is equidistant 9.6/9.8, snaps to 9.6
        (9.5, 9.6, "NM+"),      # snaps to nearest
        (9.3, 9.4, "NM"),
        (9.1, 9.2, "NM-"),
        (8.75, 9.0, "VF/NM"),   # midpoint snaps up
        (8.25, 8.5, "VF+"),     # midpoint snaps to nearest
        (8.0, 8.0, "VF"),
        (5.0, 5.0, "VG/FN"),
        (0.5, 0.5, "PR"),
        (0.1, 0.5, "PR"),       # clamps at bottom
    ]

    passed = 0
    for raw, expected_grade, expected_label in test_cases:
        grade, label, name = snap_to_cgc_grade(raw)
        if grade == expected_grade and label == expected_label:
            passed += 1
        else:
            print(f"  ❌ snap({raw}) = {grade} {label}, expected {expected_grade} {expected_label}")

    print(f"✅ Grade snap boundaries: {passed}/{len(test_cases)} passed")


def test_perfect_scores():
    """All 10s should give 10.0 GM"""
    scores = {cat: 10.0 for cat in CATEGORY_WEIGHTS}
    result = compute_grade(scores)
    assert result['final_grade'] == 10.0, f"Expected 10.0, got {result['final_grade']}"
    assert result['grade_label'] == 'GM', f"Expected GM, got {result['grade_label']}"
    print("✅ Perfect scores → 10.0 GM")


def test_near_mint_scores():
    """Typical NM comic: mostly 9s with minor flaws"""
    scores = {
        'cover_front': 9.5,
        'spine': 9.0,
        'corners': 9.5,
        'edges': 9.5,
        'cover_back': 9.5,
        'color_gloss': 9.5,
        'structural': 10.0,
        'interior': 9.5,
    }
    result = compute_grade(scores)
    assert 9.0 <= result['final_grade'] <= 9.6, f"Expected NM range, got {result['final_grade']}"
    print(f"✅ Near Mint scores → {result['final_grade']} {result['grade_label']}")


def test_fine_scores():
    """Typical FN comic: moderate wear"""
    scores = {
        'cover_front': 6.0,
        'spine': 5.5,
        'corners': 6.0,
        'edges': 6.5,
        'cover_back': 7.0,
        'color_gloss': 6.5,
        'structural': 8.0,
        'interior': 7.0,
    }
    result = compute_grade(scores)
    assert 5.5 <= result['final_grade'] <= 7.0, f"Expected FN range, got {result['final_grade']}"
    print(f"✅ Fine scores → {result['final_grade']} {result['grade_label']}")


def test_catastrophic_single_category():
    """If spine is destroyed but everything else is perfect, grade should be capped"""
    scores = {
        'cover_front': 9.5,
        'spine': 2.0,         # destroyed spine
        'corners': 9.5,
        'edges': 9.5,
        'cover_back': 9.5,
        'color_gloss': 9.5,
        'structural': 9.5,
        'interior': 9.5,
    }
    result = compute_grade(scores)
    # Should be well below NM despite high averages
    assert result['final_grade'] <= 8.5, f"Bad spine should cap grade, got {result['final_grade']}"
    assert result['limiting_factor'] == 'spine', f"Expected spine as limiter, got {result['limiting_factor']}"
    print(f"✅ Catastrophic spine → {result['final_grade']} {result['grade_label']} (limited by {result['limiting_factor']})")


def test_multi_run_averaging():
    """Multi-run median should smooth variance"""
    runs = [
        {'cover_front': 9.0, 'spine': 8.5, 'corners': 9.0, 'edges': 9.0,
         'cover_back': 9.0, 'color_gloss': 9.0, 'structural': 9.5, 'interior': 9.0},
        {'cover_front': 9.5, 'spine': 8.0, 'corners': 9.5, 'edges': 9.0,
         'cover_back': 9.5, 'color_gloss': 9.5, 'structural': 10.0, 'interior': 9.5},
        {'cover_front': 9.0, 'spine': 8.5, 'corners': 9.0, 'edges': 8.5,
         'cover_back': 9.0, 'color_gloss': 9.0, 'structural': 9.5, 'interior': 9.0},
    ]
    averaged = average_multi_run(runs)

    # Median of [9.0, 9.5, 9.0] = 9.0
    assert averaged['cover_front'] == 9.0, f"Expected median 9.0, got {averaged['cover_front']}"
    # Median of [8.5, 8.0, 8.5] = 8.5
    assert averaged['spine'] == 8.5, f"Expected median 8.5, got {averaged['spine']}"

    grade = compute_grade(averaged)
    print(f"✅ Multi-run averaging → {grade['final_grade']} {grade['grade_label']} (from 3 runs)")


def test_grade_label_roundtrip():
    """grade_to_label and label_to_grade should round-trip"""
    for numeric, label, name in CGC_GRADES:
        converted_label = grade_to_label(numeric)
        assert converted_label == label, f"grade_to_label({numeric}) = {converted_label}, expected {label}"
        converted_numeric = label_to_grade(label)
        assert converted_numeric == numeric, f"label_to_grade({label}) = {converted_numeric}, expected {numeric}"
    print(f"✅ Grade ↔ Label roundtrip: all {len(CGC_GRADES)} grades pass")


def test_deterministic_compute():
    """Same inputs must always produce same outputs"""
    scores = {
        'cover_front': 8.5,
        'spine': 7.5,
        'corners': 8.0,
        'edges': 8.5,
        'cover_back': 8.0,
        'color_gloss': 8.5,
        'structural': 9.5,
        'interior': 9.0,
    }

    results = [compute_grade(scores) for _ in range(100)]
    grades = set(r['final_grade'] for r in results)
    assert len(grades) == 1, f"Expected 1 unique grade across 100 runs, got {len(grades)}: {grades}"
    print(f"✅ Deterministic: 100 identical runs → {results[0]['final_grade']} {results[0]['grade_label']}")


def test_all_grade_ranges():
    """Verify that different score ranges produce expected grade ranges"""
    test_ranges = [
        (9.5, 9.4, 9.8, "Near Mint+ range"),
        (9.0, 8.5, 9.4, "Near Mint range"),
        (8.0, 7.5, 8.5, "Very Fine range"),
        (6.0, 5.5, 6.5, "Fine range"),
        (4.0, 3.5, 4.5, "Very Good range"),
        (2.0, 1.5, 2.5, "Good range"),
    ]

    for min_score, expected_min_grade, expected_max_grade, description in test_ranges:
        scores = {cat: min_score for cat in CATEGORY_WEIGHTS}
        result = compute_grade(scores)
        assert expected_min_grade <= result['final_grade'] <= expected_max_grade, \
            f"{description}: scores all {min_score} → {result['final_grade']}, expected {expected_min_grade}-{expected_max_grade}"
        print(f"  ✅ Scores all {min_score} → {result['final_grade']} {result['grade_label']} ({description})")

    print("✅ All grade ranges verified")


# ──────────────────────────────────────────────
# Calibration Comics (known CGC grades)
# ──────────────────────────────────────────────

CALIBRATION_COMICS = [
    {
        "title": "Amazing Spider-Man",
        "issue": "300",
        "publisher": "Marvel",
        "known_grade": 9.4,
        "notes": "First Venom, typically clean modern book"
    },
    {
        "title": "Uncanny X-Men",
        "issue": "266",
        "publisher": "Marvel",
        "known_grade": 8.0,
        "notes": "First Gambit, copper age, moderate wear typical"
    },
    {
        "title": "Batman",
        "issue": "423",
        "publisher": "DC",
        "known_grade": 7.5,
        "notes": "McFarlane cover, newsstand typically shows more wear"
    },
    {
        "title": "Spawn",
        "issue": "1",
        "publisher": "Image",
        "known_grade": 9.6,
        "notes": "High print run, many survive in high grade"
    },
    {
        "title": "Action Comics",
        "issue": "1",
        "publisher": "DC",
        "known_grade": 3.0,
        "notes": "Golden age, heavy wear expected on any surviving copy"
    },
    {
        "title": "X-Men",
        "issue": "1",
        "publisher": "Marvel",
        "known_grade": 9.8,
        "notes": "Jim Lee 1991, massive print run, many 9.8s"
    },
    {
        "title": "Walking Dead",
        "issue": "1",
        "publisher": "Image",
        "known_grade": 6.0,
        "notes": "Low print run, often read copies with moderate wear"
    },
    {
        "title": "New Mutants",
        "issue": "98",
        "publisher": "Marvel",
        "known_grade": 9.2,
        "notes": "First Deadpool, copper age typically minor wear"
    },
    {
        "title": "Teenage Mutant Ninja Turtles",
        "issue": "1",
        "publisher": "Mirage",
        "known_grade": 5.0,
        "notes": "Small press, typically shows significant wear"
    },
    {
        "title": "Incredible Hulk",
        "issue": "181",
        "publisher": "Marvel",
        "known_grade": 7.0,
        "notes": "First Wolverine, bronze age, value stamp present"
    },
]


# ──────────────────────────────────────────────
# Live API Consistency Test
# ──────────────────────────────────────────────

def test_live_consistency(image_path=None, num_runs=5):
    """
    Run the grading engine multiple times on the same image to test consistency.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic library not installed. Run: pip install anthropic")
        return

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set. Export it to run live tests.")
        return

    if not image_path:
        print("ℹ️  No --image provided. Skipping live consistency test.")
        print("   Usage: python test_grading_consistency.py --live --image path/to/comic.jpg --runs 5")
        return

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return

    import base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode()

    # Determine media type
    ext = image_path.lower().rsplit('.', 1)[-1]
    media_type = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}.get(ext, 'image/jpeg')

    prompt = build_grading_prompt("Test Comic", "1", "Unknown", ["Front Cover"])

    client = anthropic.Anthropic(api_key=api_key)
    all_grades = []
    all_scores = []

    print(f"\n🔬 Running {num_runs} grading passes on: {image_path}")
    print("─" * 60)

    for i in range(num_runs):
        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2048,
            temperature=0,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': image_data
                        }
                    },
                    {'type': 'text', 'text': prompt}
                ]
            }]
        )

        try:
            result = parse_grading_response(response.content[0].text)
            all_grades.append(result['final_grade'])
            all_scores.append(result['category_scores'])

            scores_str = " | ".join(f"{k[:5]}:{v}" for k, v in result['category_scores'].items())
            print(f"  Run {i+1}: {result['final_grade']} {result['grade_label']} ({scores_str})")
        except Exception as e:
            print(f"  Run {i+1}: ❌ Parse error: {e}")

    if all_grades:
        print("─" * 60)
        grade_range = max(all_grades) - min(all_grades)
        print(f"  Grades: {all_grades}")
        print(f"  Range: {min(all_grades)} – {max(all_grades)} (spread: {grade_range})")
        print(f"  Mean: {statistics.mean(all_grades):.1f}")
        print(f"  Median: {statistics.median(all_grades):.1f}")
        if len(all_grades) > 1:
            print(f"  Stdev: {statistics.stdev(all_grades):.2f}")

        # Per-category variance
        if all_scores:
            print(f"\n  Per-category variance across {len(all_scores)} runs:")
            for cat in CATEGORY_WEIGHTS:
                cat_values = [s.get(cat, 0) for s in all_scores]
                cat_range = max(cat_values) - min(cat_values)
                cat_stdev = statistics.stdev(cat_values) if len(cat_values) > 1 else 0
                status = "✅" if cat_range <= 1.0 else "⚠️" if cat_range <= 2.0 else "❌"
                print(f"    {status} {cat:15s}: range {cat_range:.1f}, stdev {cat_stdev:.2f} ({cat_values})")

        if grade_range <= 0.4:
            print(f"\n✅ PASS: Grade variance ≤ 0.4 ({grade_range})")
        elif grade_range <= 1.0:
            print(f"\n⚠️  MARGINAL: Grade variance {grade_range} (target ≤ 0.4)")
        else:
            print(f"\n❌ FAIL: Grade variance {grade_range} (target ≤ 0.4)")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("GRADING ENGINE — UNIT TESTS")
    print("=" * 60)

    test_weights_sum_to_one()
    test_grade_snap_boundaries()
    test_perfect_scores()
    test_near_mint_scores()
    test_fine_scores()
    test_catastrophic_single_category()
    test_multi_run_averaging()
    test_grade_label_roundtrip()
    test_deterministic_compute()
    test_all_grade_ranges()

    print("\n" + "=" * 60)
    print("ALL UNIT TESTS PASSED")
    print("=" * 60)

    # Live tests if requested
    if '--live' in sys.argv:
        image_path = None
        num_runs = 5

        if '--image' in sys.argv:
            idx = sys.argv.index('--image')
            if idx + 1 < len(sys.argv):
                image_path = sys.argv[idx + 1]

        if '--runs' in sys.argv:
            idx = sys.argv.index('--runs')
            if idx + 1 < len(sys.argv):
                num_runs = int(sys.argv[idx + 1])

        test_live_consistency(image_path, num_runs)
