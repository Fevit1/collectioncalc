"""
Slab Worthy — Signature Identification Orchestrator v2
File: routes/signature_orchestrator.py

3-pass Opus 4.6 orchestrator with PostgreSQL metadata pre-filter.
Lives alongside v1 at /api/signatures/v2/ for A/B testing.

Integration fixes applied (Session 84):
  1. cs.name → cs.creator_name (match production schema)
  2. cs.slug removed (column doesn't exist; generated in Python)
  3. R2 images fetched via HTTP image_url (match v1 pattern, no boto3)
  4. DB connection via os.environ['DATABASE_URL'] (match rest of app)
  5. Auth decorators added (@require_auth, @require_approved)
  6. init_modules() pattern added for wsgi.py consistency
  7. Removed unused imports (asyncio, boto3)
"""

import base64
import json
import logging
import os
import re
import time
# ThreadPoolExecutor removed — sequential passes needed due to Opus 4.6
# rate limit (30K input tokens/min). Parallel calls trigger 429 errors.
from dataclasses import dataclass, field
from typing import Optional

import psycopg2
import requests as http_requests
from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth import require_auth, require_approved

logger = logging.getLogger(__name__)

signatures_v2_bp = Blueprint("signatures_v2", __name__, url_prefix="/api/signatures/v2")

# ---------------------------------------------------------------------------
# Module-level state (set by init_modules from wsgi.py)
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = None
_anthropic = None
ANTHROPIC_AVAILABLE = False


def init_modules(anthropic_key, anthropic_lib=None, anthropic_avail=None):
    """Initialize module variables from wsgi.py — matches other blueprint pattern."""
    global ANTHROPIC_API_KEY, _anthropic, ANTHROPIC_AVAILABLE
    ANTHROPIC_API_KEY = anthropic_key
    if anthropic_lib is not None:
        _anthropic = anthropic_lib
    else:
        try:
            import anthropic as _anth
            _anthropic = _anth
        except ImportError:
            pass
    ANTHROPIC_AVAILABLE = bool(ANTHROPIC_API_KEY and _anthropic)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPUS_MODEL = "claude-opus-4-6"
MAX_CANDIDATES = 15          # Pre-filter target before vision calls
REFERENCE_IMAGES_PER_CREATOR = 4
PASS_TEMPERATURES = [0.2, 0.5, 0.7]
LOW_CONFIDENCE_THRESHOLD = 0.50
CONFUSION_PAIR_DELTA = 0.10  # rank1 vs rank2 within this → flag
# MAX_WORKERS removed — passes run sequentially now (rate limit constraint)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CreatorCandidate:
    creator_id: int
    name: str
    era_start: Optional[int]
    era_end: Optional[int]
    publisher_affiliations: list[str]
    signature_style: Optional[str]   # e.g. "initials", "cursive", "stylized"
    image_urls: list[str] = field(default_factory=list)
    reference_images_b64: list[str] = field(default_factory=list)


@dataclass
class PassResult:
    temperature: float
    rankings: list[dict]
    analysis: dict
    flags: dict
    raw_response: str


@dataclass
class AggregatedResult:
    top5: list[dict]
    stability_scores: dict[str, float]
    flags: dict
    analysis: dict
    pass_count: int
    passes_attempted: int
    latency_ms: int


# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------

def _get_db():
    """Get PostgreSQL connection using DATABASE_URL env var (matches rest of app)."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def _make_slug(name: str) -> str:
    """Generate a URL-safe slug from creator name."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug


def prefilter_candidates(
    era_decade: Optional[str],
    publisher: Optional[str],
    signature_location: Optional[str],
    limit: int = MAX_CANDIDATES
) -> list[CreatorCandidate]:
    """
    Query PostgreSQL to narrow candidate pool before any vision calls.
    Uses metadata (era, publisher, style) to cut from ~100 → ~15 creators.
    Falls back to full pool if filters return too few results.
    """
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            # Build dynamic filter — start broad, tighten if we have context
            filters = ["cs.active = true", "cs.reference_image_count >= 2"]
            params = []

            if era_decade and era_decade != "unknown":
                decade_map = {
                    "pre-1970": (1930, 1969),
                    "1970s": (1965, 1982),
                    "1980s": (1978, 1992),
                    "1990s": (1988, 2002),
                    "2000s": (1998, 2012),
                    "2010s+": (2008, 2099),
                }
                if era_decade in decade_map:
                    lo, hi = decade_map[era_decade]
                    filters.append(
                        "(cs.career_start <= %s AND (cs.career_end IS NULL OR cs.career_end >= %s))"
                    )
                    params.extend([hi, lo])

            if publisher and publisher not in ("unknown", ""):
                filters.append(
                    "(%s = ANY(cs.publisher_affiliations) OR cs.publisher_affiliations IS NULL)"
                )
                params.append(publisher.upper())

            where_clause = " AND ".join(filters)

            cur.execute(f"""
                SELECT
                    cs.id AS creator_id,
                    cs.creator_name,
                    cs.career_start AS era_start,
                    cs.career_end AS era_end,
                    cs.publisher_affiliations,
                    cs.signature_style,
                    array_agg(si.image_url ORDER BY si.sort_order NULLS LAST, si.created_at DESC)
                        AS image_urls
                FROM creator_signatures cs
                JOIN signature_images si ON si.creator_id = cs.id
                WHERE {where_clause}
                GROUP BY cs.id, cs.creator_name, cs.career_start,
                         cs.career_end, cs.publisher_affiliations, cs.signature_style
                HAVING COUNT(si.id) >= 2
                ORDER BY cs.reference_image_count DESC
                LIMIT %s
            """, params + [limit])

            rows = cur.fetchall()

            # If filters are too aggressive, fall back to top creators by image count
            if len(rows) < 5:
                logger.warning(
                    "Pre-filter returned only %d candidates — falling back to top %d",
                    len(rows), limit
                )
                cur.execute("""
                    SELECT
                        cs.id AS creator_id,
                        cs.creator_name,
                        cs.career_start AS era_start,
                        cs.career_end AS era_end,
                        cs.publisher_affiliations,
                        cs.signature_style,
                        array_agg(si.image_url ORDER BY si.sort_order NULLS LAST, si.created_at DESC)
                            AS image_urls
                    FROM creator_signatures cs
                    JOIN signature_images si ON si.creator_id = cs.id
                    WHERE cs.active = true
                    GROUP BY cs.id, cs.creator_name, cs.career_start,
                             cs.career_end, cs.publisher_affiliations, cs.signature_style
                    ORDER BY cs.reference_image_count DESC
                    LIMIT %s
                """, [limit])
                rows = cur.fetchall()

            candidates = []
            for row in rows:
                # Cap to REFERENCE_IMAGES_PER_CREATOR URLs
                urls = [u for u in (row["image_urls"] or []) if u][:REFERENCE_IMAGES_PER_CREATOR]
                candidates.append(CreatorCandidate(
                    creator_id=row["creator_id"],
                    name=row["creator_name"],
                    era_start=row["era_start"],
                    era_end=row["era_end"],
                    publisher_affiliations=row["publisher_affiliations"] or [],
                    signature_style=row["signature_style"],
                    image_urls=urls,
                ))

            logger.info("Pre-filter selected %d candidates", len(candidates))
            return candidates

    finally:
        conn.close()


def log_result_to_db(
    unknown_image_key: str,
    result: AggregatedResult,
    comic_context: dict
):
    """Write identification result and any flags to PostgreSQL review queue."""
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            top = result.top5[0] if result.top5 else {}
            cur.execute("""
                INSERT INTO signature_identification_log (
                    unknown_image_key,
                    top_creator,
                    top_confidence,
                    top5_json,
                    flags_json,
                    comic_context_json,
                    stability_scores_json,
                    pass_count,
                    latency_ms,
                    needs_review,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [
                unknown_image_key,
                top.get("creator"),
                top.get("confidence"),
                json.dumps(result.top5),
                json.dumps(result.flags),
                json.dumps(comic_context),
                json.dumps(result.stability_scores),
                result.pass_count,
                result.latency_ms,
                result.flags.get("low_confidence_match", False)
                    or result.flags.get("high_confusion_pair", False)
                    or result.flags.get("degraded_result", False),
            ])
            conn.commit()
    except Exception as e:
        logger.error("Failed to log identification result: %s", e)
        conn.rollback()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# R2 Image Retrieval (via public HTTP — matches v1 pattern)
# ---------------------------------------------------------------------------

def _fetch_and_encode_image(image_url: str) -> Optional[str]:
    """Fetch an image from its public URL and return base64-encoded string."""
    try:
        resp = http_requests.get(image_url, timeout=15)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode('utf-8')
    except Exception as e:
        logger.warning("Failed to fetch image %s: %s", image_url, e)
        return None


def fetch_reference_images(candidates: list[CreatorCandidate]) -> list[CreatorCandidate]:
    """
    Fetch reference images via HTTP for all candidates.
    Returns candidates with reference_images_b64 populated.
    Drops candidates with no usable images.
    """
    for candidate in candidates:
        images_b64 = []
        for url in candidate.image_urls:
            b64 = _fetch_and_encode_image(url)
            if b64:
                images_b64.append(b64)
        candidate.reference_images_b64 = images_b64

    # Drop candidates with no usable images
    return [c for c in candidates if c.reference_images_b64]


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_identification_messages(
    unknown_image_b64: str,
    candidates: list[CreatorCandidate],
    comic_context: dict,
    system_prompt: str,
) -> tuple[str, list[dict]]:
    """
    Build the system prompt and messages array for one Opus call.
    Injects context metadata and attaches all reference + unknown images.
    """
    candidate_names = ", ".join(c.name for c in candidates)

    context_block = f"""COMIC CONTEXT:
- Publisher: {comic_context.get('publisher', 'unknown')}
- Era: {comic_context.get('era_decade', 'unknown')}
- Title: {comic_context.get('title', 'unknown')}
- Signature location: {comic_context.get('signature_location', 'unknown')}
- Slab grade label: {comic_context.get('slab_label', 'unknown')}

CANDIDATE POOL: {candidate_names}

REFERENCE IMAGES FOLLOW (grouped by creator, {REFERENCE_IMAGES_PER_CREATOR} per creator max):"""

    # Build content array: text intro + reference images + unknown image
    content = [{"type": "text", "text": context_block}]

    for candidate in candidates:
        content.append({
            "type": "text",
            "text": f"\n--- REFERENCE: {candidate.name} ---"
        })
        for img_b64 in candidate.reference_images_b64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64,
                },
            })

    content.append({
        "type": "text",
        "text": "\n--- TARGET SIGNATURE (unknown) ---\nIdentify this signature:"
    })
    content.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": unknown_image_b64,
        },
    })
    content.append({
        "type": "text",
        "text": "\nReturn ONLY the JSON object as specified. No preamble."
    })

    messages = [{"role": "user", "content": content}]
    return system_prompt, messages


# ---------------------------------------------------------------------------
# Single Opus Pass
# ---------------------------------------------------------------------------

def run_single_pass(
    temperature: float,
    unknown_image_b64: str,
    candidates: list[CreatorCandidate],
    comic_context: dict,
    system_prompt: str,
    client,
) -> PassResult:
    """Execute one Opus vision call and parse the JSON response."""
    _, messages = build_identification_messages(
        unknown_image_b64, candidates, comic_context, system_prompt
    )

    try:
        response = client.messages.create(
            model=OPUS_MODEL,
            max_tokens=1500,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if model adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)

        return PassResult(
            temperature=temperature,
            rankings=parsed.get("rankings", []),
            analysis=parsed.get("analysis", {}),
            flags=parsed.get("flags", {}),
            raw_response=raw,
        )

    except json.JSONDecodeError as e:
        logger.error("JSON parse error on pass temp=%.1f: %s", temperature, e)
        return PassResult(
            temperature=temperature,
            rankings=[],
            analysis={},
            flags={"parse_error": True},
            raw_response="",
        )
    except Exception as e:
        logger.error("Opus call failed on pass temp=%.1f: %s", temperature, e)
        return PassResult(
            temperature=temperature,
            rankings=[],
            analysis={},
            flags={"api_error": True, "error": str(e)},
            raw_response="",
        )


# ---------------------------------------------------------------------------
# 3-Pass Aggregation
# ---------------------------------------------------------------------------

def aggregate_passes(passes: list[PassResult], passes_attempted: int = 3) -> AggregatedResult:
    """
    Aggregate results from 3 Opus passes:
    - Average confidence scores per creator
    - Detect ranking instability
    - Merge flags
    - Return top 5 sorted by averaged confidence
    """
    # Collect all unique creator names across passes
    all_creators: dict[str, list[float]] = {}
    creator_ranks: dict[str, list[int]] = {}

    for pass_result in passes:
        for entry in pass_result.rankings:
            name = entry.get("creator", "")
            confidence = entry.get("confidence", 0.0)
            rank = entry.get("rank", 99)
            if not name:
                continue
            all_creators.setdefault(name, []).append(confidence)
            creator_ranks.setdefault(name, []).append(rank)

    # Average confidence scores
    averaged: list[dict] = []
    for name, scores in all_creators.items():
        avg_confidence = sum(scores) / len(scores)
        avg_rank = sum(creator_ranks[name]) / len(creator_ranks[name])

        # Stability: how much does rank vary across passes?
        rank_variance = max(creator_ranks[name]) - min(creator_ranks[name])

        # Pull match/contra evidence from the most confident pass
        best_pass = max(
            [p for p in passes if any(e.get("creator") == name for e in p.rankings)],
            key=lambda p: next(
                (e.get("confidence", 0) for e in p.rankings if e.get("creator") == name), 0
            ),
            default=passes[0],
        )
        best_entry = next(
            (e for e in best_pass.rankings if e.get("creator") == name), {}
        )

        averaged.append({
            "rank": 0,  # will be set after sort
            "creator": name,
            "confidence": round(avg_confidence, 3),
            "confidence_label": _confidence_label(avg_confidence),
            "match_evidence": best_entry.get("match_evidence", []),
            "contra_evidence": best_entry.get("contra_evidence", []),
            "avg_rank": avg_rank,
        })

    # Sort by averaged confidence descending
    averaged.sort(key=lambda x: x["confidence"], reverse=True)
    top5 = averaged[:5]
    for i, entry in enumerate(top5):
        entry["rank"] = i + 1
        del entry["avg_rank"]

    # Normalize confidence scores to sum to 1.0
    total = sum(e["confidence"] for e in top5)
    if total > 0:
        for entry in top5:
            entry["confidence"] = round(entry["confidence"] / total, 3)

    # Stability scores for top candidates
    stability_scores = {}
    for entry in top5:
        name = entry["creator"]
        if name in creator_ranks:
            rank_variance = max(creator_ranks[name]) - min(creator_ranks[name])
            stability_scores[name] = round(max(0.0, 1.0 - (rank_variance / 4.0)), 2)

    # Merge flags across passes
    merged_flags: dict = {}
    for pass_result in passes:
        for k, v in pass_result.flags.items():
            if k == "notes":
                notes = merged_flags.get("notes", "")
                merged_flags["notes"] = f"{notes} | {v}".strip(" |")
            elif isinstance(v, bool):
                merged_flags[k] = merged_flags.get(k, False) or v
            else:
                merged_flags[k] = v

    # Apply final flag rules
    if top5:
        if top5[0]["confidence"] < LOW_CONFIDENCE_THRESHOLD:
            merged_flags["low_confidence_match"] = True
        if len(top5) >= 2:
            delta = top5[0]["confidence"] - top5[1]["confidence"]
            if delta < CONFUSION_PAIR_DELTA:
                merged_flags["high_confusion_pair"] = True

    # Flag degraded results (fewer than expected passes succeeded)
    if len(passes) < passes_attempted:
        merged_flags["degraded_result"] = True
        merged_flags["passes_failed"] = passes_attempted - len(passes)

    # Use analysis from the most deterministic pass (temp=0.2)
    best_analysis = next(
        (p.analysis for p in passes if p.temperature == 0.2 and p.analysis),
        passes[0].analysis if passes else {}
    )

    return AggregatedResult(
        top5=top5,
        stability_scores=stability_scores,
        flags=merged_flags,
        analysis=best_analysis,
        pass_count=len(passes),
        passes_attempted=passes_attempted,
        latency_ms=0,  # set by caller
    )


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    if score >= 0.40:
        return "low"
    return "speculative"


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def run_orchestrated_identification(
    unknown_image_b64: str,
    comic_context: dict,
    system_prompt: str,
) -> AggregatedResult:
    """
    Full orchestration pipeline:
    1. Pre-filter candidates via PostgreSQL metadata
    2. Fetch reference images from R2 (via public URL)
    3. Fire 3 parallel Opus passes
    4. Aggregate and return results
    """
    start_ms = int(time.time() * 1000)

    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("Anthropic API not configured")

    client = _anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Step 1: Pre-filter
    candidates = prefilter_candidates(
        era_decade=comic_context.get("era_decade"),
        publisher=comic_context.get("publisher"),
        signature_location=comic_context.get("signature_location"),
    )
    logger.info("Candidates after pre-filter: %d", len(candidates))

    # Step 2: Fetch reference images via HTTP
    candidates = fetch_reference_images(candidates)
    logger.info("Candidates with images loaded: %d", len(candidates))

    if not candidates:
        raise ValueError("No candidates with reference images available")

    # Step 3: Sequential Opus passes (not parallel — 30K input tokens/min rate limit
    # on Opus 4.6 means parallel calls trigger 429 errors). Each pass takes ~20-30s,
    # so sequential execution naturally spaces requests within the rate limit window.
    pass_results: list[PassResult] = []
    failed_temps: list[float] = []

    for temp in PASS_TEMPERATURES:
        result = run_single_pass(
            temp, unknown_image_b64, candidates, comic_context, system_prompt, client,
        )
        if result.rankings:
            pass_results.append(result)
            logger.info(
                "Pass temp=%.1f complete — top result: %s (%.2f)",
                result.temperature,
                result.rankings[0].get("creator", "unknown"),
                result.rankings[0].get("confidence", 0),
            )
        else:
            failed_temps.append(temp)
            logger.warning(
                "Pass temp=%.1f FAILED — flags: %s",
                result.temperature, result.flags,
            )

    # Retry failed passes once (rate limit may have cleared by now)
    if failed_temps:
        logger.info("Retrying %d failed pass(es)...", len(failed_temps))
        for temp in failed_temps:
            result = run_single_pass(
                temp, unknown_image_b64, candidates, comic_context, system_prompt, client,
            )
            if result.rankings:
                pass_results.append(result)
                logger.info(
                    "Retry pass temp=%.1f SUCCEEDED — top: %s (%.2f)",
                    result.temperature,
                    result.rankings[0].get("creator", "unknown"),
                    result.rankings[0].get("confidence", 0),
                )
            else:
                logger.warning(
                    "Retry pass temp=%.1f FAILED again — flags: %s",
                    result.temperature, result.flags,
                )

    if len(pass_results) < len(PASS_TEMPERATURES):
        logger.warning(
            "DEGRADED: Only %d/%d passes succeeded",
            len(pass_results), len(PASS_TEMPERATURES),
        )

    if not pass_results:
        raise RuntimeError("All Opus passes failed (including retries)")

    # Step 4: Aggregate
    result = aggregate_passes(pass_results, passes_attempted=len(PASS_TEMPERATURES))
    result.latency_ms = int(time.time() * 1000) - start_ms

    logger.info(
        "Orchestration complete — top: %s (%.2f), latency: %dms, passes: %d/%d",
        result.top5[0]["creator"] if result.top5 else "none",
        result.top5[0]["confidence"] if result.top5 else 0,
        result.latency_ms,
        result.pass_count,
        result.passes_attempted,
    )

    return result


# ---------------------------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------------------------

def load_system_prompt() -> str:
    """Load the system prompt from the prompts/ directory."""
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "signature_identification_system.md"
    )
    try:
        with open(prompt_path) as f:
            content = f.read()
        # Extract just the SYSTEM PROMPT section
        if "## SYSTEM PROMPT" in content:
            start = content.index("## SYSTEM PROMPT") + len("## SYSTEM PROMPT")
            end = content.index("## IDENTIFICATION TASK PROMPT") if "## IDENTIFICATION TASK PROMPT" in content else len(content)
            return content[start:end].strip()
        return content
    except FileNotFoundError:
        logger.warning("Prompt file not found at %s, using inline fallback", prompt_path)
        return _FALLBACK_SYSTEM_PROMPT


_FALLBACK_SYSTEM_PROMPT = """You are an expert forensic document examiner specializing in authenticating
comic book creator signatures. You have decades of experience analyzing handwriting, stroke patterns,
pen pressure, letter formation, and overall gestural quality.

Analyze the unknown signature against the reference images provided. For each candidate creator,
compare structural features: letter construction, stroke direction, baseline angle, pen lifts,
flourishes, and overall proportions. Account for natural variation between signing sessions.

Return a JSON object with a "rankings" array of the top 5 most likely creators. Each entry must have:
- "rank": integer 1-5
- "creator": exact name string
- "confidence": float 0.0-1.0
- "match_evidence": array of specific structural similarities observed
- "contra_evidence": array of differences or concerns

Also include:
- "analysis": object with "methodology", "key_features_observed", "difficulty_assessment"
- "flags": object with boolean flags for edge cases

Confidence scores across all 5 rankings must sum to 1.0.
Be conservative — false positives (wrong identification) are worse than low confidence scores."""


@signatures_v2_bp.route("/match", methods=["POST"])
@require_auth
@require_approved
def match_signature():
    """
    POST /api/signatures/v2/match

    Body (multipart/form-data or JSON):
      - image: the unknown signature image file (multipart) OR
      - image_b64: base64-encoded image string (JSON)
      - publisher: optional string
      - era_decade: optional string (e.g. "1990s")
      - title: optional string
      - signature_location: optional string (cover|interior|unknown)
      - slab_label: optional string

    Returns:
      {
        "top5": [...],
        "flags": {...},
        "analysis": {...},
        "stability_scores": {...},
        "latency_ms": int,
        "pass_count": int
      }
    """
    # --- Parse image input ---
    image_b64 = None

    if request.content_type and "multipart" in request.content_type:
        if "image" not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        file = request.files["image"]
        image_bytes = file.read()
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        comic_context = {
            "publisher": request.form.get("publisher", "unknown"),
            "era_decade": request.form.get("era_decade", "unknown"),
            "title": request.form.get("title", "unknown"),
            "signature_location": request.form.get("signature_location", "unknown"),
            "slab_label": request.form.get("slab_label", "unknown"),
        }
    else:
        data = request.get_json(force=True) or {}
        image_b64 = data.get("image_b64")
        if not image_b64:
            return jsonify({"error": "No image_b64 provided"}), 400
        comic_context = {
            "publisher": data.get("publisher", "unknown"),
            "era_decade": data.get("era_decade", "unknown"),
            "title": data.get("title", "unknown"),
            "signature_location": data.get("signature_location", "unknown"),
            "slab_label": data.get("slab_label", "unknown"),
        }

    # --- Run orchestration ---
    try:
        system_prompt = load_system_prompt()
        result = run_orchestrated_identification(
            unknown_image_b64=image_b64,
            comic_context=comic_context,
            system_prompt=system_prompt,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except RuntimeError as e:
        logger.error("Orchestration runtime error: %s", e)
        return jsonify({"error": "Identification failed — all passes errored"}), 500
    except Exception as e:
        logger.exception("Unexpected orchestration error")
        return jsonify({"error": "Internal server error"}), 500

    # --- Log to DB (non-blocking — don't fail the response) ---
    try:
        unknown_key = f"unknown/{int(time.time())}.jpg"
        log_result_to_db(unknown_key, result, comic_context)
    except Exception as e:
        logger.warning("DB logging failed (non-fatal): %s", e)

    return jsonify({
        "top5": result.top5,
        "flags": result.flags,
        "analysis": result.analysis,
        "stability_scores": result.stability_scores,
        "latency_ms": result.latency_ms,
        "pass_count": result.pass_count,
        "passes_attempted": result.passes_attempted,
    })


@signatures_v2_bp.route("/match/stats", methods=["GET"])
@require_auth
@require_approved
def match_stats():
    """
    GET /api/signatures/v2/match/stats
    Returns recent identification accuracy stats from the review log.
    """
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS total_identifications,
                    COUNT(*) FILTER (WHERE needs_review = true) AS flagged_for_review,
                    AVG(top_confidence) AS avg_top_confidence,
                    AVG(latency_ms) AS avg_latency_ms,
                    COUNT(*) FILTER (WHERE (flags_json->>'low_confidence_match')::boolean = true)
                        AS low_confidence_count,
                    COUNT(*) FILTER (WHERE (flags_json->>'high_confusion_pair')::boolean = true)
                        AS confusion_pair_count
                FROM signature_identification_log
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            row = cur.fetchone()
            return jsonify(dict(row))
    finally:
        conn.close()
