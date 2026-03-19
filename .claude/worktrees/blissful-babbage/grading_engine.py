"""
Grading Engine - Structured, deterministic comic book grading
Converts per-category condition scores into CGC-equivalent grades.

Approach:
1. AI evaluates 8 specific categories (0-10 each)
2. Weighted average → raw score
3. Raw score → snapped to nearest valid CGC grade
4. Multi-run: run N times, average category scores, then compute grade

This eliminates subjective "holistic" grading and produces consistent results.
"""

import json
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# ──────────────────────────────────────────────
# CGC Grade Scale (complete)
# ──────────────────────────────────────────────

CGC_GRADES = [
    (10.0, "GM",     "Gem Mint"),
    (9.9,  "MT",     "Mint"),
    (9.8,  "NM/MT",  "Near Mint/Mint"),
    (9.6,  "NM+",    "Near Mint+"),
    (9.4,  "NM",     "Near Mint"),
    (9.2,  "NM-",    "Near Mint-"),
    (9.0,  "VF/NM",  "Very Fine/Near Mint"),
    (8.5,  "VF+",    "Very Fine+"),
    (8.0,  "VF",     "Very Fine"),
    (7.5,  "VF-",    "Very Fine-"),
    (7.0,  "FN/VF",  "Fine/Very Fine"),
    (6.5,  "FN+",    "Fine+"),
    (6.0,  "FN",     "Fine"),
    (5.5,  "FN-",    "Fine-"),
    (5.0,  "VG/FN",  "Very Good/Fine"),
    (4.5,  "VG+",    "Very Good+"),
    (4.0,  "VG",     "Very Good"),
    (3.5,  "VG-",    "Very Good-"),
    (3.0,  "GD/VG",  "Good/Very Good"),
    (2.5,  "GD+",    "Good+"),
    (2.0,  "GD",     "Good"),
    (1.8,  "GD-",    "Good-"),
    (1.5,  "FR/GD",  "Fair/Good"),
    (1.0,  "FR",     "Fair"),
    (0.5,  "PR",     "Poor"),
]

# Valid numeric grades for snapping
VALID_GRADES = [g[0] for g in CGC_GRADES]

# ──────────────────────────────────────────────
# Category weights (must sum to 1.0)
# ──────────────────────────────────────────────
# These reflect what CGC graders prioritize

CATEGORY_WEIGHTS = {
    "cover_front":  0.25,   # Front cover is king
    "spine":        0.20,   # Spine condition is #2
    "corners":      0.15,   # Corners are highly visible
    "edges":        0.10,   # Edge wear
    "cover_back":   0.10,   # Back cover matters less
    "color_gloss":  0.10,   # Color quality and paper gloss
    "structural":   0.05,   # Missing pages, cut coupons, etc.
    "interior":     0.05,   # Interior page quality
}

assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"


# ──────────────────────────────────────────────
# Score-to-Grade Conversion
# ──────────────────────────────────────────────

def snap_to_cgc_grade(raw_score: float) -> Tuple[float, str, str]:
    """
    Snap a raw 0-10 score to the nearest valid CGC grade.
    Returns (numeric_grade, label, full_name).
    """
    if raw_score >= 10.0:
        return CGC_GRADES[0]  # 10.0 GM
    if raw_score <= 0.5:
        return CGC_GRADES[-1]  # 0.5 PR

    # Find the closest valid grade
    closest = min(CGC_GRADES, key=lambda g: abs(g[0] - raw_score))
    return closest


def compute_grade(category_scores: Dict[str, float]) -> dict:
    """
    Compute final CGC grade from per-category scores.

    Args:
        category_scores: Dict mapping category name to 0-10 score
            Required keys: cover_front, spine, corners, edges,
                          cover_back, color_gloss, structural, interior

    Returns:
        Dict with grade info and full breakdown
    """
    # Validate all categories present
    missing = set(CATEGORY_WEIGHTS.keys()) - set(category_scores.keys())
    if missing:
        raise ValueError(f"Missing category scores: {missing}")

    # Clamp all scores to 0-10
    clamped = {k: max(0, min(10, v)) for k, v in category_scores.items()
               if k in CATEGORY_WEIGHTS}

    # Compute weighted average
    raw_score = sum(clamped[cat] * weight
                    for cat, weight in CATEGORY_WEIGHTS.items())

    # Snap to CGC grade
    numeric_grade, grade_label, grade_name = snap_to_cgc_grade(raw_score)

    # Lowest category determines grade ceiling
    # (CGC graders can't ignore a terrible spine even if cover is perfect)
    min_score = min(clamped.values())
    min_category = min(clamped, key=clamped.get)

    # If any single category is catastrophically bad (< 3),
    # cap the grade at that category's implied grade
    if min_score < 3.0:
        ceiling_grade = snap_to_cgc_grade(min_score * 1.5)[0]  # scale up slightly
        if numeric_grade > ceiling_grade:
            numeric_grade, grade_label, grade_name = snap_to_cgc_grade(ceiling_grade)

    return {
        "raw_score": round(raw_score, 2),
        "final_grade": numeric_grade,
        "grade_label": grade_label,
        "grade_name": grade_name,
        "category_scores": clamped,
        "weights_used": CATEGORY_WEIGHTS,
        "limiting_factor": min_category if min_score < 7.0 else None,
    }


# ──────────────────────────────────────────────
# Multi-Run Averaging
# ──────────────────────────────────────────────

def average_multi_run(runs: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Average category scores across multiple grading runs.
    Uses median (not mean) for robustness against outliers.

    Args:
        runs: List of category_scores dicts from multiple runs

    Returns:
        Averaged category_scores dict
    """
    if len(runs) == 1:
        return runs[0]

    categories = runs[0].keys()
    averaged = {}

    for cat in categories:
        values = [run[cat] for run in runs if cat in run]
        if values:
            averaged[cat] = round(statistics.median(values), 1)

    return averaged


# ──────────────────────────────────────────────
# The Grading Prompt
# ──────────────────────────────────────────────

STRUCTURED_GRADING_PROMPT = """You are a professional CGC-equivalent comic book grader. You must evaluate this comic using a STRUCTURED SCORING SYSTEM.

IMPORTANT: You are evaluating the PHYSICAL CONDITION of this comic book, not its content or value.

The comic has been identified as: {title} #{issue}
Publisher: {publisher}
Photos provided: {photo_labels}

SCORING INSTRUCTIONS:
Score each of the following 8 categories from 0.0 to 10.0 (one decimal place).
Use the reference scale below for EACH category:

  10.0 = Perfect, flawless — no visible defects under close inspection
   9.5 = Near perfect — one trivial flaw barely visible
   9.0 = Excellent — very minor wear, hardly noticeable
   8.5 = Very good+ — slight wear visible on close inspection
   8.0 = Very good — minor but visible wear
   7.0 = Above average — noticeable wear, light stress marks
   6.0 = Average — moderate wear, some creasing
   5.0 = Below average — significant wear, visible creases
   4.0 = Worn — heavy wear, multiple defects
   3.0 = Poor condition — major defects
   2.0 = Heavily damaged — tears, missing pieces
   1.0 = Barely holding together

CATEGORIES TO SCORE:

1. COVER_FRONT (25% of grade): Front cover condition
   - Surface cleanliness (finger oils, dirt, foxing)
   - Color vibrancy and fading
   - Creases, wrinkles, bends
   - Tears or missing pieces
   - Writing, stamps, stickers (non-creator)
   Score: ___

2. SPINE (20% of grade): Spine condition
   - Spine stress lines/ticks (count them)
   - Spine roll (does spine lean?)
   - Spine splits (top, bottom, center)
   - Staple condition (tight, loose, missing, rusted)
   Score: ___

3. CORNERS (15% of grade): All four corners
   - Sharpness vs rounding
   - Bends, dog-ears, creases at corners
   - Blunting
   Score: ___

4. EDGES (10% of grade): Top, bottom, right edges
   - Edge wear / fraying
   - Chipping
   - Tears along edges
   Score: ___

5. COVER_BACK (10% of grade): Back cover condition
   - Same criteria as front cover
   - Often more worn than front
   Score: ___

6. COLOR_GLOSS (10% of grade): Paper and printing quality
   - Paper quality (white, cream, tan, brown)
   - Gloss/sheen remaining on cover
   - Ink coverage intact
   - Yellowing/tanning/brittleness
   Score: ___

7. STRUCTURAL (5% of grade): Overall structural integrity
   - Book lies flat
   - Pages attached at staples
   - No missing pages
   - No cut coupons
   - Centerfold attached
   Score: ___

8. INTERIOR (5% of grade): Interior page condition
   - Page quality (white to tanned)
   - Interior tears or writing
   - Subscription creases
   Score: ___

ADDITIONAL OBSERVATIONS:
- List specific defects you observe (be precise about location)
- Note any signatures detected (creator name if identifiable)
- If a photo is not provided for an area, score based on available evidence
  and note which areas you could NOT directly observe

RESPONSE FORMAT — Return ONLY this JSON, no markdown:
{{
  "category_scores": {{
    "cover_front": 0.0,
    "spine": 0.0,
    "corners": 0.0,
    "edges": 0.0,
    "cover_back": 0.0,
    "color_gloss": 0.0,
    "structural": 0.0,
    "interior": 0.0
  }},
  "defects": {{
    "front": ["specific defect 1", "specific defect 2"],
    "spine": [],
    "back": [],
    "interior": [],
    "other": []
  }},
  "observations": "Brief overall assessment noting key condition factors",
  "photos_evaluated": ["{photo_labels}"],
  "areas_not_visible": ["any areas you could not directly assess"],
  "signature_detected": false,
  "signature_info": null
}}

CRITICAL RULES:
1. Score EACH category independently — don't let one bad area drag all scores down
2. Be CONSERVATIVE — when in doubt, score lower (CGC graders are strict)
3. Be CONSISTENT — a minor spine tick is always 0.3-0.5 deduction, not sometimes 0.3 and sometimes 1.5
4. Score to ONE decimal place (e.g., 8.5, not 8.47 or 9)
5. EVERY defect you mention MUST be reflected in the relevant category score
6. If you can see only the front cover photo, still provide your best estimates for other categories but list them in areas_not_visible"""


def build_grading_prompt(title: str, issue: str, publisher: str, photo_labels: list) -> str:
    """Build the structured grading prompt with comic info filled in."""
    labels_str = ", ".join(photo_labels)
    return STRUCTURED_GRADING_PROMPT.format(
        title=title,
        issue=issue,
        publisher=publisher,
        photo_labels=labels_str
    )


# ──────────────────────────────────────────────
# Parse AI Response
# ──────────────────────────────────────────────

def parse_grading_response(response_text: str) -> dict:
    """
    Parse the AI's structured grading response and compute final grade.

    Returns dict with:
        - final_grade (numeric)
        - grade_label
        - grade_name
        - raw_score
        - category_scores
        - defects
        - observations
        - etc.
    """
    # Clean up response
    text = response_text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(text)

    # Extract category scores
    category_scores = parsed.get("category_scores", {})

    # Compute grade from scores
    grade_result = compute_grade(category_scores)

    # Merge everything
    result = {
        **grade_result,
        "defects": parsed.get("defects", {}),
        "observations": parsed.get("observations", ""),
        "photos_evaluated": parsed.get("photos_evaluated", []),
        "areas_not_visible": parsed.get("areas_not_visible", []),
        "signature_detected": parsed.get("signature_detected", False),
        "signature_info": parsed.get("signature_info", None),
    }

    return result


def parse_multi_run_responses(responses: List[str]) -> dict:
    """
    Parse multiple grading responses and compute averaged result.
    """
    all_scores = []
    all_defects = {"front": [], "spine": [], "back": [], "interior": [], "other": []}
    all_observations = []

    for resp in responses:
        parsed = json.loads(
            resp.strip().replace("```json", "").replace("```", "").strip()
        )
        all_scores.append(parsed.get("category_scores", {}))

        # Collect all unique defects across runs
        defects = parsed.get("defects", {})
        for area in all_defects:
            for d in defects.get(area, []):
                if d not in all_defects[area]:
                    all_defects[area].append(d)

        obs = parsed.get("observations", "")
        if obs:
            all_observations.append(obs)

    # Average the category scores (median)
    averaged_scores = average_multi_run(all_scores)

    # Compute grade from averaged scores
    grade_result = compute_grade(averaged_scores)

    # Include individual run scores for transparency
    result = {
        **grade_result,
        "defects": all_defects,
        "observations": all_observations[0] if all_observations else "",
        "run_count": len(responses),
        "individual_run_scores": all_scores,
        "signature_detected": False,
        "signature_info": None,
    }

    return result


# ──────────────────────────────────────────────
# Grade label compatibility (for valuation_model.py)
# ──────────────────────────────────────────────

def grade_to_label(numeric: float) -> str:
    """Convert numeric grade to label for valuation_model.py compatibility."""
    _, label, _ = snap_to_cgc_grade(numeric)
    return label

def label_to_grade(label: str) -> float:
    """Convert label to numeric grade."""
    for g, l, _ in CGC_GRADES:
        if l == label:
            return g
    return 5.0  # default to FN if unknown
