#!/usr/bin/env python3
"""
Haiku 4.5 vs Sonnet 4 — Extraction & Grading Quality Comparison
Run: ANTHROPIC_API_KEY=sk-... python3 test_haiku_vs_sonnet.py

Tests 3 comics × 2 models × 2 tasks (extraction + grading) = 12 API calls
Estimated cost: ~$0.50 total
"""

import os
import sys
import json
import base64
import time
import requests

API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
if not API_KEY:
    print("ERROR: Set ANTHROPIC_API_KEY environment variable")
    sys.exit(1)

MODELS = {
    "sonnet": "claude-sonnet-4-20250514",
    "haiku": "claude-haiku-4-5-20251001"
}

# Import prompts from existing code
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comic_extraction import EXTRACTION_PROMPT
from grading_engine import STRUCTURED_GRADING_PROMPT

# Test comics — diverse era/condition range
TEST_COMICS = {
    "Batman #251 (1973 Bronze Age)": {
        "cover": "ComicBookImages/4PicTest/Batman_251_Cover.jpg",
        "spine": "ComicBookImages/4PicTest/Batman_251_Spine.jpg",
        "back": "ComicBookImages/4PicTest/Batman_251_Back.jpg",
        "centerfold": "ComicBookImages/4PicTest/Batman_251_Centerfold.jpg",
        "expected": {"title": "Batman", "issue": "251", "publisher": "DC", "year": 1973}
    },
    "Iron Man #198 (1985 Copper Age)": {
        "cover": "ComicBookImages/4PicTest/IronMan_198_Cover.jpeg",
        "spine": "ComicBookImages/4PicTest/IronMan_198_Spine.jpeg",
        "back": "ComicBookImages/4PicTest/IronMan_198_Back.jpeg",
        "centerfold": "ComicBookImages/4PicTest/IronMan_198_Center.jpeg",
        "expected": {"title": "Iron Man", "issue": "198", "publisher": "Marvel", "year": 1985}
    },
    "Avengers #145 (1976 Bronze Age)": {
        "cover": "ComicBookImages/4PicTest/Avengers145Cover.jpeg",
        "spine": "ComicBookImages/4PicTest/Avengers145Spine.jpeg",
        "back": "ComicBookImages/4PicTest/Avengers145Back.jpeg",
        "centerfold": "ComicBookImages/4PicTest/Avengers145Centerfold.jpeg",
        "expected": {"title": "Avengers", "issue": "145", "publisher": "Marvel", "year": 1976}
    }
}


def load_image_b64(path):
    """Load image as base64"""
    with open(path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    ext = path.lower().split(".")[-1]
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    return b64, media_type


def call_anthropic(model_key, messages, max_tokens=1000, temperature=0):
    """Call Anthropic API and return response + token usage"""
    model = MODELS[model_key]
    start = time.time()
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        },
        timeout=120
    )
    elapsed = time.time() - start

    if response.status_code != 200:
        return None, {"error": response.text, "status": response.status_code}, elapsed

    data = response.json()
    usage = data.get("usage", {})
    text = data["content"][0]["text"] if data.get("content") else ""

    return text, usage, elapsed


def test_extraction(comic_name, comic_data, model_key):
    """Test extraction on a single comic cover"""
    cover_path = comic_data["cover"]
    b64, media_type = load_image_b64(cover_path)

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": EXTRACTION_PROMPT}
        ]
    }]

    text, usage, elapsed = call_anthropic(model_key, messages, max_tokens=1000)

    # Parse JSON from response
    result = None
    if text:
        try:
            # Strip markdown code fences if present
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
            result = json.loads(clean.strip())
        except json.JSONDecodeError:
            result = {"parse_error": True, "raw": text[:500]}

    return {
        "model": model_key,
        "task": "extraction",
        "comic": comic_name,
        "result": result,
        "usage": usage,
        "elapsed": round(elapsed, 2)
    }


def test_grading(comic_name, comic_data, model_key):
    """Test grading on all 4 photos"""
    expected = comic_data["expected"]
    photo_labels = "front cover, spine, back cover, centerfold"

    prompt = STRUCTURED_GRADING_PROMPT.format(
        title=expected["title"],
        issue=expected["issue"],
        publisher=expected["publisher"],
        photo_labels=photo_labels
    )

    # Build message with all 4 images
    content = []
    for key in ["cover", "spine", "back", "centerfold"]:
        path = comic_data[key]
        b64, media_type = load_image_b64(path)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64}
        })

    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]

    text, usage, elapsed = call_anthropic(model_key, messages, max_tokens=2048)

    # Parse JSON
    result = None
    if text:
        try:
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
            result = json.loads(clean.strip())
        except json.JSONDecodeError:
            result = {"parse_error": True, "raw": text[:500]}

    return {
        "model": model_key,
        "task": "grading",
        "comic": comic_name,
        "result": result,
        "usage": usage,
        "elapsed": round(elapsed, 2)
    }


def compute_grade(scores):
    """Compute weighted grade from category scores (same as grading_engine.py)"""
    weights = {
        "cover_front": 0.25, "spine": 0.20, "corners": 0.15, "edges": 0.10,
        "cover_back": 0.10, "color_gloss": 0.10, "structural": 0.05, "interior": 0.05
    }
    total = sum(scores.get(k, 0) * w for k, w in weights.items())
    # Snap to CGC scale
    cgc_scale = [10.0, 9.9, 9.8, 9.6, 9.4, 9.2, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.8, 1.5, 1.0, 0.5]
    closest = min(cgc_scale, key=lambda x: abs(x - total))
    return round(total, 2), closest


def estimate_cost(usage, model_key):
    """Estimate cost from token usage"""
    rates = {
        "sonnet": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
        "haiku": {"input": 1.0 / 1_000_000, "output": 5.0 / 1_000_000}
    }
    r = rates[model_key]
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    return round(inp * r["input"] + out * r["output"], 6)


def main():
    print("=" * 80)
    print("HAIKU 4.5 vs SONNET 4 — Comic Extraction & Grading Comparison")
    print("=" * 80)

    all_results = []

    for comic_name, comic_data in TEST_COMICS.items():
        print(f"\n{'─' * 60}")
        print(f"COMIC: {comic_name}")
        print(f"{'─' * 60}")

        # --- EXTRACTION TEST ---
        for model_key in ["sonnet", "haiku"]:
            print(f"\n  [{model_key.upper()}] Extraction...", end=" ", flush=True)
            r = test_extraction(comic_name, comic_data, model_key)
            all_results.append(r)

            expected = comic_data["expected"]
            result = r["result"] or {}

            # Check accuracy
            title_match = expected["title"].lower() in (result.get("title", "")).lower()
            issue_match = str(expected["issue"]) == str(result.get("issue", ""))
            publisher_match = expected["publisher"].lower() in (result.get("publisher", "")).lower()
            year_match = expected["year"] == result.get("year")

            accuracy = sum([title_match, issue_match, publisher_match, year_match])
            cost = estimate_cost(r["usage"], model_key) if isinstance(r["usage"], dict) and "input_tokens" in r["usage"] else 0

            print(f"{r['elapsed']}s | {accuracy}/4 correct | ${cost:.4f}")
            print(f"    Title: {'✅' if title_match else '❌'} {result.get('title', '?')} (expected: {expected['title']})")
            print(f"    Issue: {'✅' if issue_match else '❌'} {result.get('issue', '?')} (expected: {expected['issue']})")
            print(f"    Publisher: {'✅' if publisher_match else '❌'} {result.get('publisher', '?')} (expected: {expected['publisher']})")
            print(f"    Year: {'✅' if year_match else '❌'} {result.get('year', '?')} (expected: {expected['year']})")
            print(f"    Grade: {result.get('suggested_grade', '?')} | Defects: {result.get('defects', [])}")
            if result.get("parse_error"):
                print(f"    ⚠️ JSON PARSE ERROR: {result.get('raw', '')[:200]}")

        # --- GRADING TEST ---
        for model_key in ["sonnet", "haiku"]:
            print(f"\n  [{model_key.upper()}] Grading (4 photos)...", end=" ", flush=True)
            r = test_grading(comic_name, comic_data, model_key)
            all_results.append(r)

            result = r["result"] or {}
            cost = estimate_cost(r["usage"], model_key) if isinstance(r["usage"], dict) and "input_tokens" in r["usage"] else 0

            scores = result.get("category_scores", {})
            if scores:
                raw_grade, cgc_grade = compute_grade(scores)
                print(f"{r['elapsed']}s | Grade: {cgc_grade} (raw: {raw_grade}) | ${cost:.4f}")
                print(f"    Scores: CF={scores.get('cover_front', '?')} SP={scores.get('spine', '?')} "
                      f"CO={scores.get('corners', '?')} ED={scores.get('edges', '?')} "
                      f"CB={scores.get('cover_back', '?')} CG={scores.get('color_gloss', '?')} "
                      f"ST={scores.get('structural', '?')} IN={scores.get('interior', '?')}")
                defects = result.get("defects", {})
                all_defects = []
                for loc in ["front", "spine", "back", "interior", "other"]:
                    all_defects.extend(defects.get(loc, []))
                print(f"    Defects ({len(all_defects)}): {'; '.join(all_defects[:5])}")
            else:
                print(f"{r['elapsed']}s | NO SCORES")
                if result.get("parse_error"):
                    print(f"    ⚠️ JSON PARSE ERROR: {result.get('raw', '')[:200]}")

    # --- SUMMARY ---
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")

    # Collect totals by model
    for model_key in ["sonnet", "haiku"]:
        model_results = [r for r in all_results if r["model"] == model_key]
        total_cost = sum(estimate_cost(r["usage"], model_key) for r in model_results if isinstance(r["usage"], dict) and "input_tokens" in r["usage"])
        total_time = sum(r["elapsed"] for r in model_results)
        total_input = sum(r["usage"].get("input_tokens", 0) for r in model_results if isinstance(r["usage"], dict))
        total_output = sum(r["usage"].get("output_tokens", 0) for r in model_results if isinstance(r["usage"], dict))

        # Extraction accuracy
        ext_results = [r for r in model_results if r["task"] == "extraction"]
        correct = 0
        total_fields = 0
        for r in ext_results:
            comic_name = r["comic"]
            expected = TEST_COMICS[comic_name]["expected"]
            result = r["result"] or {}
            correct += int(expected["title"].lower() in (result.get("title", "")).lower())
            correct += int(str(expected["issue"]) == str(result.get("issue", "")))
            correct += int(expected["publisher"].lower() in (result.get("publisher", "")).lower())
            correct += int(expected["year"] == result.get("year"))
            total_fields += 4

        # Grading comparison
        grade_results = [r for r in model_results if r["task"] == "grading"]
        grades = []
        for r in grade_results:
            scores = (r["result"] or {}).get("category_scores", {})
            if scores:
                _, cgc = compute_grade(scores)
                grades.append(cgc)

        print(f"\n  {model_key.upper()}:")
        print(f"    Total cost:        ${total_cost:.4f}")
        print(f"    Total time:        {total_time:.1f}s")
        print(f"    Input tokens:      {total_input:,}")
        print(f"    Output tokens:     {total_output:,}")
        print(f"    Extraction:        {correct}/{total_fields} fields correct ({correct/total_fields*100:.0f}%)")
        print(f"    Grades assigned:   {grades}")

    # Cost comparison
    sonnet_cost = sum(estimate_cost(r["usage"], "sonnet") for r in all_results if r["model"] == "sonnet" and isinstance(r["usage"], dict) and "input_tokens" in r["usage"])
    haiku_cost = sum(estimate_cost(r["usage"], "haiku") for r in all_results if r["model"] == "haiku" and isinstance(r["usage"], dict) and "input_tokens" in r["usage"])

    if haiku_cost > 0:
        savings_pct = (1 - haiku_cost / sonnet_cost) * 100 if sonnet_cost > 0 else 0
        print(f"\n  COST SAVINGS: Haiku is {savings_pct:.0f}% cheaper (${sonnet_cost:.4f} vs ${haiku_cost:.4f})")
        print(f"  PROJECTED ANNUAL SAVINGS: ${(sonnet_cost - haiku_cost) / sonnet_cost * 146831:.0f}/year at 15K users")

    # Save raw results
    with open("haiku_vs_sonnet_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Raw results saved to haiku_vs_sonnet_results.json")


if __name__ == "__main__":
    main()
