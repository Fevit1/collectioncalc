"""
Signature Matcher - Reference database matching for creator signature identification.

Uses Claude Vision to compare an unknown signature against the reference database.
This is the core matching engine for Patent #3 (Signature Identification).

Usage:
    # Match a single unknown signature against the reference DB
    python signature_matcher.py --image path/to/unknown_sig.jpg

    # Test with a known signature (validation mode)
    python signature_matcher.py --test --artist "Jim Lee"

    # Run full cross-validation (each sig vs all others)
    python signature_matcher.py --cross-validate

    # Run against eBay signed comics (requires API access)
    python signature_matcher.py --ebay-test
"""

import os
import sys
import json
import base64
import argparse
import random
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

SIGNATURES_DIR = Path(__file__).parent
DB_PATH = SIGNATURES_DIR / "signatures_db.json"


def load_db():
    """Load the signature reference database."""
    with open(DB_PATH, 'r') as f:
        return json.load(f)


def image_to_base64(image_path):
    """Convert an image file to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_media_type(filename):
    """Get MIME type from filename."""
    ext = filename.lower().split('.')[-1]
    return {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif'}.get(ext, 'image/jpeg')


def build_reference_collage_prompt(db, unknown_b64, unknown_media_type):
    """
    Build a Claude Vision prompt that shows the unknown signature alongside
    reference samples from each artist. Returns a list of messages for the API.

    Strategy: Send the unknown sig + 1 reference per artist (best quality),
    ask Claude to rank the top matches with confidence scores.
    """
    content = []

    # Add the unknown signature first
    content.append({
        "type": "text",
        "text": "UNKNOWN SIGNATURE TO IDENTIFY (Image 1):"
    })
    content.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": unknown_media_type,
            "data": unknown_b64
        }
    })

    # Add one reference per artist (pick the largest/best file)
    ref_index = 2
    artist_map = {}  # Track which image index maps to which artist

    for artist in db["artists"]:
        # Pick the best reference image (largest file = likely best quality)
        best_image = None
        best_size = 0
        for img_file in artist["images"]:
            img_path = SIGNATURES_DIR / img_file
            if img_path.exists():
                size = img_path.stat().st_size
                if size > best_size:
                    best_size = size
                    best_image = img_file

        if best_image:
            img_path = SIGNATURES_DIR / best_image
            img_b64 = image_to_base64(img_path)
            media_type = get_media_type(best_image)

            content.append({
                "type": "text",
                "text": f"\nREFERENCE {ref_index} — {artist['name']}:"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": img_b64
                }
            })
            artist_map[ref_index] = artist
            ref_index += 1

    # Add the matching instruction
    content.append({
        "type": "text",
        "text": """
Analyze the UNKNOWN SIGNATURE (Image 1) and compare it against all the reference signatures shown above.

For each reference artist, evaluate:
1. Letter formation and style similarity
2. Stroke weight and pressure patterns
3. Overall flow and slant
4. Character shapes and proportions
5. Any distinctive flourishes or marks

Return your analysis as JSON with this exact format:
{
    "matches": [
        {
            "artist": "Artist Name",
            "confidence": 0.85,
            "reasoning": "Brief explanation of why this matches or doesn't"
        }
    ],
    "best_match": "Artist Name or UNKNOWN",
    "best_confidence": 0.85,
    "is_confident_match": true,
    "notes": "Any additional observations about the signature"
}

Rules:
- List the top 3 most likely matches, sorted by confidence (highest first)
- Confidence ranges: 0.0-0.3 (no match), 0.3-0.6 (possible), 0.6-0.8 (likely), 0.8-1.0 (confident match)
- Set is_confident_match to true only if best_confidence >= 0.7
- If nothing matches well, set best_match to "UNKNOWN" with confidence < 0.3
- Be conservative — a false positive is worse than a false negative
"""
    })

    return content


def match_signature(unknown_image_path, api_key=None, verbose=True):
    """
    Match an unknown signature against the reference database.

    Args:
        unknown_image_path: Path to the unknown signature image
        api_key: Anthropic API key (falls back to env var)
        verbose: Print progress

    Returns:
        dict with matches, best_match, confidence, etc.
    """
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic package not installed. Run: pip install anthropic")
        return None

    api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return None

    db = load_db()

    # Load unknown signature
    unknown_path = Path(unknown_image_path)
    if not unknown_path.exists():
        print(f"❌ Image not found: {unknown_path}")
        return None

    if verbose:
        print(f"Loading unknown signature: {unknown_path.name}")

    unknown_b64 = image_to_base64(unknown_path)
    unknown_media_type = get_media_type(unknown_path.name)

    # Build the comparison prompt
    if verbose:
        print(f"Comparing against {len(db['artists'])} reference artists...")

    content = build_reference_collage_prompt(db, unknown_b64, unknown_media_type)

    # Call Claude Vision
    client = anthropic.Anthropic(api_key=api_key)

    if verbose:
        print("Calling Claude Vision API...")

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    # Parse response
    response_text = response.content[0].text
    if verbose:
        print(f"Response received ({len(response_text)} chars)")

    # Extract JSON from response
    try:
        # Try to find JSON in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response_text[json_start:json_end])
        else:
            result = {"error": "No JSON found in response", "raw": response_text}
    except json.JSONDecodeError:
        result = {"error": "Failed to parse JSON", "raw": response_text}

    return result


def cross_validate(api_key=None, samples_per_artist=1):
    """
    Cross-validation test: Take one signature from each artist,
    use it as the "unknown", and see if the matcher correctly identifies it.

    This is the key accuracy metric for the system.
    """
    db = load_db()
    results = []

    for artist in db["artists"]:
        if len(artist["images"]) < 2:
            print(f"⚠️  Skipping {artist['name']} — need at least 2 images for cross-validation")
            continue

        # Use a random image as the "unknown" test
        test_image = random.choice(artist["images"])
        test_path = SIGNATURES_DIR / test_image

        if not test_path.exists():
            print(f"⚠️  Skipping {artist['name']} — image not found: {test_image}")
            continue

        print(f"\n{'─' * 60}")
        print(f"Testing: {artist['name']} (using {test_image})")

        result = match_signature(test_path, api_key=api_key, verbose=False)

        if result and "best_match" in result:
            correct = result["best_match"].lower().strip() == artist["name"].lower().strip()
            confidence = result.get("best_confidence", 0)

            status = "✅" if correct else "❌"
            print(f"  {status} Predicted: {result['best_match']} (confidence: {confidence})")
            if not correct:
                print(f"     Expected: {artist['name']}")
                if result.get("matches"):
                    for m in result["matches"][:3]:
                        print(f"     - {m['artist']}: {m['confidence']} — {m.get('reasoning', '')[:80]}")

            results.append({
                "artist": artist["name"],
                "test_image": test_image,
                "predicted": result["best_match"],
                "confidence": confidence,
                "correct": correct,
                "top_matches": result.get("matches", [])[:3]
            })
        else:
            print(f"  ❌ API error: {result}")
            results.append({
                "artist": artist["name"],
                "test_image": test_image,
                "predicted": "ERROR",
                "confidence": 0,
                "correct": False,
                "error": str(result)
            })

    # Summary
    print(f"\n{'=' * 60}")
    print("CROSS-VALIDATION RESULTS")
    print(f"{'=' * 60}")

    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = (correct / total * 100) if total > 0 else 0

    print(f"Total tested: {total}")
    print(f"Correct:      {correct}")
    print(f"Accuracy:     {accuracy:.1f}%")

    # Confidence breakdown
    high_conf = [r for r in results if r["confidence"] >= 0.8]
    med_conf = [r for r in results if 0.6 <= r["confidence"] < 0.8]
    low_conf = [r for r in results if r["confidence"] < 0.6]

    print(f"\nConfidence breakdown:")
    print(f"  High (>=0.8):  {len(high_conf)} ({sum(1 for r in high_conf if r['correct'])}/{len(high_conf)} correct)")
    print(f"  Medium (0.6-0.8): {len(med_conf)} ({sum(1 for r in med_conf if r['correct'])}/{len(med_conf)} correct)")
    print(f"  Low (<0.6):    {len(low_conf)} ({sum(1 for r in low_conf if r['correct'])}/{len(low_conf)} correct)")

    # Worst performers (for Mike to collect better samples)
    wrong = [r for r in results if not r["correct"]]
    if wrong:
        print(f"\nMisidentified artists (need better samples?):")
        for r in wrong:
            print(f"  - {r['artist']} → predicted {r['predicted']} ({r['confidence']})")

    # Save results
    results_path = SIGNATURES_DIR / "cross_validation_results.json"
    with open(results_path, 'w') as f:
        json.dump({
            "date": "2026-02-28",
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "results": results
        }, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    return results


def test_known_artist(artist_name, api_key=None):
    """Test matching with a specific known artist's signature."""
    db = load_db()

    # Find the artist
    artist = None
    for a in db["artists"]:
        if a["name"].lower() == artist_name.lower():
            artist = a
            break

    if not artist:
        print(f"❌ Artist '{artist_name}' not found in database")
        print(f"Available: {', '.join(a['name'] for a in db['artists'])}")
        return

    # Pick a random image to test
    test_image = random.choice(artist["images"])
    test_path = SIGNATURES_DIR / test_image

    print(f"Testing with {artist['name']}'s signature: {test_image}")
    print(f"{'─' * 60}")

    result = match_signature(test_path, api_key=api_key, verbose=True)

    if result:
        print(f"\n{'─' * 60}")
        print(f"RESULT:")
        print(f"  Best match:  {result.get('best_match', 'N/A')}")
        print(f"  Confidence:  {result.get('best_confidence', 'N/A')}")
        print(f"  Confident?:  {result.get('is_confident_match', 'N/A')}")
        correct = result.get("best_match", "").lower().strip() == artist["name"].lower().strip()
        print(f"  Correct:     {'✅ YES' if correct else '❌ NO'}")

        if result.get("matches"):
            print(f"\n  Top matches:")
            for m in result["matches"]:
                print(f"    - {m['artist']}: {m['confidence']} — {m.get('reasoning', '')[:100]}")

        if result.get("notes"):
            print(f"\n  Notes: {result['notes']}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Signature Matcher - Identify comic creator signatures")
    parser.add_argument("--image", help="Path to unknown signature image")
    parser.add_argument("--test", action="store_true", help="Test with a known artist")
    parser.add_argument("--artist", help="Artist name for --test mode")
    parser.add_argument("--cross-validate", action="store_true", help="Run full cross-validation")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')

    if args.cross_validate:
        cross_validate(api_key=api_key)
    elif args.test and args.artist:
        test_known_artist(args.artist, api_key=api_key)
    elif args.image:
        result = match_signature(args.image, api_key=api_key)
        if result:
            print(json.dumps(result, indent=2))
    else:
        # Default: show database stats
        db = load_db()
        print(f"Signature Reference Database v{db['version']}")
        print(f"{'─' * 40}")
        print(f"Artists:    {db['stats']['total_artists']}")
        print(f"Images:     {db['stats']['total_images']}")
        print(f"High qual:  {db['stats']['high_quality']}")
        print(f"Med qual:   {db['stats']['medium_quality']}")
        print(f"Low qual:   {db['stats']['low_quality']}")
        print(f"\nMissing priority artists:")
        for m in db["missing_priority_artists"]:
            print(f"  ⚠️  {m['name']} — {m['reason']}")
        print(f"\nRun with --cross-validate to test accuracy")
        print(f"Run with --test --artist 'Jim Lee' to test a specific artist")
        print(f"Run with --image path/to/sig.jpg to identify an unknown signature")
