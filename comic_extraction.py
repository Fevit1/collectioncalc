"""
Comic Extraction Module
Extracts comic book information from photos using Claude Vision.
"""

import os
import base64
import json
import requests
from io import BytesIO

# Try to import barcode scanning library
try:
    from pyzbar import pyzbar
    from PIL import Image
    BARCODE_SCANNING_AVAILABLE = True
except ImportError:
    BARCODE_SCANNING_AVAILABLE = False
    print("pyzbar not available - barcode scanning disabled")

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')


def scan_barcode(image_data: bytes) -> dict:
    """
    Scan image for UPC barcode and extract the 5-digit supplement.
    
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
        
        # Scan for barcodes
        barcodes = pyzbar.decode(image)
        
        for barcode in barcodes:
            data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            
            # UPC-A is 12 digits, EAN-13 is 13 digits
            # The 5-digit supplement may be separate or appended
            if barcode_type in ['UPCA', 'EAN13', 'UPCE']:
                print(f"[Barcode] Found {barcode_type}: {data}")
                return {
                    'type': barcode_type,
                    'data': data,
                    'supplement': None  # Supplement usually separate
                }
            
            # EAN-5 is the 5-digit supplement we want!
            if barcode_type == 'EAN5' or (len(data) == 5 and data.isdigit()):
                print(f"[Barcode] Found 5-digit supplement: {data}")
                return {
                    'type': 'SUPPLEMENT',
                    'data': data,
                    'supplement': data
                }
        
        # No barcode found
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

# Vision Guide prompt for accurate extraction
EXTRACTION_PROMPT = """Analyze this comic book image and extract information. Return ONLY a JSON object with these fields:

IDENTIFICATION FIELDS:
- title: Comic book title (usually the largest text on the cover). Include the main series name only, NOT "Annual" or "Special" - those go in issue_type.
- issue: Issue number - IMPORTANT: Look for a "#" symbol followed by a number, typically in the TOP-LEFT area near the price. IGNORE prices like "60¢", "$1.00", "25p" - these are NOT issue numbers. The issue number usually appears as "#242" or "No. 242". Just return the number, no # symbol.
- issue_type: CRITICAL - Look carefully for these indicators on the cover:
  * "Annual" or "ANNUAL" → return "Annual"
  * "King-Size Special" or "KING-SIZE SPECIAL" → return "Annual" (these are annuals)
  * "Giant-Size" or "GIANT-SIZE" → return "Giant-Size"
  * "Special" or "SPECIAL" (standalone) → return "Special"
  * "Special Edition" → return "Special Edition"
  * If none of these are present → return "Regular"
  These indicators are often in LARGE TEXT at the top of the cover or in a banner. They dramatically affect the comic's value - an Annual #6 is completely different from Regular #6.
- publisher: Publisher name (Marvel, DC, Image, etc.) - often in small text at top
- year: Publication year - look for copyright text or indicia, usually small text
- writer: Look for writer credits on cover (often near top or bottom). Common patterns: "Written by NAME", "WRITER: NAME", or just a name with "WRITER" nearby. Return the name(s) if found, otherwise empty string.
- artist: Look for artist credits on cover. Common patterns: "Art by NAME", "ARTIST: NAME", or just a name with "ART" or "PENCILS" nearby. Return the name(s) if found, otherwise empty string.
- edition: Look at the BOTTOM-LEFT CORNER. If you see a UPC BARCODE, return "newsstand". If you see ARTWORK or LOGO, return "direct". If unclear, return "unknown".
- printing: Look for "2nd Printing", "3rd Print", "Second Printing", etc. anywhere on cover. Return "1st" if no printing indicator found, otherwise "2nd", "3rd", etc.
- is_facsimile: IMPORTANT - Look for "FACSIMILE", "FACSIMILE EDITION", or "FACSIMILE REPRINT" anywhere on the cover. These are modern reprints of classic covers. Return true if found, false otherwise. Facsimiles often have a small "FACSIMILE EDITION" banner or text, sometimes in the corner or along an edge.
- cover: Look for cover variant indicators like "Cover A", "Cover B", "Variant Cover", "1:25", "1:50", "Incentive", "Virgin", etc. Return the variant info if found, otherwise empty string.
- variant: Other variant description if applicable (e.g., "McFarlane variant", "Artgerm cover"), otherwise empty string
- barcode_digits: **REQUIRED** - Look carefully at the UPC barcode area (bottom-left of cover). Find the 5-DIGIT ADD-ON CODE - a separate smaller barcode to the RIGHT of the main UPC. The 5 digits appear as human-readable numbers near this small barcode, often printed VERTICALLY (reading top-to-bottom) or horizontally. These digits encode issue/printing/cover info. Examples: DC "00111" = issue 1, 1st printing, cover A. DC "00121" = issue 1, 2nd printing, cover A. DC "00112" = issue 1, 1st printing, cover B. Marvel typically uses similar 5-digit codes. Extract ONLY these 5 digits as a string. If you cannot clearly read all 5 digits, return empty string. Do NOT return the main 12-digit UPC number. YOU MUST ALWAYS INCLUDE THIS FIELD.

CONDITION ASSESSMENT FIELDS:
Examine the comic's PHYSICAL CONDITION carefully. You can only see the front cover, so assess what's visible.

IMPORTANT - DISTINGUISH BETWEEN:
1. COMIC DEFECTS (on the actual comic) - These affect grade
2. BAG/SLEEVE ARTIFACTS (on the protective covering) - IGNORE these:
   - Price stickers on the outside of a bag
   - Reflections or glare from plastic sleeve
   - Tape on the bag opening
   - Bag wrinkles or cloudiness
   If the comic appears to be in a bag/sleeve, look THROUGH it to assess the comic itself.

3. SIGNATURES - Distinguish between:
   - CREATOR SIGNATURES (writer, artist, etc.) - These ADD value, not defects. Look for professional signatures, often with CGC/CBCS witness stickers, or signatures that match known creator names for that comic.
   - RANDOM WRITING (names, dates, scribbles) - These are defects that lower grade.

- suggested_grade: Based on visible condition, suggest one of: MT, NM, VF, FN, VG, G, FR, PR. Be conservative - grade what you can see.
- defects: Array of visible defects found ON THE COMIC (not on bag). Examples:
  * "Tear on front cover, approx 1 inch"
  * "Spine roll"
  * "Color-breaking crease across cover"
  * "Corner wear, top right"
  * "Staining near bottom"
  * "Rusty staples"
  * "Price sticker residue on cover"
  Return empty array [] if no defects visible.
- signatures: Array of any signatures visible. For each, note if it appears to be a creator signature or unknown. Example:
  * "Signature present - appears to be creator (Jim Lee)"
  * "Signature present - unknown/unverified"
  * "Name written in marker - not a creator signature (defect)"
  Return empty array [] if no signatures.
- grade_reasoning: Brief explanation of grade choice, e.g., "VF - Minor spine stress visible, corners sharp, colors bright" or "VG - Visible tear on cover, moderate wear"

GRADE GUIDE (be conservative):
- MT (10.0): Perfect, virtually flawless
- NM (9.4): Nearly perfect, minor imperfections only
- VF (8.0): Minor wear, small stress marks OK, still attractive
- FN (6.0): Moderate wear, minor creases, slightly rolled spine OK
- VG (4.0): Significant wear, small tears, creases, still complete
- G (2.0): Heavy wear, larger creases, small pieces may be missing
- FR (1.5): Major wear, tears, pieces missing but still readable
- PR (1.0): Severe damage, may be incomplete

CRITICAL RULES:
1. Do NOT confuse prices (60¢, $1.50, 25p) with issue numbers. Issue numbers are preceded by "#" or "No." and are typically 1-4 digits.
2. ALWAYS check for "Annual", "King-Size Special", "Giant-Size", or "Special" - these are DIFFERENT series than the regular comic and have very different values.
3. If you see "KING-SIZE SPECIAL" anywhere, the issue_type MUST be "Annual".
4. ALWAYS check for "FACSIMILE" or "FACSIMILE EDITION" - these are reprints worth $5-15, not originals worth potentially hundreds. Set is_facsimile: true if found.
5. For condition: You can ONLY see the front cover. Note this limitation - back cover damage would not be visible.
6. Ignore bag/sleeve artifacts. Assess the comic itself.
7. Creator signatures are valuable, not defects.
8. IMAGE ORIENTATION CHECK: If the image appears to be UPSIDE-DOWN (text is inverted, characters are upside-down), add a field "is_upside_down": true. Otherwise omit this field or set it to false. This helps the system auto-correct the orientation.

YOUR RESPONSE MUST INCLUDE ALL OF THESE FIELDS (use empty string "" if not found):
{
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
  "suggested_grade": "",
  "defects": [],
  "signatures": [],
  "grade_reasoning": ""
}

Be accurate. If unsure about any field, use reasonable estimates."""


def extract_from_photo(image_data: bytes, filename: str = "comic.jpg") -> dict:
    """
    Extract comic information from a photo using Claude Vision.
    
    Args:
        image_data: Raw image bytes
        filename: Original filename (used to determine media type)
    
    Returns:
        dict with extracted fields or error
    """
    if not ANTHROPIC_API_KEY:
        return {"success": False, "error": "ANTHROPIC_API_KEY not configured"}
    
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


def extract_from_base64(base64_data: str, media_type: str = "image/jpeg") -> dict:
    """
    Extract comic information from a base64-encoded image.
    
    Args:
        base64_data: Base64-encoded image string
        media_type: MIME type of the image
    
    Returns:
        dict with extracted fields or error
    """
    if not ANTHROPIC_API_KEY:
        return {"success": False, "error": "ANTHROPIC_API_KEY not configured"}
    
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
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "temperature": 0,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT
                        }
                    ]
                }]
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Anthropic API error: {response.status_code} - {response.text}"
            }
        
        data = response.json()
        
        # Extract text content
        text_content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_content += block.get("text", "")
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', text_content)
        
        if json_match:
            extracted = json.loads(json_match.group())
            
            # Use pyzbar barcode if Claude didn't find one
            if scanned_barcode and scanned_barcode.get('supplement'):
                if not extracted.get('barcode_digits'):
                    extracted['barcode_digits'] = scanned_barcode['supplement']
                    extracted['barcode_source'] = 'pyzbar'
                    print(f"[Extraction] Using pyzbar barcode: {scanned_barcode['supplement']}")
            
            # Decode barcode if present
            barcode_decoded = None
            if extracted.get('barcode_digits'):
                barcode_decoded = decode_barcode(extracted['barcode_digits'])
                if barcode_decoded:
                    extracted['barcode_decoded'] = barcode_decoded
                if barcode_decoded:
                    extracted['barcode_decoded'] = barcode_decoded
            
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
            
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
