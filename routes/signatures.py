"""
Signatures Blueprint - Signature identification and matching
Routes: /api/signatures/match, /api/signatures/identify, /api/signatures/db-stats, /api/signatures/signed-sales
"""
import os
import json
import base64
import requests as http_requests
from pathlib import Path
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

from auth import require_auth, require_approved

# Create blueprint
signatures_bp = Blueprint('signatures', __name__, url_prefix='/api/signatures')

# Module imports (set by wsgi.py)
ANTHROPIC_API_KEY = None
ANTHROPIC_AVAILABLE = False
anthropic = None

SIGNATURES_DIR = Path(__file__).parent.parent / 'signatures'
DB_PATH = SIGNATURES_DIR / 'signatures_db.json'


def init_modules(anthropic_key, anthropic_lib, anthropic_avail):
    """Initialize modules from wsgi.py"""
    global ANTHROPIC_API_KEY, anthropic, ANTHROPIC_AVAILABLE
    ANTHROPIC_API_KEY = anthropic_key
    anthropic = anthropic_lib
    ANTHROPIC_AVAILABLE = anthropic_avail


def load_signature_db():
    """Load the local signature reference database."""
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


# -------------------------------------------------------------------
# Route: Match an unknown signature against the reference database
# -------------------------------------------------------------------
@signatures_bp.route('/match', methods=['POST'])
@require_auth
@require_approved
def api_match_signature():
    """
    Match an unknown signature image against the reference database.

    Accepts:
        image: base64-encoded signature image
        media_type: MIME type (default image/jpeg)
        sale_id: optional — link result to an eBay/market sale

    Returns:
        matches: top 3 artist matches with confidence scores
        best_match: most likely artist name (or "UNKNOWN")
        best_confidence: confidence score 0.0-1.0
        is_confident_match: true if best_confidence >= 0.7
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({'error': 'Anthropic API not available'}), 503

    data = request.get_json() or {}
    unknown_b64 = data.get('image', '')
    media_type = data.get('media_type', 'image/jpeg')
    sale_id = data.get('sale_id')

    if not unknown_b64:
        return jsonify({'error': 'No signature image provided'}), 400

    # Load reference DB
    try:
        db = load_signature_db()
    except Exception as e:
        return jsonify({'error': f'Failed to load signature database: {e}'}), 500

    # Build the comparison prompt
    content = []

    # Unknown signature first
    content.append({"type": "text", "text": "UNKNOWN SIGNATURE TO IDENTIFY (Image 1):"})
    content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": unknown_b64}
    })

    # Add one reference per artist (best quality = largest file)
    ref_index = 2
    for artist in db["artists"]:
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
            img_media = get_media_type(best_image)

            content.append({"type": "text", "text": f"\nREFERENCE {ref_index} — {artist['name']}:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": img_media, "data": img_b64}
            })
            ref_index += 1

    # Matching instruction
    content.append({"type": "text", "text": """
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
"""})

    # Call Claude Vision
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.content[0].text

        # Parse JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response_text[json_start:json_end])
        else:
            return jsonify({'error': 'No valid JSON in API response', 'raw': response_text[:500]}), 500

    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse API response', 'raw': response_text[:500]}), 500
    except Exception as e:
        return jsonify({'error': f'API call failed: {str(e)}'}), 500

    # Optionally save match result to DB
    if sale_id and result.get('best_match') and result.get('best_confidence', 0) >= 0.5:
        try:
            _save_match_result(sale_id, result)
        except Exception as e:
            result['db_save_error'] = str(e)

    result['success'] = True
    return jsonify(result)


def _save_match_result(sale_id, result):
    """Save a match result to the signature_matches table."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        # Find or create the creator in creator_signatures
        artist_name = result['best_match']
        cur.execute("SELECT id FROM creator_signatures WHERE LOWER(creator_name) = LOWER(%s)", (artist_name,))
        row = cur.fetchone()

        if row:
            sig_id = row['id']
        else:
            # Create the creator entry
            cur.execute("""
                INSERT INTO creator_signatures (creator_name, source)
                VALUES (%s, 'signature_matcher_v1')
                RETURNING id
            """, (artist_name,))
            sig_id = cur.fetchone()['id']

        # Insert the match
        cur.execute("""
            INSERT INTO signature_matches (sale_id, signature_id, confidence, match_method)
            VALUES (%s, %s, %s, %s)
        """, (sale_id, sig_id, result.get('best_confidence', 0), 'claude_vision_v1'))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------------------
# Helpers: Two-step signature identification from full cover photos
# -------------------------------------------------------------------

def _fetch_and_encode_r2_image(image_url):
    """Fetch an image from R2 URL and return (base64_string, media_type)."""
    resp = http_requests.get(image_url, timeout=15)
    resp.raise_for_status()
    content_type = resp.headers.get('content-type', 'image/jpeg')
    b64 = base64.b64encode(resp.content).decode('utf-8')
    return b64, content_type


def _get_wildcard_artist_ids(cur, limit=10):
    """Get top N most-matched artist IDs from signature_matches (DB-driven wildcards)."""
    try:
        cur.execute("""
            SELECT signature_id, COUNT(*) as match_count
            FROM signature_matches
            GROUP BY signature_id
            ORDER BY match_count DESC
            LIMIT %s
        """, (limit,))
        return [row['signature_id'] for row in cur.fetchall()]
    except Exception:
        return []


def _fetch_reference_signatures(candidate_names, wildcard_ids=None):
    """
    Fetch reference images from PostgreSQL for candidate artists + wildcards.
    Returns dict keyed by artist name with id, images list, and best_image_url.
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return {}

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        # Get creators matching candidate names (case-insensitive)
        creator_ids = set()
        creator_map = {}  # id -> name

        if candidate_names:
            placeholders = ','.join(['%s'] * len(candidate_names))
            cur.execute(f"""
                SELECT id, creator_name FROM creator_signatures
                WHERE LOWER(creator_name) IN ({placeholders})
                AND archived_at IS NULL
            """, [n.lower() for n in candidate_names])
            for row in cur.fetchall():
                creator_ids.add(row['id'])
                creator_map[row['id']] = row['creator_name']

        # Add wildcard artist IDs
        if wildcard_ids:
            for wid in wildcard_ids:
                if wid not in creator_ids:
                    creator_ids.add(wid)

        # Fetch names for wildcard IDs we don't already have
        missing_ids = [wid for wid in (wildcard_ids or []) if wid not in creator_map]
        if missing_ids:
            placeholders = ','.join(['%s'] * len(missing_ids))
            cur.execute(f"""
                SELECT id, creator_name FROM creator_signatures
                WHERE id IN ({placeholders}) AND archived_at IS NULL
            """, missing_ids)
            for row in cur.fetchall():
                creator_map[row['id']] = row['creator_name']

        if not creator_ids:
            return {}

        # Fetch all reference images for these creators
        id_list = list(creator_ids)
        placeholders = ','.join(['%s'] * len(id_list))
        cur.execute(f"""
            SELECT creator_id, image_url, era, notes
            FROM signature_images
            WHERE creator_id IN ({placeholders})
            ORDER BY created_at DESC
        """, id_list)
        images = cur.fetchall()

        # Group by creator, select best (most recent = first) image
        result = {}
        for cid in creator_ids:
            name = creator_map.get(cid)
            if not name:
                continue
            creator_images = [img for img in images if img['creator_id'] == cid]
            if creator_images:
                result[name] = {
                    'id': cid,
                    'images': creator_images,
                    'best_image_url': creator_images[0]['image_url']
                }

        return result
    finally:
        cur.close()
        conn.close()


def _step1_detect_signatures(cover_b64, media_type):
    """
    Step 1: Use Haiku to detect signatures on a full cover photo.
    Returns parsed JSON with signatures_detected count and details.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": cover_b64}
        },
        {
            "type": "text",
            "text": """Analyze this comic book cover for handwritten signatures (NOT printed text, NOT logos, NOT credits).

TASK: Detect all handwritten signatures present on the cover.

For EACH signature found, provide:
1. Location on cover (e.g., "bottom right corner", "top left near logo")
2. Approximate number of characters/letters visible
3. Signature style (flowing cursive, angular print, block letters, monogram, etc.)
4. Ink color if distinguishable (black, blue, silver, gold, red, etc.)
5. Your best guess at who signed it — consider the comic's creators, era, and known convention signers
6. Confidence in your guess (0-100)

Return ONLY valid JSON:
{
    "signatures_detected": 2,
    "signatures": [
        {
            "index": 0,
            "location": "bottom right corner",
            "character_count": 7,
            "style": "flowing cursive",
            "ink_color": "black marker",
            "preliminary_id": "Jim Lee",
            "preliminary_confidence": 65,
            "reasoning": "Matches known Jim Lee signature style, he is the cover artist"
        }
    ],
    "notes": "Any other observations"
}

RULES:
- Only report actual handwritten signatures — NOT printed creator credits, logos, or title text
- If you cannot determine the signer, use "UNKNOWN" as preliminary_id
- Be conservative with confidence — 30-60% is fine for preliminary guesses
- Return empty signatures array if no handwritten signatures are found
- Maximum 5 signatures"""
        }
    ]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = {
        'haiku_input': response.usage.input_tokens,
        'haiku_output': response.usage.output_tokens
    }

    # Parse JSON
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1
    if json_start >= 0 and json_end > json_start:
        result = json.loads(response_text[json_start:json_end])
        return result, tokens
    else:
        return {"signatures_detected": 0, "signatures": [], "notes": "Failed to parse detection response"}, tokens


def _step2_match_signatures(cover_b64, media_type, detected_sigs, references):
    """
    Step 2: Use Sonnet to match detected signatures against reference images.
    Sends the original cover image + reference images for visual comparison.
    Returns parsed results with confidence scores per signature.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    content = []

    # Original cover image first
    content.append({"type": "text", "text": "COMIC COVER WITH SIGNATURES TO IDENTIFY:"})
    content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": cover_b64}
    })

    # Describe each detected signature for context
    sig_descriptions = []
    for sig in detected_sigs:
        sig_descriptions.append(
            f"  Signature {sig['index'] + 1}: {sig.get('location', 'unknown location')}, "
            f"{sig.get('style', 'unknown style')}, {sig.get('ink_color', 'unknown ink')}, "
            f"~{sig.get('character_count', '?')} characters"
        )
    content.append({
        "type": "text",
        "text": f"Detected {len(detected_sigs)} signature(s) on this cover:\n" + "\n".join(sig_descriptions)
    })

    # Add reference images
    ref_index = 1
    artist_names_in_prompt = []
    for artist_name, ref_data in references.items():
        best_url = ref_data['best_image_url']
        try:
            img_b64, img_media = _fetch_and_encode_r2_image(best_url)
            era_note = f" (era: {ref_data['images'][0].get('era', 'unknown')})" if ref_data['images'][0].get('era') else ""
            content.append({"type": "text", "text": f"\nREFERENCE {ref_index} — {artist_name}{era_note}:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": img_media, "data": img_b64}
            })
            artist_names_in_prompt.append(artist_name)
            ref_index += 1
        except Exception as e:
            print(f"[signatures/identify] Failed to fetch reference for {artist_name}: {e}")

    if not artist_names_in_prompt:
        return {"signatures": [], "error": "No reference images could be loaded"}, {'sonnet_input': 0, 'sonnet_output': 0}

    # Matching instructions
    content.append({"type": "text", "text": f"""
TASK: For each signature on the cover, compare it against the {len(artist_names_in_prompt)} reference signatures above.

EVALUATION CRITERIA:
1. Letter formation and stroke characteristics
2. Slant angle and baseline consistency
3. Overall flow, rhythm, and spacing
4. Distinctive flourishes, underlines, or marks
5. Pressure variation patterns
6. Character shapes and proportions

Return ONLY valid JSON:
{{
    "signatures": [
        {{
            "signature_index": 0,
            "location": "bottom right corner",
            "best_match": "Artist Name",
            "best_confidence": 0.85,
            "is_confident_match": true,
            "candidates": [
                {{
                    "artist_name": "Artist Name",
                    "confidence": 0.85,
                    "reasoning": "Strong match in letter formation and distinctive flourish"
                }},
                {{
                    "artist_name": "Another Artist",
                    "confidence": 0.30,
                    "reasoning": "Similar slant but different letter shapes"
                }}
            ]
        }}
    ],
    "overall_notes": "Summary observations"
}}

RULES:
- Provide up to 3 candidates per signature, sorted by confidence (highest first)
- Confidence: 0.8-1.0 (confident), 0.6-0.8 (likely), 0.3-0.6 (possible), <0.3 (unlikely)
- Set is_confident_match to true ONLY if best_confidence >= 0.7
- If no reference matches well, set best_match to "UNKNOWN" with confidence < 0.3
- Be conservative — a false positive is worse than a false negative
- You may also suggest artists NOT in the reference set if you recognize the signature
"""})

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text
    tokens = {
        'sonnet_input': response.usage.input_tokens,
        'sonnet_output': response.usage.output_tokens
    }

    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1
    if json_start >= 0 and json_end > json_start:
        result = json.loads(response_text[json_start:json_end])
        return result, tokens
    else:
        return {"signatures": [], "error": "Failed to parse matching response"}, tokens


def _record_identification(comic_id, results):
    """Save identification results to signature_matches table."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url or not comic_id:
        return

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        for sig in results.get('signatures', []):
            best = sig.get('best_match')
            confidence = sig.get('best_confidence', 0)
            if not best or best == 'UNKNOWN' or confidence < 0.5:
                continue

            cur.execute("SELECT id FROM creator_signatures WHERE LOWER(creator_name) = LOWER(%s)", (best,))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    INSERT INTO signature_matches (sale_id, signature_id, confidence, match_method)
                    VALUES (%s, %s, %s, %s)
                """, (comic_id, row['id'], confidence, 'claude_vision_v2_identify'))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[signatures/identify] Error recording identification: {e}")
    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------------------
# Route: Identify signatures on a full comic cover (two-step)
# -------------------------------------------------------------------
@signatures_bp.route('/identify', methods=['POST'])
@require_auth
@require_approved
def api_identify_signatures():
    """
    Two-step signature identification from a full cover photo.

    Step 1 (Haiku): Detect signatures, locations, and preliminary guesses.
    Step 2 (Sonnet): Match against reference images from the database.

    Accepts:
        image: base64-encoded full cover photo
        media_type: MIME type (default image/jpeg)
        comic_id: optional — link results to a comic in the collection

    Returns:
        signatures_found: number of signatures detected
        signatures: array of identified signatures with confidence scores
        tokens_used: breakdown of API token usage
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({'error': 'Anthropic API not available'}), 503

    data = request.get_json() or {}
    cover_b64 = data.get('image', '')
    media_type = data.get('media_type', 'image/jpeg')
    comic_id = data.get('comic_id')

    if not cover_b64:
        return jsonify({'error': 'No cover image provided'}), 400

    total_tokens = {}

    # ── Step 1: Haiku detection ──
    try:
        haiku_result, haiku_tokens = _step1_detect_signatures(cover_b64, media_type)
        total_tokens.update(haiku_tokens)
    except Exception as e:
        return jsonify({'error': f'Signature detection failed: {str(e)}'}), 500

    detected_sigs = haiku_result.get('signatures', [])
    num_found = haiku_result.get('signatures_detected', len(detected_sigs))

    # No signatures? Return early — skip Step 2
    if not detected_sigs:
        return jsonify({
            'success': True,
            'signatures_found': 0,
            'signatures': [],
            'haiku_notes': haiku_result.get('notes', ''),
            'tokens_used': total_tokens,
            'authentication_note': 'No signatures detected on this cover.'
        })

    # ── Gather candidate artist names from Haiku's guesses ──
    candidate_names = []
    for sig in detected_sigs:
        prelim = sig.get('preliminary_id', '')
        if prelim and prelim != 'UNKNOWN':
            candidate_names.append(prelim)

    # ── Get DB-driven wildcard artists (top 10 most-matched) ──
    wildcard_ids = []
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            wc_conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            wc_cur = wc_conn.cursor()
            wildcard_ids = _get_wildcard_artist_ids(wc_cur, limit=10)
            wc_cur.close()
            wc_conn.close()
    except Exception:
        pass  # Wildcards are optional — proceed without them

    # ── Fetch reference images from PostgreSQL/R2 ──
    try:
        references = _fetch_reference_signatures(candidate_names, wildcard_ids)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch reference signatures: {str(e)}'}), 500

    # If we have no references at all, return Haiku results only
    if not references:
        return jsonify({
            'success': True,
            'signatures_found': num_found,
            'signatures': [{
                'index': s['index'],
                'location': s.get('location', ''),
                'style': s.get('style', ''),
                'ink_color': s.get('ink_color', ''),
                'best_match': {
                    'artist_name': s.get('preliminary_id', 'UNKNOWN'),
                    'confidence': s.get('preliminary_confidence', 0) / 100.0,
                    'is_confident': False
                },
                'candidates': [],
                'note': 'No reference images available for matching — showing preliminary guess only'
            } for s in detected_sigs],
            'tokens_used': total_tokens,
            'authentication_note': 'For definitive verification, submit to CGC Signature Series or CBCS Verified Signature.'
        })

    # ── Step 2: Sonnet matching ──
    try:
        sonnet_result, sonnet_tokens = _step2_match_signatures(cover_b64, media_type, detected_sigs, references)
        total_tokens.update(sonnet_tokens)
    except Exception as e:
        # On Sonnet failure, return Haiku results as fallback
        return jsonify({
            'success': True,
            'signatures_found': num_found,
            'signatures': [{
                'index': s['index'],
                'location': s.get('location', ''),
                'style': s.get('style', ''),
                'ink_color': s.get('ink_color', ''),
                'best_match': {
                    'artist_name': s.get('preliminary_id', 'UNKNOWN'),
                    'confidence': s.get('preliminary_confidence', 0) / 100.0,
                    'is_confident': False
                },
                'candidates': [],
                'note': f'Reference matching failed ({str(e)}) — showing preliminary guess only'
            } for s in detected_sigs],
            'tokens_used': total_tokens,
            'authentication_note': 'For definitive verification, submit to CGC Signature Series or CBCS Verified Signature.'
        })

    # ── Merge Haiku detection info with Sonnet match results ──
    final_signatures = []
    sonnet_sigs = sonnet_result.get('signatures', [])

    for i, haiku_sig in enumerate(detected_sigs):
        # Find corresponding Sonnet result by index
        sonnet_sig = next((s for s in sonnet_sigs if s.get('signature_index') == i), None)

        if sonnet_sig:
            # Enrich candidates with artist_id from references
            candidates = sonnet_sig.get('candidates', [])
            for c in candidates:
                ref = references.get(c.get('artist_name'))
                if ref:
                    c['artist_id'] = ref['id']

            best_name = sonnet_sig.get('best_match', haiku_sig.get('preliminary_id', 'UNKNOWN'))
            best_conf = sonnet_sig.get('best_confidence', 0)
            best_ref = references.get(best_name)

            final_signatures.append({
                'index': i,
                'location': haiku_sig.get('location', sonnet_sig.get('location', '')),
                'style': haiku_sig.get('style', ''),
                'ink_color': haiku_sig.get('ink_color', ''),
                'character_count': haiku_sig.get('character_count'),
                'preliminary_id': haiku_sig.get('preliminary_id', ''),
                'preliminary_confidence': haiku_sig.get('preliminary_confidence', 0),
                'best_match': {
                    'artist_name': best_name,
                    'artist_id': best_ref['id'] if best_ref else None,
                    'confidence': best_conf,
                    'is_confident': best_conf >= 0.7
                },
                'candidates': candidates
            })
        else:
            # No Sonnet result for this signature — use Haiku data
            final_signatures.append({
                'index': i,
                'location': haiku_sig.get('location', ''),
                'style': haiku_sig.get('style', ''),
                'ink_color': haiku_sig.get('ink_color', ''),
                'character_count': haiku_sig.get('character_count'),
                'preliminary_id': haiku_sig.get('preliminary_id', ''),
                'preliminary_confidence': haiku_sig.get('preliminary_confidence', 0),
                'best_match': {
                    'artist_name': haiku_sig.get('preliminary_id', 'UNKNOWN'),
                    'artist_id': None,
                    'confidence': haiku_sig.get('preliminary_confidence', 0) / 100.0,
                    'is_confident': False
                },
                'candidates': []
            })

    # ── Optionally save results ──
    if comic_id:
        try:
            _record_identification(comic_id, {'signatures': final_signatures})
        except Exception as e:
            print(f"[signatures/identify] Error saving results: {e}")

    return jsonify({
        'success': True,
        'signatures_found': len(final_signatures),
        'signatures': final_signatures,
        'overall_notes': sonnet_result.get('overall_notes', ''),
        'tokens_used': total_tokens,
        'references_used': len(references),
        'authentication_note': 'For definitive verification, submit to CGC Signature Series or CBCS Verified Signature.'
    })


# -------------------------------------------------------------------
# Route: Get reference database stats
# -------------------------------------------------------------------
@signatures_bp.route('/db-stats', methods=['GET'])
def api_db_stats():
    """Return stats about the local signature reference database."""
    try:
        db = load_signature_db()
        return jsonify({
            'success': True,
            'version': db.get('version'),
            'total_artists': db['stats']['total_artists'],
            'total_images': db['stats']['total_images'],
            'quality_breakdown': {
                'high': db['stats']['high_quality'],
                'medium': db['stats']['medium_quality'],
                'low': db['stats']['low_quality']
            },
            'artists': [{'name': a['name'], 'quality': a['quality_rating'], 'image_count': len(a['images'])} for a in db['artists']],
            'missing_priority': db.get('missing_priority_artists', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------------------------
# Route: Query signed eBay sales (for testing matcher against real data)
# -------------------------------------------------------------------
@signatures_bp.route('/signed-sales', methods=['GET'])
def api_signed_sales():
    """
    Get eBay sales flagged as signed, with optional creator filter.
    Useful for testing the signature matcher against real sales images.

    Query params:
        creator: filter by creator name (partial match)
        limit: max results (default 20, max 100)
        has_image: only return sales with image_url (default true)
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'error': 'Database not configured'}), 503

    creator = request.args.get('creator', '')
    limit = min(int(request.args.get('limit', 20)), 100)
    has_image = request.args.get('has_image', 'true').lower() == 'true'

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        query = """
            SELECT id, raw_title, parsed_title, canonical_title, issue_number,
                   sale_price, sale_date, grade, grading_company, creators,
                   image_url, listing_url, ebay_item_id
            FROM ebay_sales
            WHERE is_signed = TRUE
        """
        params = []

        if has_image:
            query += " AND image_url IS NOT NULL AND image_url != ''"

        if creator:
            query += " AND (creators ILIKE %s OR raw_title ILIKE %s)"
            params.extend([f'%{creator}%', f'%{creator}%'])

        query += " ORDER BY sale_date DESC NULLS LAST LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        sales = cur.fetchall()

        # Convert dates to strings
        for s in sales:
            if s.get('sale_date'):
                s['sale_date'] = s['sale_date'].isoformat()

        # Get total count
        count_query = "SELECT COUNT(*) as total FROM ebay_sales WHERE is_signed = TRUE"
        if has_image:
            count_query += " AND image_url IS NOT NULL AND image_url != ''"
        cur.execute(count_query)
        total = cur.fetchone()['total']

        # Get creator breakdown
        cur.execute("""
            SELECT creators, COUNT(*) as count
            FROM ebay_sales
            WHERE is_signed = TRUE AND creators IS NOT NULL AND creators != ''
            GROUP BY creators
            ORDER BY count DESC
            LIMIT 30
        """)
        creator_breakdown = cur.fetchall()

        return jsonify({
            'success': True,
            'total_signed': total,
            'returned': len(sales),
            'sales': sales,
            'creator_breakdown': creator_breakdown
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------------------
# Route: Signed premium analysis — compare signed vs unsigned FMV
# -------------------------------------------------------------------
@signatures_bp.route('/premium-analysis', methods=['GET'])
def api_premium_analysis():
    """
    Analyze the price premium of signed comics vs unsigned.
    Professional-grade methodology:
      1. Time-windowed comparisons (±90 days) to control for market shifts
      2. Log-transformed premiums for symmetric distributions
      3. Bootstrap 95% confidence intervals
      4. Percentile-based outlier trimming
      5. Title-year disambiguation to prevent era collisions

    Query params:
        min_comps: minimum unsigned comparables required (default 3)
        min_price: minimum sale price to include (default 10)
        trim_pct: percentile to trim from each tail (default 5)
        time_window: days ± for time-matched comps (default 90, 0=no limit)
        bootstrap_n: number of bootstrap iterations (default 1000)
    """
    import math
    import random

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'error': 'Database not configured'}), 503

    min_comps = int(request.args.get('min_comps', 3))
    min_price = float(request.args.get('min_price', 10))
    trim_pct = float(request.args.get('trim_pct', 5))
    time_window = int(request.args.get('time_window', 90))
    bootstrap_n = min(int(request.args.get('bootstrap_n', 1000)), 5000)

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        # ── SQL: match each signed sale to individual unsigned sales ──
        # Returns individual pairs (not aggregated) so we can do proper
        # time-windowed matching and per-pair log ratios in Python.
        # This gives us much better statistical properties than matching
        # against pre-aggregated medians.
        time_clause_graded = ""
        time_clause_raw = ""
        if time_window > 0:
            # sale_date is a proper date column — subtraction gives integer days
            time_clause_graded = (
                f"AND ("
                f"  s.sale_date IS NULL "
                f"  OR u.sale_date IS NULL "
                f"  OR ABS(s.sale_date - u.sale_date) <= {time_window}"
                f")"
            )
            time_clause_raw = time_clause_graded

        cur.execute(f"""
            WITH signed AS (
                SELECT id, canonical_title, issue_number, grade, sale_price,
                       sale_date, creators, raw_title, title_year
                FROM ebay_sales
                WHERE is_signed = TRUE
                  AND canonical_title IS NOT NULL
                  AND issue_number IS NOT NULL
                  AND sale_price > %(min_price)s
            ),
            -- For each signed sale, find matching unsigned sales
            -- and compute per-signed-sale aggregates
            graded_matches AS (
                SELECT
                    s.id as signed_id, s.canonical_title, s.issue_number,
                    s.grade as signed_grade, s.sale_price as signed_price,
                    s.sale_date as signed_date,
                    s.creators, s.raw_title, s.title_year as signed_year,
                    COUNT(u.id) as comp_count,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY u.sale_price) as median_price,
                    AVG(u.sale_price) as mean_price,
                    MIN(u.sale_price) as min_price,
                    MAX(u.sale_price) as max_price,
                    ARRAY_AGG(u.sale_price ORDER BY u.sale_price) as all_prices
                FROM signed s
                JOIN ebay_sales u
                    ON u.canonical_title = s.canonical_title
                    AND u.issue_number = s.issue_number
                    AND u.is_signed = FALSE
                    AND u.grade IS NOT NULL
                    AND s.grade IS NOT NULL
                    AND ABS(s.grade - u.grade) <= 0.5
                    AND u.sale_price > %(min_price)s
                    AND (
                        (s.title_year IS NOT NULL AND u.title_year IS NOT NULL
                         AND ABS(s.title_year - u.title_year) <= 2)
                        OR s.title_year IS NULL
                        OR u.title_year IS NULL
                    )
                    {time_clause_graded}
                GROUP BY s.id, s.canonical_title, s.issue_number,
                         s.grade, s.sale_price, s.sale_date,
                         s.creators, s.raw_title, s.title_year
                HAVING COUNT(u.id) >= %(min_comps)s
            ),
            raw_matches AS (
                SELECT
                    s.id as signed_id, s.canonical_title, s.issue_number,
                    s.grade as signed_grade, s.sale_price as signed_price,
                    s.sale_date as signed_date,
                    s.creators, s.raw_title, s.title_year as signed_year,
                    COUNT(u.id) as comp_count,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY u.sale_price) as median_price,
                    AVG(u.sale_price) as mean_price,
                    MIN(u.sale_price) as min_price,
                    MAX(u.sale_price) as max_price,
                    ARRAY_AGG(u.sale_price ORDER BY u.sale_price) as all_prices
                FROM signed s
                JOIN ebay_sales u
                    ON u.canonical_title = s.canonical_title
                    AND u.issue_number = s.issue_number
                    AND u.is_signed = FALSE
                    AND u.grade IS NULL
                    AND u.graded = FALSE
                    AND s.grade IS NULL
                    AND u.sale_price > %(min_price)s
                    AND (
                        (s.title_year IS NOT NULL AND u.title_year IS NOT NULL
                         AND ABS(s.title_year - u.title_year) <= 2)
                        OR s.title_year IS NULL
                        OR u.title_year IS NULL
                    )
                    {time_clause_raw}
                GROUP BY s.id, s.canonical_title, s.issue_number,
                         s.grade, s.sale_price, s.sale_date,
                         s.creators, s.raw_title, s.title_year
                HAVING COUNT(u.id) >= %(min_comps)s
            )
            SELECT * FROM graded_matches
            UNION ALL
            SELECT * FROM raw_matches
            ORDER BY signed_price DESC
        """, {'min_price': min_price, 'min_comps': min_comps})

        rows = cur.fetchall()

        # Total signed count for coverage stats
        cur.execute("""
            SELECT COUNT(*) as total FROM ebay_sales
            WHERE is_signed = TRUE AND canonical_title IS NOT NULL
              AND issue_number IS NOT NULL AND sale_price > %s
        """, (min_price,))
        total_signed = cur.fetchone()['total']

        # ── Process rows with collision handling ──
        pairs = []
        skipped_collision = 0

        for row in rows:
            signed_price = float(row['signed_price'])
            comp_min = float(row['min_price'])
            comp_max = float(row['max_price'])
            comp_count = row['comp_count']
            median_price = float(row['median_price'])
            mean_price = float(row['mean_price'])
            all_prices = [float(p) for p in row['all_prices']] if row['all_prices'] else []

            collision_detected = comp_max > comp_min * 5 and comp_count >= 6

            if collision_detected and all_prices:
                log_mid = (math.log(comp_min) + math.log(comp_max)) / 2
                mid_price = math.exp(log_mid)

                lower_tier = [p for p in all_prices if p <= mid_price]
                upper_tier = [p for p in all_prices if p > mid_price]

                lower_median = sorted(lower_tier)[len(lower_tier)//2] if lower_tier else 0
                upper_median = sorted(upper_tier)[len(upper_tier)//2] if upper_tier else 0

                if abs(signed_price - lower_median) < abs(signed_price - upper_median):
                    tier = lower_tier
                else:
                    tier = upper_tier

                if len(tier) < min_comps:
                    skipped_collision += 1
                    continue

                median_price = sorted(tier)[len(tier)//2]
                mean_price = sum(tier) / len(tier)
                comp_count = len(tier)

            # ── Log-transformed premium ──
            # ln(signed/unsigned) gives symmetric distribution
            # More resistant to outliers than percentage premium
            if median_price > 0 and signed_price > 0:
                log_ratio = math.log(signed_price / median_price)
            else:
                log_ratio = 0.0

            premium_pct = ((signed_price - median_price) / median_price) * 100 if median_price > 0 else 0.0

            grade_val = float(row['signed_grade']) if row['signed_grade'] is not None else None

            pairs.append({
                'comic': f"{row['canonical_title']} #{row['issue_number']}",
                'grade': grade_val,
                'signed_price': signed_price,
                'unsigned_median': round(median_price, 2),
                'unsigned_mean': round(mean_price, 2),
                'num_comps': comp_count,
                'premium_vs_median': round(premium_pct, 1),
                'log_ratio': round(log_ratio, 4),
                'collision_adjusted': collision_detected,
                'creator': row.get('creators') or ''
            })

        # ── Helper functions ──
        def trim_outliers(values, pct):
            if not values or pct <= 0:
                return values
            n = len(values)
            cut = max(1, int(n * pct / 100))
            if cut * 2 >= n:
                return values
            s = sorted(values)
            return s[cut:-cut]

        def bootstrap_ci(values, n_iter=1000, ci=95):
            """Compute bootstrap confidence interval for the median."""
            if len(values) < 5:
                return None, None, None
            rng = random.Random(42)  # deterministic seed
            medians = []
            for _ in range(n_iter):
                sample = [rng.choice(values) for _ in range(len(values))]
                sample.sort()
                medians.append(sample[len(sample)//2])
            medians.sort()
            lo_idx = int(n_iter * (100 - ci) / 200)
            hi_idx = int(n_iter * (100 + ci) / 200)
            median_of_medians = medians[len(medians)//2]
            return round(medians[lo_idx], 1), round(median_of_medians, 1), round(medians[hi_idx], 1)

        # ── Aggregate stats ──
        skipped_no_comps = total_signed - len(rows) - skipped_collision

        if pairs:
            # Percentage premiums
            premiums_all = sorted([p['premium_vs_median'] for p in pairs])
            premiums_trimmed = trim_outliers(premiums_all, trim_pct)
            positive_all = [p for p in premiums_all if p > 0]
            positive_trimmed = [p for p in premiums_trimmed if p > 0]

            # Log ratios for geometric mean
            log_ratios_all = [p['log_ratio'] for p in pairs]
            log_ratios_trimmed = trim_outliers(sorted(log_ratios_all), trim_pct)

            # Geometric mean premium: exp(mean(log_ratios)) - 1
            geo_mean_all = (math.exp(sum(log_ratios_all) / len(log_ratios_all)) - 1) * 100 if log_ratios_all else 0
            geo_mean_trimmed = (math.exp(sum(log_ratios_trimmed) / len(log_ratios_trimmed)) - 1) * 100 if log_ratios_trimmed else 0

            # Bootstrap confidence intervals on trimmed premiums
            ci_lo, ci_median, ci_hi = bootstrap_ci(premiums_trimmed, n_iter=bootstrap_n)

            # Grade tiers
            graded_pairs = [p for p in pairs if p['grade'] is not None]
            raw_pairs = [p for p in pairs if p['grade'] is None]
            high_grade = [p for p in graded_pairs if p['grade'] and p['grade'] >= 9.0]
            mid_grade = [p for p in graded_pairs if p['grade'] and 7.0 <= p['grade'] < 9.0]
            low_grade = [p for p in graded_pairs if p['grade'] and p['grade'] < 7.0]

            def tier_stats(tier_pairs):
                if not tier_pairs:
                    return None
                prems = sorted([p['premium_vs_median'] for p in tier_pairs])
                logs = sorted([p['log_ratio'] for p in tier_pairs])
                geo = (math.exp(sum(logs) / len(logs)) - 1) * 100 if logs else 0
                result = {
                    'count': len(prems),
                    'mean': round(sum(prems) / len(prems), 1),
                    'median': round(prems[len(prems)//2], 1),
                    'geometric_mean': round(geo, 1),
                    'min': round(min(prems), 1),
                    'max': round(max(prems), 1)
                }
                if len(prems) >= 10:
                    trimmed = trim_outliers(prems, trim_pct)
                    trimmed_logs = trim_outliers(logs, trim_pct)
                    if trimmed:
                        result['trimmed_mean'] = round(sum(trimmed) / len(trimmed), 1)
                        result['trimmed_median'] = round(trimmed[len(trimmed)//2], 1)
                        result['trimmed_geo_mean'] = round((math.exp(sum(trimmed_logs) / len(trimmed_logs)) - 1) * 100, 1) if trimmed_logs else None
                        result['trimmed_count'] = len(trimmed)
                        t_ci_lo, t_ci_med, t_ci_hi = bootstrap_ci(trimmed, n_iter=bootstrap_n)
                        if t_ci_lo is not None:
                            result['ci_95'] = [t_ci_lo, t_ci_hi]
                return result

            summary = {
                'total_signed_sales': total_signed,
                'matched_pairs': len(pairs),
                'skipped_no_comps': skipped_no_comps,
                'skipped_collision': skipped_collision,
                'trim_pct': trim_pct,
                'time_window_days': time_window,
                'overall_raw': {
                    'mean_premium': round(sum(premiums_all) / len(premiums_all), 1),
                    'median_premium': round(premiums_all[len(premiums_all)//2], 1),
                    'geometric_mean_premium': round(geo_mean_all, 1),
                    'min_premium': round(min(premiums_all), 1),
                    'max_premium': round(max(premiums_all), 1),
                    'positive_count': len(positive_all),
                    'positive_pct': round(len(positive_all) / len(premiums_all) * 100, 1)
                },
                'overall_trimmed': {
                    'mean_premium': round(sum(premiums_trimmed) / len(premiums_trimmed), 1) if premiums_trimmed else None,
                    'median_premium': round(premiums_trimmed[len(premiums_trimmed)//2], 1) if premiums_trimmed else None,
                    'geometric_mean_premium': round(geo_mean_trimmed, 1),
                    'min_premium': round(min(premiums_trimmed), 1) if premiums_trimmed else None,
                    'max_premium': round(max(premiums_trimmed), 1) if premiums_trimmed else None,
                    'positive_count': len(positive_trimmed),
                    'positive_pct': round(len(positive_trimmed) / len(premiums_trimmed) * 100, 1) if premiums_trimmed else None,
                    'count': len(premiums_trimmed),
                    'ci_95_median': [ci_lo, ci_hi] if ci_lo is not None else None
                },
                'by_grade_tier': {
                    'high_grade_9plus': tier_stats(high_grade),
                    'mid_grade_7to9': tier_stats(mid_grade),
                    'low_grade_under7': tier_stats(low_grade),
                    'raw_ungraded': tier_stats(raw_pairs)
                }
            }
        else:
            summary = {
                'total_signed_sales': total_signed,
                'matched_pairs': 0,
                'skipped_no_comps': skipped_no_comps,
                'skipped_collision': skipped_collision,
                'note': 'No matched pairs found. Need more unsigned comparables.'
            }

        pairs.sort(key=lambda x: -x['premium_vs_median'])

        return jsonify({
            'success': True,
            'summary': summary,
            'pairs': pairs[:50],
            'methodology': {
                'description': 'Each signed sale matched against time-windowed unsigned sales of same title+issue at same grade (±0.5).',
                'time_window': f'Unsigned comps must be within ±{time_window} days of signed sale date (0=no limit). Controls for market fluctuations.',
                'log_transform': 'Geometric mean computed via ln(signed/unsigned) for symmetric premium distribution. More robust than arithmetic mean for price ratios.',
                'confidence_intervals': f'Bootstrap 95% CI on trimmed median ({bootstrap_n} iterations, seed=42). Shows statistical certainty of premium estimate.',
                'collision_handling': 'When unsigned comps span >5x price range with 6+ sales, prices split into tiers; signed sale matched to nearest tier.',
                'outlier_trimming': f'Top and bottom {trim_pct}% of premiums removed. Adjustable via ?trim_pct=N.',
                'min_comps': min_comps,
                'min_price': min_price
            }
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
    finally:
        cur.close()
        conn.close()
