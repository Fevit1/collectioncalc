"""
Comic Extraction Module
Extracts comic book information from photos using Claude Vision.
"""

import os
import base64
import json
from io import BytesIO
from models import call_with_fallback

try:
    import anthropic
    # Resilience layer (Commit 2): bound every extraction call so a slow/overloaded
    # Anthropic backend can't turn /api/extract into a multi-minute hang. timeout=30s
    # caps a single attempt; max_retries=1 gives one automatic retry on a transient
    # 429/5xx/timeout, then raises anthropic.APITimeoutError (handled in
    # extract_from_base64 -> "Request timed out", which the client maps to honest
    # "busy" copy). Worst case ~60s of API time, not an open-ended wait.
    _client = anthropic.Anthropic(
        api_key=os.environ.get('ANTHROPIC_API_KEY'),
        timeout=30.0,
        max_retries=1,
    )
    ANTHROPIC_AVAILABLE = True
except Exception:
    _client = None
    ANTHROPIC_AVAILABLE = False

# Try to import barcode scanning library
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    from PIL import Image
    BARCODE_SCANNING_AVAILABLE = True
except ImportError:
    BARCODE_SCANNING_AVAILABLE = False
    print("pyzbar not available - barcode scanning disabled")

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')  # kept for backward compat checks

# PIL for server-side orientation normalization (independent of pyzbar/barcode,
# so it works even if barcode scanning is unavailable).
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# HEIC/HEIF decode (iPhone default capture format). Registering the opener
# teaches PIL to open HEIC, so every path that decodes through this module
# (normalize_orientation_b64 → /api/extract, /api/grade, /api/messages) gets
# HEIC support and re-emits JPEG — the Anthropic API and Rekognition never see
# HEIC bytes. Degrades gracefully: without the package, HEIC uploads fail the
# normalize step with the existing fail-loud ValueError.
HEIF_SUPPORTED = False
if PIL_AVAILABLE:
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        HEIF_SUPPORTED = True
    except ImportError:
        print("[Extraction] pillow-heif not installed — HEIC/HEIF uploads will not decode")


def normalize_orientation_b64(base64_data: str, assume_portrait: bool = False) -> str:
    """Authoritative server-side orientation fix.

    The Anthropic vision API ignores EXIF orientation and reads raw pixels, and
    the primary upload path (app.html) sends the original phone photo
    un-normalized. We must hand the model an upright image regardless of what the
    client did, or a 90deg-rotated cover gets read as garbled/hallucinated text.

    Two failure modes, handled in order:
      1. Rotated WITH an EXIF orientation tag (typical phone → app.html upload):
         `exif_transpose` rotates the pixels the correct way and strips the tag.
      2. Hard-rotated WITHOUT EXIF (e.g. images re-exported by Google Photos /
         other tools that drop the tag without baking in the rotation): there is
         no metadata to act on. When `assume_portrait` is set (extraction only
         ever looks at the front cover, and comic covers are always portrait), a
         still-landscape image is rotated 90deg counter-clockwise to portrait.
         CCW is the empirically-correct direction for the observed phone output;
         it is best-effort for arbitrary no-EXIF inputs. (A barcode-orientation
         signal could make this direction-exact later — see scan_barcode.)

    Do NOT pass assume_portrait=True for images that may legitimately be
    landscape (e.g. centerfold/two-page spreads).

    Returns normalized base64 (always re-encoded JPEG). Raises ValueError if the
    image can't be decoded (fail loud — never forward a garbage payload).
    """
    if not PIL_AVAILABLE:
        print("[Extraction] PIL unavailable — cannot normalize orientation; sending image as-is")
        return base64_data
    # Tolerate a data-URL prefix (data:image/...;base64,) — matches the defensive
    # split(',') pattern used elsewhere; reserve fail-loud for truly bad images.
    if base64_data.startswith('data:') and ',' in base64_data:
        base64_data = base64_data.split(',', 1)[1]
    try:
        raw = base64.b64decode(base64_data)
        img = Image.open(BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # mode 1: rotate per EXIF, drop the tag
        if assume_portrait and img.width > img.height:
            # mode 2: no usable EXIF but still landscape — a front cover is never
            # landscape, so this is a sideways photo. Rotate to portrait (CCW).
            print(f"[Extraction] Cover still landscape ({img.width}x{img.height}) after EXIF "
                  f"normalization — rotating 90deg CCW to portrait")
            img = img.rotate(90, expand=True)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=92)
        return base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception as e:
        raise ValueError(f"Could not decode/normalize image: {e}")


# Photo types whose CORRECT orientation is LANDSCAPE — never force-rotated to
# portrait. A comic centerfold is a two-page spread, legitimately wider than tall;
# everything else in the grading flow (front, back, spine) is portrait when shot
# correctly. Unknown/missing type defaults to portrait (the front-cover main path).
_LANDSCAPE_PHOTO_TYPES = {'centerfold', 'center', 'interior'}


def assume_portrait_for(photo_type: str) -> bool:
    """Map a grading photo type to the assume_portrait flag for orientation
    normalization. centerfold -> False (EXIF-only); front/back/spine/unknown -> True."""
    return (photo_type or 'front').strip().lower() not in _LANDSCAPE_PHOTO_TYPES


def normalize_for_photo_type(base64_data: str, photo_type: str = 'front') -> str:
    """Photo-type-aware server-side orientation normalization for grading inputs.
    Keeps the type->assume_portrait policy in ONE place so /api/extract and
    /api/messages stay consistent. front/back/spine assume portrait; centerfold is
    EXIF-only (never force-rotated). Always emits JPEG; raises ValueError on a
    truly undecodable image (same contract as normalize_orientation_b64)."""
    return normalize_orientation_b64(base64_data, assume_portrait=assume_portrait_for(photo_type))


def rotate_180_b64(base64_data: str) -> str:
    """Rotate a base64 image 180 deg; return base64 JPEG. Used by the extraction
    low-confidence fallback — a 180 deg flip is invisible to the dimension-based
    orientation heuristic in normalize_orientation_b64. Tolerates a data-URL
    prefix. Raises if PIL is missing or the image can't be decoded (the caller
    treats any failure as 'skip the retry, keep pass 1')."""
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL unavailable — cannot rotate 180")
    if base64_data.startswith('data:') and ',' in base64_data:
        base64_data = base64_data.split(',', 1)[1]
    raw = base64.b64decode(base64_data)
    img = Image.open(BytesIO(raw))
    img = img.rotate(180, expand=True)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=92)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def scan_barcode(image_data: bytes) -> dict:
    """
    Scan image for UPC barcode and extract the 5-digit supplement.
    Tries all 4 rotations (0°, 90°, 180°, 270°) to find barcode.
    
    Args:
        image_data: Raw image bytes (JPEG, PNG, etc.)
    
    Returns:
        dict with barcode info or None if not found
    """
    if not BARCODE_SCANNING_AVAILABLE:
        return None
    
    try:
        # Open image with PIL
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary (pyzbar works better with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Try scanning at different rotations (0°, 90°, 180°, 270°)
        all_barcodes = []
        rotation_found = 0
        
        for rotation in [0, 90, 180, 270]:
            if rotation == 0:
                rotated = image
            else:
                rotated = image.rotate(-rotation, expand=True)  # Negative for clockwise
            
            # Scan for barcodes (UPC-A, EAN-13, UPC-E, EAN-5 for supplement)
            found = pyzbar.decode(rotated, symbols=[
                ZBarSymbol.UPCA, ZBarSymbol.EAN13, ZBarSymbol.UPCE, 
                ZBarSymbol.EAN5, ZBarSymbol.CODE128
            ])
            
            if not found:
                # Try without symbol filter as fallback
                found = pyzbar.decode(rotated)
            
            if found:
                all_barcodes = found
                rotation_found = rotation
                print(f"[Barcode] Found {len(found)} barcode(s) at {rotation}° rotation")
                break
        
        if not all_barcodes:
            return None
        
        # Process found barcodes
        upc_main = None
        upc_addon = None
        barcode_type = None
        
        for barcode in all_barcodes:
            data = barcode.data.decode('utf-8')
            btype = barcode.type
            
            print(f"[Barcode] Found {btype}: {data}")
            
            # EAN-5 is the 5-digit supplement we want
            if btype == 'EAN5' or (len(data) == 5 and data.isdigit()):
                upc_addon = data
                print(f"[Barcode] 5-digit supplement found: {data}")
            
            # UPC-A is 12 digits
            elif btype == 'UPCA' or (len(data) == 12 and data.isdigit()):
                upc_main = data
                barcode_type = 'UPCA'
            
            # EAN-13 is 13 digits
            elif btype == 'EAN13' or (len(data) == 13 and data.isdigit()):
                upc_main = data
                barcode_type = 'EAN13'
            
            # Some scanners return combined UPC + addon (17 digits)
            elif len(data) >= 17 and data.isdigit():
                upc_main = data[:12]
                upc_addon = data[12:17]
                barcode_type = 'UPCA+EAN5'
                print(f"[Barcode] Combined code split: main={upc_main}, addon={upc_addon}")
        
        if upc_main or upc_addon:
            return {
                'upc_main': upc_main,
                'upc_addon': upc_addon,
                'type': barcode_type,
                'rotation': rotation_found,
                'supplement': upc_addon  # Alias for backward compatibility
            }
        
        return None
        
    except Exception as e:
        print(f"[Barcode] Scan error: {e}")
        return None


def decode_barcode(digits: str) -> dict:
    """
    Decode 5-digit UPC supplement code from comic book barcode.
    
    Standard format (IIICP) since Diamond 2008/2009:
        - Digits 1-3: Issue number (001-999)
        - Digit 4: Cover variant (1=A, 2=B, 3=C, etc.)
        - Digit 5: Printing (1=1st, 2=2nd, etc.)
    
    Args:
        digits: 5-digit barcode supplement string
    
    Returns:
        dict with decoded info, or None if invalid
    """
    if not digits or len(digits) != 5 or not digits.isdigit():
        return None
    
    cover_num = int(digits[3])
    printing_num = int(digits[4])
    
    return {
        'issue': int(digits[0:3]),
        'cover': cover_num,
        'cover_letter': chr(64 + cover_num) if cover_num > 0 else None,  # 1=A, 2=B, etc.
        'printing': printing_num,
        'is_variant': cover_num > 1,      # True if not cover A
        'is_reprint': printing_num > 1,   # True if not 1st printing
    }


# Vision Guide prompt - JSON template FIRST for better compliance
EXTRACTION_PROMPT = """Analyze this comic book image and extract information.

YOU MUST RETURN EXACTLY THIS JSON STRUCTURE - NO OTHER FIELDS ALLOWED:
```json
{
  "is_comic_cover": true,
  "title": "",
  "issue": "",
  "issue_type": "",
  "publisher": "",
  "year": null,
  "writer": "",
  "artist": "",
  "edition": "",
  "printing": "",
  "is_facsimile": false,
  "cover": "",
  "variant": "",
  "barcode_digits": "",
  "is_slabbed": false,
  "slab_cert_number": "",
  "slab_company": "",
  "slab_grade": "",
  "slab_label_type": "",
  "suggested_grade": "",
  "defects": [],
  "signatures": [],
  "grade_reasoning": ""
}
```

FIELD DEFINITIONS:

IMAGE VALIDATION (check FIRST):
- is_comic_cover: true if this image shows a comic book cover (front cover, slabbed comic, or trade paperback). false if it's not a comic (random photo, blank image, non-comic book, finger over lens, etc.). If false, set all other fields to their defaults and return immediately.

IDENTIFICATION FIELDS:
- title: Comic book title (largest text on cover). Main series name only - NOT "Annual" or "Special" (those go in issue_type).
- issue: Issue number. Look for "#" symbol, typically TOP-LEFT near price. IGNORE prices (60¢, $1.00, 25p). Just the number, no # symbol.
- issue_type: Check for these indicators:
  * "Annual" or "ANNUAL" → "Annual"
  * "King-Size Special" or "KING-SIZE SPECIAL" → "Annual"
  * "Giant-Size" or "GIANT-SIZE" → "Giant-Size"
  * "Special" or "SPECIAL" (standalone) → "Special"
  * "Special Edition" → "Special Edition"
  * None found → "Regular"
- publisher: Publisher name (Marvel, DC, Image, etc.)
- year: Publication year. Check copyright/indicia first. If not visible, use your knowledge of comic publication history to determine the year. Only return null if you truly cannot determine it.
- writer: Writer credits on cover ("Written by NAME", "WRITER: NAME"). Empty string if not found.
- artist: Artist credits on cover ("Art by NAME", "ARTIST: NAME", "PENCILS"). Empty string if not found.
- edition: Check BOTTOM-LEFT CORNER. UPC BARCODE = "newsstand". ARTWORK/LOGO = "direct". Unclear = "unknown".
- printing: Look for "2nd Printing", "3rd Print", etc. Return "1st" if no indicator, otherwise "2nd", "3rd", etc.
- is_facsimile: true if "FACSIMILE", "FACSIMILE EDITION", or "FACSIMILE REPRINT" appears anywhere. These are modern reprints worth $5-15.
- cover: Variant indicators like "Cover A", "Cover B", "Variant Cover", "1:25", "Virgin", etc. Empty string if none.
- variant: Other variant description ("McFarlane variant", "Artgerm cover"). Empty string if none.
- barcode_digits: IMPORTANT - Find the 5-DIGIT ADD-ON CODE next to the main UPC barcode (bottom-left). It's a separate smaller barcode to the RIGHT of the main UPC. The 5 digits may be printed VERTICALLY or horizontally. Examples: "00111", "00121", "00412". Extract ONLY these 5 digits. Empty string if not readable. Do NOT return the main 12-digit UPC.

SLAB DETECTION FIELDS (for professionally graded/encapsulated comics):
- is_slabbed: true if the comic is in a hard plastic grading case (slab) from CGC, CBCS, PGX, etc. Look for: a colored label at the top of a rigid plastic holder, certification numbers, and the comic sealed inside.
- slab_cert_number: The certification/serial number printed on the slab label. This is typically a long number (e.g., "4375804009", "1234567001"). It may appear as a barcode on the label as well. Extract the full number. Empty string if not slabbed or not readable.
- slab_company: The grading company name from the label: "CGC", "CBCS", "PGX", or other. Empty string if not slabbed.
- slab_grade: The numeric grade shown on the slab label (e.g., "9.8", "9.6", "8.0"). This is the OFFICIAL grade, not your assessment. Empty string if not slabbed.
- slab_label_type: The type of slab label, which significantly affects value. Identify by label COLOR and text:
  * "universal" — Blue label (CGC) or similar. Standard grading, no signatures or restoration.
  * "signature_series" — Yellow label (CGC). Signature was WITNESSED by a CGC representative. Big value premium.
  * "qualified" — Green label (CGC). Has a notable defect noted on label (missing coupon, cut coupon, etc.) but graded as if defect weren't there.
  * "restored" — Purple label (CGC). Comic has been professionally or amateur restored/repaired. Generally reduces value.
  * "pedigree" — Gold label (CGC). From a recognized exceptional collection. Rare, adds premium.
  * "signature_restored" — Yellow/Purple combo label. Witnessed signature on a restored book.
  * "signature_qualified" — Yellow/Green combo label. Witnessed signature with a qualifying defect.
  * "conserved" — Grey or Yellow/Grey label. Book has been conserved (non-invasive preservation).
  * "cgc_jsa" — CGC x JSA label. Unwitnessed signature authenticated by James Spence Authentication.
  For CBCS: use the same categories (CBCS uses similar color coding — blue=universal, yellow=verified signature, green=qualified, purple=restored).
  Empty string if not slabbed or label type cannot be determined.

CONDITION FIELDS:
- suggested_grade: Based on visible condition: MT, NM, VF, FN, VG, G, FR, or PR. Be conservative.
- defects: Array of defects ON THE COMIC (not bag/sleeve). Examples: "Tear on front cover", "Spine roll", "Corner wear". Empty array [] if none.
- signatures: Array of signatures visible. Note if creator or unknown. Examples: "Creator signature - Jim Lee", "Unknown signature". Empty array [] if none.
- grade_reasoning: Brief explanation. Example: "NM - Sharp corners, clean colors, no visible defects"

GRADE GUIDE:
- MT (10.0): Perfect
- NM (9.4): Nearly perfect, minor imperfections only
- VF (8.0): Minor wear, small stress marks OK
- FN (6.0): Moderate wear, minor creases OK
- VG (4.0): Significant wear, small tears/creases
- G (2.0): Heavy wear, larger creases
- FR (1.5): Major wear, tears, pieces missing
- PR (1.0): Severe damage

IMPORTANT RULES:
1. Do NOT confuse prices (60¢, $1.50) with issue numbers
2. ALWAYS check for "Annual", "Giant-Size", "Special" - these are different series
3. ALWAYS check for "FACSIMILE" - these are reprints worth much less
4. Ignore bag/sleeve artifacts - assess the comic itself
5. Creator signatures ADD value, random writing is a defect
6. If image is UPSIDE-DOWN, add "is_upside_down": true
7. SERIES DISAMBIGUATION: Many titles have had multiple series runs (e.g., Ghost Rider, Spider-Man, X-Men). Do NOT assume issue #1 is the original series. Use ALL available clues to determine the correct series run:
   - Publication year from cover date, indicia, or copyright
   - Art style (modern vs vintage)
   - Publisher logo era (e.g., Marvel corner box styles changed over decades)
   - Price point ($3.99+ suggests 2010s-2020s, 60¢ suggests 1980s, 12¢ suggests 1960s)
   - Paper/printing quality (modern glossy vs vintage newsprint)
   - Creator names (if visible, use their known active periods)
   - Barcode format (modern UPC vs vintage without barcode)
   If you can determine the year, use it to identify the EXACT series run. Include the volume or series year in the title if needed to disambiguate (e.g., "Ghost Rider (2022)" vs "Ghost Rider (1973)").
8. SLABBED COMICS: If the comic is in a grading slab (rigid plastic case with label), set is_slabbed to true and extract the cert number, company, and grade from the label. For slabbed comics, use the LABEL grade as suggested_grade (not your own assessment), and note "Professionally graded" in grade_reasoning.
9. GRADING CONSISTENCY: Be precise and systematic when grading. Evaluate these specific criteria in order:
   - Corners: Sharp (NM+), very slight rounding (NM), visible rounding (VF), bent/creased (FN or lower)
   - Spine: Tight (NM+), minor stress lines (NM/VF), stress lines (VF), roll or creases (FN or lower)
   - Cover: Clean/glossy (NM+), minor wear (NM/VF), noticeable wear/scuffing (FN), heavy wear (VG or lower)
   - Structural: No tears/missing pieces (VF+), small tears (FN), significant damage (VG or lower)
   Assign a NUMERIC grade (e.g., 9.4, 8.0, 6.5) rather than just a label. The grade_reasoning MUST reference specific observed defects or their absence.

Return ONLY the JSON object with ALL fields shown above. Use empty string "" for unknown text fields, null for year, empty array [] for defects/signatures.

<!-- FUTURE: DETAILED SIGNATURE ANALYSIS (commented out for now)
When signature detection is re-enabled, add these fields to the JSON schema:
- signature_detected: boolean - true if ANY handwriting/signature found
- signature_analysis: If signature_detected is true, provide this object (otherwise null):
  {
    "creators": [{"name": "Full Name", "role": "Artist/Writer/Inker/Colorist"}],
    "confidence_scores": [{"name": "Full Name", "confidence": 55, "reasoning": "brief reason"}],
    "most_likely_signer": {"name": "Name", "confidence": 55},
    "signature_characteristics": "Location on cover, ink color (gold/silver/black/blue), style"
  }

SIGNATURE DETECTION INSTRUCTIONS (Two-step process):
STEP 1 - SCAN: Systematically scan the ENTIRE cover for any handwriting or signatures:
- Sky, moon, or background areas
- Across character faces or bodies
- Title/logo area
- All four corners
- Margins and edges
- Near creator credits
Look for: Gold/silver metallic ink (very common), black sharpie, blue/red marker, pen signatures

STEP 2 - ANALYZE: If you found ANYTHING that looks like handwriting/signature:
- Note exactly where it is located
- Describe its appearance (ink color, style)
- Look at creator credits at bottom of cover
- Compare signature to creator names to estimate who signed

When assigning confidence: Any creator could have signed. Give roughly equal initial weight to all listed creators. Increase confidence only if legible letters clearly match a specific name.
-->"""


def extract_from_photo(image_data: bytes, filename: str = "comic.jpg") -> dict:
    """
    Extract comic information from a photo using Claude Vision.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename (used to determine media type)
    
    Returns:
        dict with extracted fields or error
    """
    if not ANTHROPIC_AVAILABLE or not _client:
        return {"success": False, "error": "Anthropic SDK not available"}

    # Determine media type from filename
    ext = filename.lower().split('.')[-1] if '.' in filename else 'jpg'
    media_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'heic': 'image/heic'
    }
    media_type = media_type_map.get(ext, 'image/jpeg')
    
    # Convert to base64
    base64_data = base64.b64encode(image_data).decode('utf-8')
    
    return extract_from_base64(base64_data, media_type)


# Default field set applied to every parsed extraction so downstream code can rely
# on every key existing. (Pulled out of extract_from_base64 so both the first pass
# and the 180 deg re-read apply identical defaults.)
_EXTRACTION_DEFAULTS = {
    "is_comic_cover": True,
    "title": "",
    "issue": "",
    "issue_type": "Regular",
    "publisher": "",
    "year": None,
    "writer": "",
    "artist": "",
    "edition": "unknown",
    "printing": "1st",
    "is_facsimile": False,
    "cover": "",
    "variant": "",
    "barcode_digits": "",
    "is_slabbed": False,
    "slab_cert_number": "",
    "slab_company": "",
    "slab_grade": "",
    "slab_label_type": "",
    "suggested_grade": "",
    "defects": [],
    "signatures": [],
    "grade_reasoning": ""
}


def _run_vision_pass(b64: str, media_type: str):
    """One Claude vision extraction pass. Returns (parsed_dict_or_None, raw_text).
    None means the response had no parseable JSON. Defaults are applied so the
    caller sees a complete dict. No barcode/orientation logic here — that lives in
    extract_from_base64 so the 180 deg fallback can re-run JUST this pass."""
    import re
    response = call_with_fallback(
        _client, 'sonnet',
        max_tokens=1000,
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": EXTRACTION_PROMPT}
            ]
        }]
    )
    text_content = ""
    for block in response.content:
        if block.type == "text":
            text_content += block.text
    json_match = re.search(r'\{[\s\S]*\}', text_content)
    if not json_match:
        return None, text_content
    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError:
        # Malformed JSON (e.g. truncated at max_tokens) counts as 'unparseable' so
        # the 180 deg low-confidence fallback gets a chance, instead of hard-failing
        # via the outer except and skipping the retry entirely.
        return None, text_content
    for key, default_value in _EXTRACTION_DEFAULTS.items():
        if key not in parsed:
            parsed[key] = default_value
    return parsed, text_content


def _extraction_score(extracted) -> int:
    """Confidence proxy for an extraction pass (higher is better). Decides whether
    a 180 deg re-read beat the original orientation."""
    if not extracted:
        return -1
    score = 0
    if extracted.get('is_comic_cover', True):
        score += 2
    if (extracted.get('title') or '').strip():
        score += 2
    if (extracted.get('issue') or '').strip():
        score += 1
    if extracted.get('is_upside_down') is True:
        score -= 1
    return score


def _extraction_low_confidence(extracted):
    """Is a first-pass extraction weak enough to warrant a one-shot 180 deg
    re-read? Returns (is_low, reason)."""
    if not extracted:
        return True, 'unparseable'
    if extracted.get('is_upside_down') is True:
        return True, 'model_flagged_upside_down'
    if not extracted.get('is_comic_cover', True):
        return True, 'not_recognized_as_cover'
    if not (extracted.get('title') or '').strip():
        return True, 'no_title_read'
    return False, None


def extract_from_base64(base64_data: str, media_type: str = "image/jpeg", photo_type: str = "front") -> dict:
    """
    Extract comic information from a base64-encoded image.
    
    Args:
        base64_data: Base64-encoded image string
        media_type: MIME type of the image
    
    Returns:
        dict with extracted fields or error
    """
    if not ANTHROPIC_AVAILABLE or not _client:
        return {"success": False, "error": "Anthropic SDK not available"}

    # Authoritative orientation normalization BEFORE both the barcode scan and the
    # vision call. The client may send a rotated-with-EXIF photo and the API reads
    # raw pixels. Per-photo policy (normalize_for_photo_type): front/back/spine
    # assume portrait; centerfold is EXIF-only. Fail loud if undecodable.
    try:
        base64_data = normalize_for_photo_type(base64_data, photo_type)
        media_type = "image/jpeg"  # normalize_for_photo_type always emits JPEG
    except ValueError as e:
        return {"success": False, "error": f"Image could not be processed: {e}"}

    # First, try to scan barcode with pyzbar (more reliable than vision)
    scanned_barcode = None
    try:
        image_bytes = base64.b64decode(base64_data)
        scanned_barcode = scan_barcode(image_bytes)
        if scanned_barcode:
            print(f"[Extraction] Barcode scanned: {scanned_barcode}")
    except Exception as e:
        print(f"[Extraction] Barcode scan failed: {e}")

    try:
        extracted, text_content = _run_vision_pass(base64_data, media_type)
        vision_calls = 1

        # --- Item 2: one-shot 180 deg low-confidence fallback. A 180 deg flip is
        #     invisible to the dimension-based orientation heuristic above, so when
        #     the first read is weak we re-read ONCE rotated 180 deg and keep
        #     whichever pass scored higher. Every retry is logged so the doubled
        #     vision-call cost is visible. ---
        low, reason = _extraction_low_confidence(extracted)
        if low:
            print(f"[Extraction] Pass 1 low-confidence (reason={reason}) — retrying "
                  f"with 180 deg rotation [VISION CALL #2 — doubled cost]")
            try:
                extracted2, text2 = _run_vision_pass(rotate_180_b64(base64_data), media_type)
                vision_calls = 2
                s1, s2 = _extraction_score(extracted), _extraction_score(extracted2)
                if s2 > s1:
                    extracted, text_content = extracted2, text2
                    if extracted is not None:
                        # Corrected server-side: returned data is already upright, so
                        # the client must NOT rotate again (would re-invert).
                        extracted['is_upside_down'] = False
                        extracted['orientation_corrected'] = '180'
                    print(f"[Extraction] 180 deg retry KEPT pass 2 (score {s1} -> {s2}); "
                          f"vision_calls={vision_calls}")
                else:
                    # Server is authoritative on orientation: it evaluated both
                    # rotations and kept pass 1, so the client must NOT re-rotate
                    # (would cause a redundant 180 round-trip / wrong stored photo).
                    # With this, a returned is_upside_down is never True.
                    if extracted is not None:
                        extracted['is_upside_down'] = False
                    print(f"[Extraction] 180 deg retry discarded, kept pass 1 "
                          f"(score {s1} vs {s2}); vision_calls={vision_calls}")
            except Exception as e:
                print(f"[Extraction] 180 deg retry skipped/failed (keeping pass 1): {e}")

        if extracted is not None:
            
            # Check if the image is actually a comic book cover
            if not extracted.get('is_comic_cover', True):
                return {
                    "success": False,
                    "error": "This doesn't appear to be a comic book cover. Please upload a photo of a comic's front cover.",
                    "not_comic": True
                }

            # Clean up old field names if Claude returns them
            if "signature_detected" in extracted:
                del extracted["signature_detected"]
            if "signature_analysis" in extracted:
                del extracted["signature_analysis"]
            
            # Use pyzbar barcode data (more reliable than vision)
            if scanned_barcode:
                # Store full barcode info
                extracted['barcode_scanned'] = scanned_barcode
                
                # Use scanned UPC main if available
                if scanned_barcode.get('upc_main'):
                    extracted['upc_main'] = scanned_barcode['upc_main']
                
                # Use scanned addon (5-digit) if available
                if scanned_barcode.get('upc_addon'):
                    extracted['barcode_digits'] = scanned_barcode['upc_addon']
                    extracted['barcode_source'] = 'pyzbar'
                    print(f"[Extraction] Using pyzbar 5-digit addon: {scanned_barcode['upc_addon']}")
                elif scanned_barcode.get('supplement'):
                    extracted['barcode_digits'] = scanned_barcode['supplement']
                    extracted['barcode_source'] = 'pyzbar'
                    print(f"[Extraction] Using pyzbar supplement: {scanned_barcode['supplement']}")
            
            # Decode barcode ONLY from a pyzbar-confirmed 5-digit addon.
            # The vision model is also asked to read barcode_digits, but its guess
            # is unreliable — especially on pre-2008 books that have NO IIICP
            # add-on at all — and must NOT derive issue/printing/variant. Trusting
            # it produced false decodes like Amethyst Annual #1 -> "issue 251".
            # `barcode_source` is set to 'pyzbar' only by the scanner branches
            # above; the model never sets it. Without a confirmed addon we keep
            # only the main UPC (series ID) and leave issue/printing/variant to the
            # vision read (low confidence).
            if extracted.get('barcode_digits') and extracted.get('barcode_source') == 'pyzbar':
                barcode_decoded = decode_barcode(extracted['barcode_digits'])
                if barcode_decoded:
                    extracted['barcode_decoded'] = barcode_decoded
                    
                    # Flag reprints and variants from barcode
                    if barcode_decoded.get('is_reprint'):
                        extracted['is_reprint'] = True
                        # Update printing field if barcode says it's not 1st
                        if barcode_decoded.get('printing', 1) > 1:
                            extracted['printing'] = f"{barcode_decoded['printing']}{'nd' if barcode_decoded['printing'] == 2 else 'rd' if barcode_decoded['printing'] == 3 else 'th'}"
                    
                    if barcode_decoded.get('is_variant'):
                        extracted['is_variant'] = True
                        # Add cover letter if not already specified
                        if not extracted.get('cover') and barcode_decoded.get('cover_letter'):
                            extracted['cover'] = f"Cover {barcode_decoded['cover_letter']}"
                    
                    print(f"[Extraction] Barcode decoded: {barcode_decoded}")
            elif extracted.get('barcode_digits'):
                # Vision-model guess with no pyzbar-confirmed addon — do NOT derive
                # issue/printing/variant from it (series ID via main UPC only).
                print(f"[Extraction] Ignoring unverified vision barcode_digits "
                      f"'{extracted.get('barcode_digits')}' (no pyzbar addon) — series ID only")
                extracted['barcode_source'] = 'vision_unverified'

            return {
                "success": True,
                "extracted": extracted
            }
        else:
            return {
                "success": False,
                "error": "Could not parse extraction response",
                "raw": text_content
            }
            
    except anthropic.APITimeoutError:
        return {"success": False, "error": "Request timed out"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
